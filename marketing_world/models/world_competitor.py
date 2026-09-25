# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MarketingWorldCompetitor(models.Model):
    """Tracked competitors per customer."""

    _name = 'marketing.world.competitor'
    _description = 'World Monitor Competitor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Competitor Name', required=True, tracking=True)
    website = fields.Char('Website')
    description = fields.Text('Description')

    # ── Customer ──
    customer_id = fields.Many2one(
        'res.partner', string='Customer',
        domain="[('is_company', '=', True)]",
        required=True, ondelete='cascade',
        help='The customer whose competitor this is',
    )

    # ── Monitoring ──
    wm_search_query = fields.Char(
        'WM Search Query',
        help='Search query used in World Monitor for news about this competitor',
    )
    last_mention_date = fields.Datetime('Last Mention', readonly=True)
    mention_count = fields.Integer('Mention Count', default=0)
    latest_mention_summary = fields.Text('Latest Mention Summary', readonly=True)

    # ── Website RAG data ──
    website_scraped_at = fields.Datetime('Website Last Scraped', readonly=True)
    website_homepage = fields.Text('Website Homepage', readonly=True,
                                    help='Extracted text from competitor homepage')
    website_about = fields.Text('Website About', readonly=True,
                                 help='Extracted text from about/company page')
    website_pricing = fields.Text('Website Pricing', readonly=True,
                                   help='Extracted text from pricing page')
    website_features = fields.Text('Website Features', readonly=True,
                                    help='Extracted text from features/product page')
    website_pages_count = fields.Integer('Pages Scraped', readonly=True, default=0)

    # ── Battle Cards ──
    battle_card = fields.Text(
        'Battle Card',
        help='Competitive intelligence battle card',
    )
    battle_card_updated = fields.Datetime('Battle Card Updated')

    # ── Alerts ──
    alert_new_product = fields.Boolean(
        'Alert: New Product',
        default=True,
        help='Alert when competitor launches new products',
    )
    alert_funding = fields.Boolean(
        'Alert: Funding',
        default=True,
        help='Alert when competitor receives funding',
    )
    alert_partnership = fields.Boolean(
        'Alert: Partnership',
        default=True,
        help='Alert when competitor forms partnerships',
    )

    # ── Links ──
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    related_event_ids = fields.One2many(
        'marketing.world.event',
        compute='_compute_related_events',
        string='Related Events',
        help='World events mentioning this competitor',
    )
    related_event_count = fields.Integer(
        'Related Events',
        compute='_compute_related_events',
    )

    @api.depends('name')
    def _compute_related_events(self):
        for record in self:
            if record.name:
                events = self.env['marketing.world.event'].search([
                    '|',
                    ('name', 'ilike', record.name),
                    ('summary', 'ilike', record.name),
                    ('state', 'in', ('relevant', 'escalated', 'triaged')),
                ], limit=50)
                record.related_event_ids = events
                record.related_event_count = len(events)
            else:
                record.related_event_ids = False
                record.related_event_count = 0

    # ── Website scraping (RAG) ──

    def action_scrape_website(self):
        """Scrape competitor website for RAG context."""
        for record in self:
            if not record.website:
                raise UserError(_('No website URL configured for this competitor.'))
            record._scrape_competitor_website()
        return True

    def _scrape_competitor_website(self):
        """Fetch and extract text from competitor key pages.

        Stores extracted text in dedicated fields for RAG-powered battle cards.
        """
        self.ensure_one()
        base_url = self.website.rstrip('/')
        timeout = 15
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (compatible; VertelWorldMonitor/1.0; '
                '+https://vertel.se)'
            ),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'sv,en;q=0.9',
        }

        # Pages to attempt
        pages = {
            'homepage': base_url,
            'about': None,
            'pricing': None,
            'features': None,
        }

        # Common about page paths
        for path in ['/about', '/about-us', '/company', '/om-oss',
                      '/about-us/', '/company/']:
            pages['about'] = base_url + path
            break  # Try first one — _fetch_page handles 404

        # Common pricing paths
        for path in ['/pricing', '/plans', '/pris', '/pricing/', '/plans-and-pricing']:
            pages['pricing'] = base_url + path
            break

        # Common feature paths
        for path in ['/features', '/product', '/platform', '/functions',
                      '/features/', '/product/']:
            pages['features'] = base_url + path
            break

        results = {}
        pages_scraped = 0

        for page_key, page_url in pages.items():
            if not page_url:
                continue
            try:
                text = self._fetch_page_text(page_url, timeout, headers)
                if text:
                    results[page_key] = text
                    pages_scraped += 1
                    _logger.info(
                        'Scraped %s for %s: %d chars',
                        page_key, self.name, len(text),
                    )
            except Exception as e:
                _logger.debug(
                    'Failed to scrape %s for %s: %s',
                    page_key, self.name, str(e),
                )

        # Write results to fields
        vals = {
            'website_scraped_at': fields.Datetime.now(),
            'website_pages_count': pages_scraped,
        }
        for key, field in [
            ('homepage', 'website_homepage'),
            ('about', 'website_about'),
            ('pricing', 'website_pricing'),
            ('features', 'website_features'),
        ]:
            vals[field] = results.get(key, '')

        self.write(vals)
        _logger.info(
            'Scraped %d pages for competitor %s',
            pages_scraped, self.name,
        )
        return results

    @api.model
    def _fetch_page_text(self, url, timeout=15, headers=None):
        """Fetch a URL and extract visible text using BeautifulSoup.

        Returns cleaned text content or empty string on failure.
        """
        if not headers:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (compatible; VertelWorldMonitor/1.0; '
                    '+https://vertel.se)'
                ),
                'Accept': 'text/html',
            }

        try:
            resp = requests.get(
                url, timeout=timeout, headers=headers,
                allow_redirects=True,
            )
            if resp.status_code != 200:
                _logger.debug('HTTP %d for %s', resp.status_code, url)
                return ''

            # Limit to 512KB to avoid OOM
            content = resp.content[:524288]

            soup = BeautifulSoup(content, 'lxml')

            # Remove script, style, nav, footer, header boilerplate
            for tag in soup.find_all(['script', 'style', 'nav', 'footer',
                                       'header', 'noscript', 'iframe',
                                       'svg', 'form']):
                tag.decompose()

            # Remove hidden elements
            for tag in soup.find_all(True):
                if tag.get('aria-hidden') == 'true':
                    tag.decompose()
                elif tag.get('style') and 'display:none' in tag.get('style', '').replace(' ', ''):
                    tag.decompose()

            # Get text, clean up whitespace
            text = soup.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' +', ' ', text)

            # Limit to 10000 chars per page
            return text[:10000]

        except requests.Timeout:
            _logger.debug('Timeout fetching %s', url)
            return ''
        except requests.ConnectionError:
            _logger.debug('Connection error fetching %s', url)
            return ''
        except Exception as e:
            _logger.debug('Error fetching %s: %s', url, str(e))
            return ''

    @api.model
    def _extract_tagline(self, homepage_text):
        """Extract likely tagline/headline from homepage text."""
        if not homepage_text:
            return ''
        lines = [l.strip() for l in homepage_text.split('\n') if l.strip()]
        # First non-trivial line is often the headline
        for line in lines[:20]:
            if len(line) > 10 and len(line) < 200:
                return line[:150]
        return lines[0][:150] if lines else ''

    @api.model
    def _extract_pricing_tiers(self, pricing_text):
        """Try to identify pricing tiers from pricing text."""
        if not pricing_text:
            return []
        # Look for currency patterns
        price_patterns = re.findall(
            r'(\d[\d\s]*[.,]?\d*\s*(?:kr|sek|usd|eur|€|\$|£))',
            pricing_text, re.IGNORECASE,
        )
        return price_patterns[:5]

    # ── Actions ──

    def action_check_wm(self):
        """Search World Monitor for news about this competitor."""
        for record in self:
            query = record.wm_search_query or record.name
            try:
                wm_api = self.env['world.monitor.api']
                results = wm_api.fetch_news_intelligence(query=query, limit=10)
                if results:
                    first = results[0] if isinstance(results, list) else results
                    record.write({
                        'last_mention_date': fields.Datetime.now(),
                        'mention_count': record.mention_count + len(results) if isinstance(results, list) else record.mention_count + 1,
                        'latest_mention_summary': first.get('summary', first.get('content', ''))[:500] if isinstance(first, dict) else '',
                    })
            except Exception as e:
                _logger.error('WM search failed for %s: %s', record.name, str(e))
        return True

    def action_scrape_and_generate(self):
        """Scrape website first, then generate battle card."""
        self.action_scrape_website()
        return self.action_generate_battle_card()

    def action_generate_battle_card(self):
        """Generate battle card from WM intelligence + Odoo data + website RAG."""
        for record in self:
            try:
                wm_api = self.env['world.monitor.api']
                query = record.wm_search_query or record.name

                # ── 1. Ensure website is scraped (if URL exists and never scraped) ──
                if record.website and not record.website_scraped_at:
                    try:
                        record._scrape_competitor_website()
                    except Exception as e:
                        _logger.warning('Website scrape failed: %s', str(e))

                # ── 2. Fetch WM news intelligence ──
                wm_results = []
                try:
                    wm_results = wm_api.fetch_news_intelligence(
                        query=query, limit=15
                    )
                except Exception as e:
                    _logger.warning(
                        'WM fetch failed: %s', str(e),
                    )

                # ── 3. Gather related events from Odoo ──
                related_events = self.env['marketing.world.event'].search([
                    '|',
                    ('name', 'ilike', record.name),
                    ('summary', 'ilike', record.name),
                    ('state', 'in', ('relevant', 'escalated', 'triaged')),
                ], limit=20)

                # ── 4. Build battle card ──
                customer_name = record.customer_id.display_name if record.customer_id else '—'
                now = fields.Datetime.now().isoformat()

                lines = []
                lines.append(f'# Battle Card: {record.name}')
                lines.append('')
                lines.append(f'**Customer**: {customer_name}')
                lines.append(f'**Generated**: {now}')
                lines.append(f'**Website**: {record.website or "—"}')
                lines.append(f'**Website Scraped**: {record.website_scraped_at or "—"} ({record.website_pages_count} pages)')
                lines.append(f'**WM Search Query**: {record.wm_search_query or record.name}')
                lines.append(f'**WM Mentions Found**: {len(wm_results) if isinstance(wm_results, list) else 0}')
                lines.append(f'**Odoo Events Mentioning**: {len(related_events)}')
                lines.append('')

                # ── Positioning & Messaging (from website RAG) ──
                if record.website_homepage:
                    tagline = self._extract_tagline(record.website_homepage)
                    lines.append('## Positioning & Messaging')
                    lines.append('')
                    lines.append(f'**Tagline**: {tagline}' if tagline else '')
                    lines.append(f'**Headline**: *Full homepage text analyzed — see RAG-data nedan*')
                    lines.append('')
                    # Extract key sections from homepage
                    homepage_lines = record.website_homepage.split('\n')
                    key_sections = [l.strip() for l in homepage_lines
                                    if l.strip() and len(l.strip()) > 20][:5]
                    if key_sections:
                        lines.append('**Key homepage takeaways**:')
                        for s in key_sections:
                            lines.append(f'- {s[:150]}')
                    lines.append('')

                # ── Pricing & Features (from website RAG) ──
                if record.website_pricing:
                    tiers = self._extract_pricing_tiers(record.website_pricing)
                    lines.append('### Pricing')
                    lines.append('')
                    if tiers:
                        lines.append(f'**Prisindikationer från webbplatsen**: {", ".join(tiers[:5])}')
                    else:
                        lines.append('*Prisuppgifter funna — se RAG-data nedan*')
                    lines.append('')

                if record.website_features:
                    feature_lines = [l.strip() for l in record.website_features.split('\n')
                                     if l.strip() and len(l.strip()) > 15][:8]
                    if feature_lines:
                        lines.append('### Nyckelfunktioner')
                        lines.append('')
                        for fl in feature_lines:
                            lines.append(f'- {fl[:120]}')
                        lines.append('')

                if record.website_about:
                    about_lines = [l.strip() for l in record.website_about.split('\n')
                                   if l.strip() and len(l.strip()) > 20][:5]
                    if about_lines:
                        lines.append('### Om företaget')
                        lines.append('')
                        for al in about_lines:
                            lines.append(f'- {al[:150]}')
                        lines.append('')

                # ── Recent Movements (from Odoo events) ──
                if related_events:
                    lines.append('## Recent Movements')
                    lines.append('')
                    lines.append('| Date | Event | Severity | Category |')
                    lines.append('|------|-------|----------|----------|')
                    for e in related_events.sorted(key=lambda x: x.date, reverse=True)[:10]:
                        date_str = str(e.date.date()) if e.date else '—'
                        lines.append(f'| {date_str} | {e.name[:60]} | {e.severity} | {e.category} |')
                    lines.append('')

                    by_cat = {}
                    for e in related_events:
                        cat = e.category
                        if cat not in by_cat:
                            by_cat[cat] = []
                        by_cat[cat].append(e)

                    lines.append('### Omvärldsanalys per kategori')
                    lines.append('')
                    for cat, cat_events in sorted(by_cat.items()):
                        cat_label = dict(
                            self.env['marketing.world.event'].fields_get(
                                ['category']
                            )['category']['selection']
                        ).get(cat, cat)
                        lines.append(f'**{cat_label}**')
                        for e in cat_events:
                            severity_badge = {
                                'critical': '🔴', 'high': '🟠',
                                'medium': '🟡', 'low': '🟢', 'info': '🔵',
                            }.get(e.severity, '⚪')
                            lines.append(f'- {severity_badge} {e.name} '
                                          f'({e.severity.upper()})')
                            if e.summary:
                                lines.append(f'  - {e.summary[:150]}')
                            if e.risk_ids:
                                lines.append(f'  - ⚠️ Risk #{e.risk_ids[0].id}')
                        lines.append('')

                # ── World Monitor news ──
                if wm_results and isinstance(wm_results, list):
                    lines.append('## World Monitor-information')
                    lines.append('')
                    for item in wm_results[:10]:
                        title = item.get('title', item.get('name', 'Untitled'))
                        summary = item.get('summary', item.get('content', ''))
                        source = item.get('source_name', item.get('source', '—'))
                        url = item.get('url', '')
                        if isinstance(summary, str):
                            lines.append(f'- **{title}**')
                            lines.append(f'  - {summary[:200]}')
                            lines.append(f'  - Källa: {source}')
                            if url:
                                lines.append(f'  - {url}')
                    lines.append('')

                # ── Competitive SWOT (nu med RAG-data) ──
                lines.append('## Competitive SWOT')
                lines.append('')

                has_rag = bool(record.website_homepage or record.website_features
                               or record.website_pricing or record.website_about)

                lines.append('### Strengths (deras vs. oss)')
                if has_rag:
                    lines.append('- *Baseras på webbplatsanalys + WM-data*')
                    # Extract potential strengths from homepage
                    if record.website_homepage:
                        hp_lower = record.website_homepage.lower()
                        strength_signals = []
                        if any(w in hp_lower for w in ['leader', 'award', '#1', 'top-rated',
                                                        'most trusted', 'enterprise-grade']):
                            strength_signals.append('Positionerar sig som marknadsledare')
                        if any(w in hp_lower for w in ['million', 'billion', '1000+', '10,000+']):
                            strength_signals.append('Angett kundmassa/storlek som signalerar marknadskraft')
                        if any(w in hp_lower for w in ['integrat', 'api', 'connector']):
                            strength_signals.append('Stark integrationsförmåga')
                        for signal in strength_signals:
                            lines.append(f'- {signal}')
                    if not strength_signals:
                        lines.append('- *Webbplatsdata tillgänglig — granska homepage för styrkor*')
                else:
                    lines.append('- *Ingen webbplatsdata — kör "Scrape Website" eller ange URL för RAG*')
                lines.append('')

                lines.append('### Weaknesses (deras vs. oss)')
                if has_rag:
                    lines.append('- *Analyseras från webbplats — leta efter gap, otydligheter*')
                    if record.website_pricing and not self._extract_pricing_tiers(record.website_pricing):
                        lines.append('- 💰 Ingen tydlig prisinformation på webbplatsen')
                    if record.website_homepage:
                        hp_lower = record.website_homepage.lower()
                        if any(w in hp_lower for w in ['contact sales', 'request demo', 'book a call']):
                            lines.append('- 🔒 Kräver kontaktsälj — kan indikera högt pris eller komplex onboarding')
                        if len(record.website_homepage) < 500:
                            lines.append('- 📄 Homepage har lite textinnehåll — svag SEO/positionering')
                else:
                    lines.append('- *Ingen webbplatsdata — ange URL för djupare analys*')
                lines.append('')

                lines.append('### Opportunities (för oss)')
                if related_events:
                    critical_events = related_events.filtered(
                        lambda e: e.severity in ('high', 'critical')
                    )
                    if critical_events:
                        lines.append('- 🟠 Händelser som påverkar konkurrentbilden:')
                        for e in critical_events:
                            lines.append(f'  - {e.name}')
                if has_rag and record.website_homepage:
                    hp_lower = record.website_homepage.lower()
                    if 'enterprise' not in hp_lower:
                        lines.append('- 🎯 Enterprise-segmentet verkar inte adresseras — möjlighet för oss')
                    if 'pricing' not in hp_lower and not record.website_pricing:
                        lines.append('- 💵 Ingen prisbild synlig — kan indikera otydlig GTM')
                if not related_events and not has_rag:
                    lines.append('- *Samla data först: kör "Scrape Website" och "Check World Monitor"*')
                lines.append('')

                lines.append('### Threats (från dem)')
                threat_sources = []
                if wm_results and isinstance(wm_results, list):
                    for item in wm_results[:5]:
                        title = item.get('title', item.get('name', '—'))
                        threat_sources.append(title[:80])
                if has_rag and record.website_homepage:
                    hp_lower = record.website_homepage.lower()
                    if any(w in hp_lower for w in ['new', 'launch', 'announce', 'coming soon']):
                        threat_sources.append('Nya produkter/tjänster på gång enligt webbplatsen')
                    if any(w in hp_lower for w in ['funding', 'series', 'raised', 'investment']):
                        threat_sources.append('Expandering med ny finansiering')
                if threat_sources:
                    lines.append('- 🟢 Att bevaka:')
                    for ts in threat_sources:
                        lines.append(f'  - {ts}')
                else:
                    lines.append('- *Ingen data — kör WM-sökning för att upptäcka hot*')
                lines.append('')

                # ── Counter-Strategies ──
                lines.append('## Counter-Strategies')
                lines.append('')
                if has_rag or wm_results or related_events:
                    counter = [
                        ('Säljargument', 'Använd RAG-data från deras webbplats + WM-insikter för att visa att ni har djupare omvärldsbevakning'),
                    ]
                    if has_rag:
                        counter.append(('Differentiering', 'Betona integrerad strategi (ERP + omvärldsbevakning + AI) — något de inte kan matcha'))
                    if record.website_pricing:
                        counter.append(('Prissättning', 'Använd insikter från deras prissida för att positionera ert prisvärde'))
                    counter.append(('Bevakning', 'Fortsätt övervaka WM-flödet + återskrapa webbplatsen periodiskt för förändringar'))
                    counter.append(('Uppdatering', 'Kör "Scrape & Generate" för att hålla battle card aktuellt'))
                    for i, (title, desc) in enumerate(counter, 1):
                        lines.append(f'{i}. **{title}**: {desc}')
                else:
                    lines.append('1. **Börja med att samla data**: Ange URL, kör "Scrape Website" för RAG')
                    lines.append('2. **WM-sökning**: Kör "Check World Monitor" för att få senaste nytt')
                    lines.append('3. **Full analys**: Kör "Scrape & Generate" för att få allt på en gång')
                lines.append('')

                # ── Raw RAG data section ──
                if has_rag:
                    lines.append('---')
                    lines.append('## Rådata från webbplats (RAG)')
                    lines.append('')
                    lines.append('*Nedan text användes som RAG-kontext vid genereringen.*')
                    lines.append('')

                    homepage_length = len(record.website_homepage) if record.website_homepage else 0
                    about_length = len(record.website_about) if record.website_about else 0
                    pricing_length = len(record.website_pricing) if record.website_pricing else 0
                    features_length = len(record.website_features) if record.website_features else 0

                    lines.append(f'| Page | Chars | Extracted |')
                    lines.append(f'|------|-------|-----------|')
                    lines.append(f'| 🏠 Homepage | {homepage_length} | {"✅" if record.website_homepage else "❌"} |')
                    lines.append(f'| 🏢 About | {about_length} | {"✅" if record.website_about else "❌"} |')
                    lines.append(f'| 💰 Pricing | {pricing_length} | {"✅" if record.website_pricing else "❌"} |')
                    lines.append(f'| ⚙️ Features | {features_length} | {"✅" if record.website_features else "❌"} |')

                    if record.website_homepage:
                        lines.append('')
                        lines.append('### Homepage (utdrag)')
                        lines.append('')
                        lines.append(f'```\n{record.website_homepage[:3000]}\n```')
                    if record.website_about:
                        lines.append('')
                        lines.append('### About')
                        lines.append('')
                        lines.append(f'```\n{record.website_about[:2000]}\n```')

                lines.append('')
                lines.append('---')
                lines.append(f'_Battle card auto-generated {now}_')
                lines.append(f'_Sources: WM news intelligence, Odoo events, website RAG_')

                battle_card_text = '\n'.join(lines)

                # Update WM mention info
                if wm_results and isinstance(wm_results, list):
                    first = wm_results[0]
                    record.write({
                        'last_mention_date': fields.Datetime.now(),
                        'mention_count': record.mention_count + len(wm_results),
                        'latest_mention_summary': (
                            first.get('summary', first.get('content', ''))[:500]
                            if isinstance(first, dict) else ''
                        ),
                    })

                # Write battle card
                record.write({
                    'battle_card': battle_card_text,
                    'battle_card_updated': fields.Datetime.now(),
                })

                _logger.info(
                    'Battle card generated for %s '
                    '(WM: %d, events: %d, RAG pages: %d)',
                    record.name,
                    len(wm_results) if isinstance(wm_results, list) else 0,
                    len(related_events),
                    record.website_pages_count,
                )

            except Exception as e:
                _logger.error(
                    'Battle card failed for %s: %s',
                    record.name, str(e), exc_info=True,
                )
                record.write({
                    'battle_card': _(
                        'Battle Card: %s\n\n'
                        'Customer: %s\n'
                        'Generated: %s\n\n'
                        '---\n'
                        'Kunde inte generera. Fel: %s\n'
                        'Kontrollera URL och WM-anslutning.'
                    ) % (
                        record.name,
                        record.customer_id.display_name if record.customer_id else '—',
                        fields.Datetime.now().isoformat(),
                        str(e),
                    ),
                    'battle_card_updated': fields.Datetime.now(),
                })
