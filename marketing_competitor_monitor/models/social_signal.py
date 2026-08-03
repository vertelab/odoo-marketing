# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
import time
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CompetitorSocialSignal(models.Model):
    """Structured social media signals from LinkedIn and YouTube for tracked competitors."""

    _name = 'competitor.social.signal'
    _description = 'Competitor Social Signal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'published_at desc, id desc'
    _rec_name = 'display_name'

    # ── Identity & Source ──
    display_name = fields.Char('Title', compute='_compute_display_name', store=True)
    competitor_id = fields.Many2one(
        'marketing.world.competitor', string='Competitor',
        required=True, ondelete='cascade',
    )
    platform = fields.Selection([
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
    ], string='Platform', required=True, index=True)
    external_id = fields.Char('External ID', required=True, index=True,
                               help='Unique ID from the original platform (post ID, video ID)')
    url = fields.Char('URL', help='Direct link to the original post/video')

    # ── Content ──
    content = fields.Text('Content', help='Full text of the post or video description')
    author_name = fields.Char('Author Name')
    author_url = fields.Char('Author URL', help='Link to author profile/channel')

    # ── Time ──
    published_at = fields.Datetime('Published At', required=True, index=True)

    # ── Engagement ──
    engagement_likes = fields.Integer('Likes')
    engagement_comments = fields.Integer('Comments')
    engagement_shares = fields.Integer('Shares')
    engagement_total = fields.Integer(
        'Total Engagement',
        compute='_compute_engagement_total', store=True,
    )

    # ── YouTube-specific ──
    youtube_view_count = fields.Integer('YouTube Views')
    youtube_duration = fields.Char('Duration', help='Video duration (e.g. 12:34)')

    # ── AI Classification ──
    signal_type = fields.Selection([
        ('product_launch', 'Product Launch'),
        ('hire', 'Hiring/New Role'),
        ('funding', 'Funding'),
        ('partnership', 'Partnership'),
        ('customer_case', 'Customer Case'),
        ('pricing_change', 'Pricing Change'),
        ('positioning_shift', 'Positioning Shift'),
        ('complaint', 'Complaint/Crisis'),
        ('general_update', 'General Update'),
        ('other', 'Other'),
    ], string='Signal Type', index=True, tracking=True)
    signal_type_original = fields.Selection(
        related='signal_type', readonly=True,
        help='Original AI classification before manual override',
    )
    ai_relevance = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('noise', 'Noise'),
    ], string='AI Relevance', index=True)
    ai_relevance_original = fields.Selection(
        related='ai_relevance', readonly=True,
    )
    ai_score = fields.Integer('AI Score', help='Relevance score 0-100')
    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('mixed', 'Mixed'),
    ], string='Sentiment')
    sentiment_original = fields.Selection(
        related='sentiment', readonly=True,
    )
    ai_analysis = fields.Text('AI Analysis')
    ai_classified_at = fields.Datetime('AI Classified At')

    # ── State ──
    state = fields.Selection([
        ('new', 'New'),
        ('triaged', 'Triaged'),
        ('reviewed', 'Reviewed'),
        ('in_battle_card', 'In Battle Card'),
        ('archived', 'Archived'),
    ], string='State', required=True, default='new', index=True, tracking=True)

    # ── Multi-company ──
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        index=True,
    )

    # ── Override tracking ──
    overridden_fields = fields.Char(
        'Overridden Fields',
        help='Comma-separated list of fields that were manually overridden',
    )

    _sql_constraints = [
        ('unique_external_id_platform',
         'UNIQUE(external_id, platform)',
         'A signal with this external ID and platform already exists.'),
    ]

    # ── Computes ──

    @api.depends('platform', 'author_name', 'content')
    def _compute_display_name(self):
        for record in self:
            platform_icon = '🔗'
            if record.platform == 'linkedin':
                platform_icon = '💼'
            elif record.platform == 'youtube':
                platform_icon = '📺'
            first_line = (record.content or '')[:80].strip()
            if first_line:
                record.display_name = f'{platform_icon} [{record.platform}] {first_line}'
            else:
                record.display_name = f'{platform_icon} [{record.platform}] {record.author_name or "Unknown"}'

    @api.depends('engagement_likes', 'engagement_comments', 'engagement_shares')
    def _compute_engagement_total(self):
        for record in self:
            record.engagement_total = (
                (record.engagement_likes or 0) +
                (record.engagement_comments or 0) +
                (record.engagement_shares or 0) +
                (record.youtube_view_count or 0)
            )

    # ── State transitions ──

    def action_triage(self):
        """Mark signal as triaged."""
        for record in self:
            if record.state == 'new':
                record.state = 'triaged'

    def action_review(self):
        """Mark signal as reviewed."""
        for record in self:
            if record.state in ('new', 'triaged'):
                record.state = 'reviewed'

    def action_archive(self):
        """Archive signal."""
        for record in self:
            if record.state != 'archived':
                record.state = 'archived'
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Signal archived'),
                )

    # ── Override support ──

    def write(self, vals):
        """Track which fields are manually overridden."""
        override_fields = ['signal_type', 'ai_relevance', 'sentiment']
        overridden = []
        for f in override_fields:
            if f in vals:
                # Store original on first override
                original_field = f + '_original'
                if not self._fields.get(original_field):
                    pass
                overridden.append(f)

        if overridden:
            vals['overridden_fields'] = ','.join(overridden)

        return super().write(vals)

    # ── Open original ──

    def action_open_original(self):
        """Open the original post/video in a new browser tab."""
        self.ensure_one()
        if not self.url:
            raise UserError(_('No URL available for this signal.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }

    # ── LinkedIn pull ──

    @api.model
    def cron_pull_linkedin(self):
        """Pull LinkedIn company posts for all tracked competitors.

        Called by ir.cron every 6 hours. Uses linkedin_api (Voyager).
        """
        _logger.info('LinkedIn monitor: starting pull cycle')
        credentials = self._get_linkedin_credentials()
        if not credentials:
            _logger.warning('LinkedIn monitor: no credentials configured')
            return {'error': 'no_credentials'}

        email, password = credentials
        competitors = self.env['marketing.world.competitor'].search([
            ('competitor_linkedin_public_id', '!=', False),
            ('competitor_linkedin_pull_state', '!=', 'error'),
        ])

        if not competitors:
            _logger.info('LinkedIn monitor: no competitors with LinkedIn IDs')
            return {'processed': 0}

        # Import linkedin_api here to avoid import error at module load
        try:
            from linkedin_api import Linkedin
        except ImportError:
            _logger.error('linkedin_api not installed')
            return {'error': 'missing_dependency'}

        try:
            api = Linkedin(email, password)
        except Exception as e:
            _logger.error('LinkedIn login failed: %s', str(e))
            # Notify managers
            self._notify_linkedin_error('login_failed', str(e))
            return {'error': 'login_failed'}

        total_created = 0
        total_updated = 0
        total_errors = 0

        for competitor in competitors:
            try:
                public_id = competitor.competitor_linkedin_public_id
                posts = api.get_company_updates(public_id=public_id, max_results=50)

                created, updated = self._process_linkedin_posts(posts, competitor)
                total_created += created
                total_updated += updated

                competitor.write({
                    'competitor_linkedin_last_pull': fields.Datetime.now(),
                    'competitor_linkedin_pull_state': 'ok',
                })

                _logger.info(
                    'LinkedIn pull for %s: %d created, %d updated',
                    competitor.name, created, updated,
                )

            except Exception as e:
                total_errors += 1
                error_msg = str(e)
                _logger.error('LinkedIn pull failed for %s: %s', competitor.name, error_msg)

                # Detect CHALLENGE
                if 'CHALLENGE' in error_msg or 'challenge' in error_msg.lower():
                    competitor.write({
                        'competitor_linkedin_pull_state': 'challenge',
                    })
                    self._notify_linkedin_error('challenge', error_msg)
                else:
                    competitor.write({
                        'competitor_linkedin_pull_state': 'error',
                    })

        _logger.info(
            'LinkedIn monitor: %d created, %d updated, %d errors',
            total_created, total_updated, total_errors,
        )
        return {
            'created': total_created,
            'updated': total_updated,
            'errors': total_errors,
        }

    @api.model
    def _get_linkedin_credentials(self):
        """Read LinkedIn credentials from ir.config_parameter."""
        ICP = self.env['ir.config_parameter'].sudo()
        email = ICP.get_param('competitor_linkedin.email', '')
        password = ICP.get_param('competitor_linkedin.password', '')
        if email and password:
            return (email, password)
        return None

    @api.model
    def _notify_linkedin_error(self, error_type, message):
        """Send notification about LinkedIn issues to marketing managers."""
        group = self.env.ref('marketing_core.group_marketing_manager', raise_if_not_found=False)
        if not group:
            return
        users = group.users
        if not users:
            return

        titles = {
            'login_failed': 'LinkedIn Monitor: Inloggning misslyckades',
            'challenge': 'LinkedIn Monitor: CHALLENGE — kräver manuell åtgärd',
            'rate_limit': 'LinkedIn Monitor: Rate limit nådd',
        }
        title = titles.get(error_type, f'LinkedIn Monitor: {error_type}')

        for user in users:
            user.partner_id.message_post(
                subject=title,
                body=(
                    f'<p><b>{title}</b></p>'
                    f'<p>{message[:500]}</p>'
                    f'<p>Kontrollera LinkedIn-inställningarna under '
                    f'Inställningar → World Monitor → LinkedIn Monitor.</p>'
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

    @api.model
    def _process_linkedin_posts(self, posts, competitor):
        """Process LinkedIn posts and create/update signals.

        Args:
            posts: List of post dicts from linkedin_api.get_company_updates()
            competitor: marketing.world.competitor record

        Returns:
            tuple: (created_count, updated_count)
        """
        created = 0
        updated = 0

        for post in posts:
            post_id = post.get('id', post.get('urn', ''))
            if not post_id:
                continue

            # Extract post URN from LinkedIn format
            urn = post_id.split(':')[-1] if ':' in post_id else post_id

            # Extract content
            commentary = post.get('commentary', '')
            if isinstance(commentary, dict):
                commentary = commentary.get('text', '')

            # Extract timestamp
            created_at = post.get('createdAt', post.get('created', 0))
            if isinstance(created_at, (int, float)):
                published = datetime.fromtimestamp(created_at / 1000)
            else:
                published = fields.Datetime.now()

            # Extract engagement
            likes = 0
            comments = 0
            social_detail = post.get('socialDetail', {}) or {}
            if social_detail:
                likes = social_detail.get('totalSocialActivityCounts', {}).get('likeCount', 0)
                comments = social_detail.get('totalSocialActivityCounts', {}).get('commentCount', 0)

            # Check for existing signal
            existing = self.search([
                ('external_id', '=', urn),
                ('platform', '=', 'linkedin'),
            ], limit=1)

            if existing:
                # Update engagement
                existing.write({
                    'engagement_likes': likes or existing.engagement_likes,
                    'engagement_comments': comments or existing.engagement_comments,
                })
                updated += 1
            else:
                # Create new signal
                self.create({
                    'competitor_id': competitor.id,
                    'platform': 'linkedin',
                    'external_id': urn,
                    'url': f'https://www.linkedin.com/feed/update/{urn}',
                    'content': commentary[:10000] if commentary else '',
                    'author_name': competitor.name,
                    'published_at': published,
                    'engagement_likes': likes,
                    'engagement_comments': comments,
                    'state': 'new',
                    'company_id': competitor.company_id.id,
                })
                created += 1

        return created, updated

    # ── LinkedIn company resolving ──

    @api.model
    def resolve_linkedin_company(self, competitor):
        """Try to resolve a competitor's LinkedIn company public ID.

        Uses linkedin_api to search for the company by name.
        """
        if not competitor.name:
            return False

        try:
            from linkedin_api import Linkedin
            credentials = self._get_linkedin_credentials()
            if not credentials:
                return False

            api = Linkedin(*credentials)
            companies = api.search_companies(keywords=[competitor.name])

            if not companies:
                _logger.warning('LinkedIn resolve: no company found for %s', competitor.name)
                competitor.write({
                    'competitor_linkedin_pull_state': 'not_found',
                })
                return False

            # Take first result
            company = companies[0]
            public_id = company.get('publicIdentifier', company.get('urn', ''))
            if public_id:
                competitor.write({
                    'competitor_linkedin_public_id': public_id,
                    'competitor_linkedin_pull_state': 'ok',
                })
                _logger.info('LinkedIn resolved %s → %s', competitor.name, public_id)
                return True

        except Exception as e:
            _logger.error('LinkedIn resolve failed for %s: %s', competitor.name, str(e))
            return False

    @api.model
    def action_resolve_linkedin(self):
        """Resolve LinkedIn company IDs for all competitors without one."""
        competitors = self.env['marketing.world.competitor'].search([
            '|',
            ('competitor_linkedin_public_id', '=', False),
            ('competitor_linkedin_pull_state', '=', 'unknown'),
        ])
        resolved = 0
        for comp in competitors:
            if self.resolve_linkedin_company(comp):
                resolved += 1
        return resolved

    # ── YouTube pull ──

    @api.model
    def cron_pull_youtube(self):
        """Pull YouTube videos for all tracked competitors.

        Uses RSS as primary method, optionally enriches with Data API v3.
        Called by ir.cron every 6 hours.
        """
        import xml.etree.ElementTree as ET
        import requests as req

        _logger.info('YouTube monitor: starting pull cycle')
        api_key = self._get_youtube_api_key()
        competitors = self.env['marketing.world.competitor'].search([
            ('competitor_youtube_channel_id', '!=', False),
        ])

        if not competitors:
            _logger.info('YouTube monitor: no competitors with channel IDs')
            return {'processed': 0}

        total_created = 0
        total_updated = 0

        for competitor in competitors:
            try:
                channel_id = competitor.competitor_youtube_channel_id.strip()
                if not channel_id:
                    continue

                # 1. Fetch via RSS (always)
                rss_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
                resp = req.get(rss_url, timeout=15)

                if resp.status_code != 200:
                    _logger.warning(
                        'YouTube RSS failed for %s: HTTP %d',
                        competitor.name, resp.status_code,
                    )
                    continue

                root = ET.fromstring(resp.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom',
                      'yt': 'http://www.youtube.com/xml/schemas/2015'}

                # 2. Optionally fetch stats from Data API v3
                stats_map = {}
                if api_key:
                    stats_map = self._fetch_youtube_stats_batch(
                        channel_id, api_key, root, ns,
                    )

                # 3. Process each entry
                for entry in root.findall('atom:entry', ns):
                    video_id_el = entry.find('yt:videoId', ns)
                    if video_id_el is None:
                        continue
                    video_id = video_id_el.text

                    title_el = entry.find('atom:title', ns)
                    published_el = entry.find('atom:published', ns)
                    desc_el = entry.find('atom:content', ns)
                    author_el = entry.find('atom:author/atom:name', ns)
                    link_el = entry.find('atom:link', ns)

                    title = title_el.text if title_el is not None else ''
                    published_str = published_el.text if published_el is not None else ''
                    description = desc_el.text if desc_el is not None else ''
                    author = author_el.text if author_el is not None else ''
                    video_url = link_el.get('href') if link_el is not None else ''

                    # Parse date
                    try:
                        published_dt = datetime.fromisoformat(
                            published_str.replace('Z', '+00:00')
                        )
                    except (ValueError, AttributeError):
                        published_dt = fields.Datetime.now()

                    # Get stats from API if available
                    stats = stats_map.get(video_id, {})

                    # Check for existing
                    existing = self.search([
                        ('external_id', '=', video_id),
                        ('platform', '=', 'youtube'),
                    ], limit=1)

                    if existing:
                        upd = {}
                        for eng_field, api_field in [
                            ('engagement_likes', 'likeCount'),
                            ('engagement_comments', 'commentCount'),
                            ('youtube_view_count', 'viewCount'),
                        ]:
                            val = stats.get(api_field)
                            if val is not None and val != existing[eng_field]:
                                upd[eng_field] = int(val)
                        if upd:
                            existing.write(upd)
                            total_updated += 1
                    else:
                        self.create({
                            'competitor_id': competitor.id,
                            'platform': 'youtube',
                            'external_id': video_id,
                            'url': video_url or f'https://www.youtube.com/watch?v={video_id}',
                            'content': f'{title}\n\n{description[:5000]}' if description else title,
                            'author_name': author or competitor.name,
                            'published_at': published_dt,
                            'engagement_likes': int(stats.get('likeCount', 0)) if stats else 0,
                            'engagement_comments': int(stats.get('commentCount', 0)) if stats else 0,
                            'youtube_view_count': int(stats.get('viewCount', 0)) if stats else 0,
                            'state': 'new',
                            'company_id': competitor.company_id.id,
                        })
                        total_created += 1

                # Update competitor pull time
                competitor.write({
                    'competitor_youtube_last_pull': fields.Datetime.now(),
                })

            except Exception as e:
                _logger.error(
                    'YouTube pull failed for %s: %s',
                    competitor.name, str(e), exc_info=True,
                )

        _logger.info(
            'YouTube monitor: %d created, %d updated',
            total_created, total_updated,
        )
        return {'created': total_created, 'updated': total_updated}

    @api.model
    def _get_youtube_api_key(self):
        """Read YouTube API key from settings."""
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('competitor_youtube.api_key', '')

    @api.model
    def _fetch_youtube_stats_batch(self, channel_id, api_key, root, ns):
        """Fetch video statistics from YouTube Data API v3.

        Returns dict of {video_id: {stat_fields}}.
        """
        import requests as req

        # Collect video IDs from RSS
        video_ids = []
        for entry in root.findall('atom:entry', ns):
            vid = entry.find('yt:videoId', ns)
            if vid is not None:
                video_ids.append(vid.text)

        if not video_ids:
            return {}

        # Batch query — API supports up to 50 IDs per request
        ids_param = ','.join(video_ids[:50])
        url = (
            'https://www.googleapis.com/youtube/v3/videos'
            f'?part=statistics&id={ids_param}&key={api_key}'
        )

        try:
            resp = req.get(url, timeout=10)
            if resp.status_code != 200:
                _logger.warning('YouTube API error: %s', resp.text[:200])
                return {}

            data = resp.json()
            stats_map = {}
            for item in data.get('items', []):
                vid = item.get('id', '')
                stats = item.get('statistics', {})
                if vid and stats:
                    stats_map[vid] = stats
            return stats_map

        except Exception as e:
            _logger.warning('YouTube API batch failed: %s', str(e))
            return {}

    # ── YouTube channel resolving ──

    @api.model
    def resolve_youtube_channel(self, competitor):
        """Try to find a YouTube channel for a competitor by name or website."""
        if not competitor.name and not competitor.website:
            return False

        api_key = self._get_youtube_api_key()
        if not api_key:
            _logger.warning('YouTube resolve: no API key configured')
            return False

        import requests as req

        # Try search by name
        query = competitor.website or competitor.name
        url = (
            'https://www.googleapis.com/youtube/v3/search'
            f'?part=snippet&q={req.utils.quote(query)}'
            f'&type=channel&maxResults=5&key={api_key}'
        )

        try:
            resp = req.get(url, timeout=10)
            if resp.status_code != 200:
                return False

            data = resp.json()
            items = data.get('items', [])

            for item in items:
                channel_id = item.get('id', {}).get('channelId', '')
                title = item.get('snippet', {}).get('title', '')
                if channel_id and title:
                    # Verify it's the right competitor
                    if competitor.name.lower() in title.lower():
                        competitor.write({
                            'competitor_youtube_channel_id': channel_id,
                        })
                        _logger.info(
                            'YouTube resolved %s → %s (%s)',
                            competitor.name, channel_id, title,
                        )
                        return True

            _logger.info(
                'YouTube resolve: no channel found for %s',
                competitor.name,
            )
            return False

        except Exception as e:
            _logger.error('YouTube resolve failed: %s', str(e))
            return False

    # ─── Resolve all ──

    @api.model
    def cron_resolve_all(self):
        """Resolve LinkedIn and YouTube IDs for all competitors missing them."""
        self.action_resolve_linkedin()

        competitors = self.env['marketing.world.competitor'].search([
            ('competitor_youtube_channel_id', '=', False),
        ])
        for comp in competitors:
            self.resolve_youtube_channel(comp)

    # ── AI Scoring ──

    @api.model
    def cron_score_signals(self):
        """Score all new signals with AI classification.

        Classifies signal_type, relevance, and sentiment based on content patterns.
        Called by ir.cron or can be triggered on-demand.
        """
        signals = self.search([('state', '=', 'new')])
        if not signals:
            return {'scored': 0}

        scored = 0
        for signal in signals:
            try:
                self._score_signal(signal)
                scored += 1
            except Exception as e:
                _logger.error('Scoring failed for signal %s: %s', signal.id, str(e))

        _logger.info('AI scoring: %d/%d signals scored', scored, len(signals))
        return {'scored': scored}

    @api.model
    def _score_signal(self, signal):
        """Classify a single signal using pattern-based heuristics.

        Sets signal_type, ai_score, ai_relevance, sentiment, ai_analysis.
        """
        content = (signal.content or '').lower()
        text_length = len(content)

        # ── Signal Type Classification ──
        signal_type = self._classify_signal_type(content)
        if signal_type == 'other':
            signal_type = 'general_update'

        # ── Scoring ──
        score = 0

        # Strategic relevance (3×, max 45)
        strategic_weight = 0
        if signal_type in ('product_launch', 'funding'):
            strategic_weight = 15
        elif signal_type in ('pricing_change', 'positioning_shift', 'hire'):
            strategic_weight = 12
        elif signal_type in ('partnership', 'complaint'):
            strategic_weight = 8
        elif signal_type == 'customer_case':
            strategic_weight = 6
        elif signal_type == 'general_update':
            strategic_weight = 3
        score += strategic_weight * 3

        # Novelty (2×, max 20)
        novelty = 0
        # Check if this mentions something new/different
        novelty_keywords = ['announcing', 'launching', 'introducing', 'new', 'first',
                            'excited to share', 'today we', 'introducing', 'next chapter']
        found_novelty = sum(1 for kw in novelty_keywords if kw in content)
        novelty = min(10, found_novelty * 3)
        score += novelty * 2

        # Urgency (2×, max 20)
        urgency = 0
        urgency_keywords = ['immediately', 'urgent', 'breaking', 'now available',
                            'starting today', 'limited time', 'deadline']
        found_urgency = sum(1 for kw in urgency_keywords if kw in content)
        urgency = min(10, found_urgency * 3)
        score += urgency * 2

        # Engagement signal (1×, max 15)
        engagement_score = 0
        total_eng = signal.engagement_total or 0
        if total_eng > 1000:
            engagement_score = 15
        elif total_eng > 500:
            engagement_score = 12
        elif total_eng > 100:
            engagement_score = 8
        elif total_eng > 10:
            engagement_score = 4
        score += engagement_score

        # Cap at 100
        score = min(100, score)

        # ── AI Relevance ──
        if score >= 60:
            relevance = 'high'
        elif score >= 30:
            relevance = 'medium'
        elif score >= 10:
            relevance = 'low'
        else:
            relevance = 'noise'

        # ── Sentiment ──
        sentiment = self._classify_sentiment(content)

        # ── Analysis text ──
        analysis = (
            f'**Signal Type**: {signal_type}\n'
            f'**Score**: {score}/100\n'
            f'**Relevance**: {relevance}\n'
            f'**Sentiment**: {sentiment}\n\n'
            f'**Scoring breakdown**:\n'
            f'- Strategic relevance: {strategic_weight}/15\n'
            f'- Novelty signals: {novelty}/10\n'
            f'- Urgency signals: {urgency}/10\n'
            f'- Engagement: {engagement_score}/15\n\n'
            f'**Classification patterns**:\n'
            f'{self._explain_classification(content, signal_type)}\n'
        )

        # Write
        signal.write({
            'signal_type': signal_type,
            'ai_score': score,
            'ai_relevance': relevance,
            'sentiment': sentiment,
            'ai_analysis': analysis,
            'ai_classified_at': fields.Datetime.now(),
            'state': 'triaged',
        })

    @api.model
    def _classify_signal_type(self, content):
        """Classify signal type from content using pattern matching."""
        patterns = {
            'product_launch': [
                r'\b(announcing|launching|introducing|new\s+(product|feature|platform))\b',
                r'\b(today we(\'re| are)\s+(launch|announce|introduce))\b',
                r'\b(excited to (announce|share|launch|introduce))\b',
            ],
            'hire': [
                r'\b(welcome|joining\s+(the\s+)?team|appointed\s+(as|to))\b',
                r'\b(new\s+(head|vp|director|chief|president))\b',
                r'\b(promot|hire|hiring)\b.*\b(vp|head|director|chief)\b',
            ],
            'funding': [
                r'\b(raised|series\s+[a-e]|funding|investment|investor)\b',
                r'\b(\$[\d.]+\s*[mkb])\b.*\b(funding|raise|series)\b',
            ],
            'partnership': [
                r'\b(partner(ed|ing)?\s+(with|on)|integration\s+with|collaborat)\b',
                r'\b(new\s+partnership|strategic\s+(alliance|partnership))\b',
            ],
            'customer_case': [
                r'\b(customer\s+(story|success|case)|how\s+\w+\s+(uses|implemented))\b',
                r'\b(case\s+study|success\s+story)\b',
            ],
            'pricing_change': [
                r'\b(pricing|price|plan|tier|subscription)\b',
                r'\b(now\s+(starting\s+)?at|from\s+\$|free\s+tier)\b',
            ],
            'positioning_shift': [
                r'\b(we(\'re|\s+are)\s+(now|evolving|transforming|reimagining))\b',
                r'\b(new\s+(vision|mission|direction|chapter|era))\b',
            ],
            'complaint': [
                r'\b(sorry|apologize|apology|outage|downtime|issue|incident)\b',
                r'\b(we(\'re|\s+are)\s+(sorry|working\s+on\s+fixing))\b',
            ],
        }

        for stype, stype_patterns in patterns.items():
            for pattern in stype_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return stype

        return 'other'

    @api.model
    def _classify_sentiment(self, content):
        """Classify sentiment from content."""
        positive = [
            r'\b(excited|thrilled|delighted|proud|honored|grateful|incredible)\b',
            r'\b(growth|record|milestone|achievement|success|breakthrough)\b',
            r'\b(love|amazing|fantastic|excellent|outstanding)\b',
        ]
        negative = [
            r'\b(sorry|apologize|regret|unfortunately|difficult|challenge)\b',
            r'\b(outage|downtime|issue|problem|bug|error|delay)\b',
            r'\b(layoff|restructur|declin|loss|cut)\b',
        ]

        pos_score = 0
        neg_score = 0
        for p in positive:
            if re.search(p, content, re.IGNORECASE):
                pos_score += 1
        for n in negative:
            if re.search(n, content, re.IGNORECASE):
                neg_score += 1

        if pos_score > 0 and neg_score == 0:
            return 'positive'
        elif neg_score > 0 and pos_score == 0:
            return 'negative'
        elif pos_score > 0 and neg_score > 0:
            return 'mixed'
        else:
            return 'neutral'

    @api.model
    def _explain_classification(self, content, signal_type):
        """Generate explanation text for why a signal was classified a certain way."""
        explanations = []
        patterns = {
            'product_launch': 'Matches launch/announcement keywords',
            'hire': 'Mentions hiring, new role, or team expansion',
            'funding': 'Contains funding, investment, or raise language',
            'partnership': 'References partnership or integration',
            'customer_case': 'Describes customer success or case study',
            'pricing_change': 'Discusses pricing, plans, or tiers',
            'positioning_shift': 'Suggests repositioning or new direction',
            'complaint': 'Contains apology or incident language',
            'general_update': 'General company update without strong signals',
        }
        explanations.append(patterns.get(signal_type, 'Unclassified'))
        return '\n'.join(f'- {e}' for e in explanations)

    # ── Pull all (combined cron) ──

    @api.model
    def cron_pull_all(self):
        """Run all social pulls and scoring in sequence."""
        results = {}
        results['linkedin'] = self.cron_pull_linkedin()
        results['youtube'] = self.cron_pull_youtube()
        results['scored'] = self.cron_score_signals()
        results['timestamp'] = fields.Datetime.now().isoformat()
        _logger.info(
            'Social Monitor Pull complete: LinkedIn=%(linkedin)s, '
            'YouTube=%(youtube)s, Scored=%(scored)s',
            results,
        )
        return results
