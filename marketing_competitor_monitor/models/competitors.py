# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from datetime import timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MarketingWorldCompetitor(models.Model):
    """Extend marketing.world.competitor with social monitoring fields."""

    _inherit = 'marketing.world.competitor'

    # ── LinkedIn ──
    competitor_linkedin_public_id = fields.Char(
        'LinkedIn Company ID',
        help='LinkedIn public identifier (e.g. "meltwater" from linkedin.com/company/meltwater)',
    )
    competitor_linkedin_last_pull = fields.Datetime('Last LinkedIn Pull', readonly=True)
    competitor_linkedin_pull_state = fields.Selection([
        ('unknown', 'Unknown'),
        ('ok', 'OK'),
        ('not_found', 'Not Found'),
        ('challenge', 'CHALLENGE'),
        ('error', 'Error'),
    ], string='LinkedIn Status', default='unknown')

    # ── YouTube ──
    competitor_youtube_channel_id = fields.Char(
        'YouTube Channel ID',
        help='YouTube channel ID (from channel URL or search)',
    )
    competitor_youtube_last_pull = fields.Datetime('Last YouTube Pull', readonly=True)

    # ── Social signals (computed) ──
    social_signal_ids = fields.One2many(
        'competitor.social.signal', 'competitor_id',
        string='Social Signals',
    )
    social_signal_count = fields.Integer(
        'Social Signals',
        compute='_compute_social_signal_count',
        store=True,
    )
    last_social_signal_at = fields.Datetime(
        'Last Social Signal',
        compute='_compute_last_social_signal_at',
        store=False,
    )

    # ── Social summary (computed for battle card) ──
    social_posting_frequency_30d = fields.Integer(
        'Posts (30d)',
        compute='_compute_social_stats_30d',
    )
    social_avg_engagement_30d = fields.Float(
        'Avg Engagement (30d)',
        compute='_compute_social_stats_30d',
    )

    @api.depends('social_signal_ids')
    def _compute_social_signal_count(self):
        for record in self:
            record.social_signal_count = len(record.social_signal_ids)

    @api.depends('social_signal_ids')
    def _compute_last_social_signal_at(self):
        for record in self:
            if record.social_signal_ids:
                record.last_social_signal_at = record.social_signal_ids[0].published_at
            else:
                record.last_social_signal_at = False

    def _compute_social_stats_30d(self):
        """Compute 30-day social stats for the battle card trend indicator."""
        Signal = self.env['competitor.social.signal']
        cutoff = fields.Datetime.now() - timedelta(days=30)
        for record in self:
            recent = Signal.search([
                ('competitor_id', '=', record.id),
                ('published_at', '>=', cutoff),
            ])
            record.social_posting_frequency_30d = len(recent)
            if recent:
                total_eng = sum(
                    (s.engagement_likes or 0) +
                    (s.engagement_comments or 0) +
                    (s.engagement_shares or 0) +
                    (s.youtube_view_count or 0)
                    for s in recent
                )
                record.social_avg_engagement_30d = round(total_eng / len(recent), 1)
            else:
                record.social_avg_engagement_30d = 0.0

    # ── Actions ──

    def action_open_social_signals(self):
        """Open social signals for this competitor."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Social Signals — %s') % self.name,
            'res_model': 'competitor.social.signal',
            'view_mode': 'tree,form',
            'domain': [('competitor_id', '=', self.id)],
            'context': {
                'default_competitor_id': self.id,
                'search_default_group_type': 1,
            },
        }

    def action_pull_linkedin(self):
        """On-demand LinkedIn pull for this competitor."""
        self.ensure_one()
        signal_model = self.env['competitor.social.signal']
        # Resolve LinkedIn ID if missing
        if not self.competitor_linkedin_public_id:
            signal_model.resolve_linkedin_company(self)
        # Run pull via the cron method but filtered
        return signal_model.cron_pull_linkedin()

    def action_pull_youtube(self):
        """On-demand YouTube pull for this competitor."""
        self.ensure_one()
        signal_model = self.env['competitor.social.signal']
        if not self.competitor_youtube_channel_id:
            signal_model.resolve_youtube_channel(self)
        return signal_model.cron_pull_youtube()

    def action_resolve_social_ids(self):
        """Resolve both LinkedIn and YouTube IDs."""
        self.ensure_one()
        signal_model = self.env['competitor.social.signal']
        results = {}
        results['linkedin'] = signal_model.resolve_linkedin_company(self)
        results['youtube'] = signal_model.resolve_youtube_channel(self)
        return results

    # ── Battle card integration ──

    def action_pull_and_generate(self):
        """Pull social signals then generate battle card."""
        self.ensure_one()
        signal_model = self.env['competitor.social.signal']
        signal_model.cron_pull_linkedin()
        signal_model.cron_pull_youtube()
        signal_model.cron_score_signals()
        return self.action_generate_battle_card()

    def get_social_signal_data_for_battle_card(self):
        """Return structured social signal data for battle card generation.

        Returns a dict with:
        - recent_signals: list of recent signal summaries
        - trend_30d: dict with posting frequency, avg engagement, top topics, sentiment
        - signals_by_type: dict grouping signals by signal_type
        """
        self.ensure_one()
        Signal = self.env['competitor.social.signal']
        now = fields.Datetime.now()
        cutoff_30d = now - timedelta(days=30)
        cutoff_7d = now - timedelta(days=7)

        recent = Signal.search([
            ('competitor_id', '=', self.id),
            ('state', '!=', 'archived'),
        ], order='published_at desc', limit=30)

        recent_30d = recent.filtered(lambda s: s.published_at and s.published_at >= cutoff_30d)
        recent_7d = recent.filtered(lambda s: s.published_at and s.published_at >= cutoff_7d)

        # Signal summaries for timeline
        signal_summaries = []
        for s in recent[:20]:
            first_line = (s.content or '')[:100].strip()
            platform_icon = '💼' if s.platform == 'linkedin' else '📺'
            signal_summaries.append({
                'icon': platform_icon,
                'platform': s.platform,
                'type': dict(s._fields['signal_type'].selection).get(s.signal_type, s.signal_type),
                'content': first_line,
                'date': str(s.published_at.date()) if s.published_at else '—',
                'url': s.url or '',
                'engagement': s.engagement_total or 0,
            })

        # 30-day trend
        posting_freq = len(recent_30d)
        avg_eng = 0.0
        if recent_30d:
            total_eng = sum(
                (s.engagement_likes or 0) + (s.engagement_comments or 0) +
                (s.engagement_shares or 0) + (s.youtube_view_count or 0)
                for s in recent_30d
            )
            avg_eng = round(total_eng / len(recent_30d), 1)

        # Top topics (signal types) in last 30 days
        type_counts = {}
        for s in recent_30d:
            st = s.signal_type or 'other'
            type_counts[st] = type_counts.get(st, 0) + 1
        sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
        top_topics = []
        for stype, count in sorted_types[:5]:
            label = dict(s._fields['signal_type'].selection).get(stype, stype)
            pct = round(count / posting_freq * 100) if posting_freq > 0 else 0
            top_topics.append({'type': label, 'count': count, 'pct': pct})

        # Sentiment distribution
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0, 'mixed': 0}
        for s in recent_30d:
            sent = s.sentiment or 'neutral'
            if sent in sentiment_counts:
                sentiment_counts[sent] += 1
        sentiment_pct = {}
        for k, v in sentiment_counts.items():
            sentiment_pct[k] = round(v / posting_freq * 100) if posting_freq > 0 else 0

        # Recent 7-day count for comparison
        prev_count = len(recent_7d)

        # Signals by type for SWOT
        signals_by_type = {}
        for s in recent:
            st = s.signal_type or 'other'
            if st not in signals_by_type:
                signals_by_type[st] = []
            signals_by_type[st].append({
                'content': (s.content or '')[:200],
                'date': str(s.published_at.date()) if s.published_at else '—',
                'platform': s.platform,
            })

        return {
            'signal_count': len(recent),
            'signal_count_30d': posting_freq,
            'signal_count_7d': prev_count,
            'avg_engagement_30d': avg_eng,
            'top_topics': top_topics,
            'sentiment': sentiment_pct,
            'signal_summaries': signal_summaries,
            'signals_by_type': signals_by_type,
        }

    def action_generate_battle_card_with_social(self):
        """Generate battle card with integrated social signal data.

        Extends the standard battle card with:
        - Social signal timeline
        - 30-day trend indicator
        - SWOT insights from social data
        - Response recommendations
        """
        self.ensure_one()

        # First generate the standard battle card
        result = self.action_generate_battle_card()

        # Then get social data
        social = self.get_social_signal_data_for_battle_card()

        if social['signal_count'] == 0:
            # Add note about no signals
            current = self.battle_card or ''
            if '---' not in current:
                current += '\n\n---\n## Sociala signaler\n\n'
                current += '*Inga sociala signaler insamlade ännu. '
                current += 'Kör "Pull LinkedIn" eller "Pull YouTube" för att samla in data.*\n'
            self.write({'battle_card': current})
            return result

        # Build social section
        lines = []

        # --- Trend section ---
        lines.append('')
        lines.append('---')
        lines.append('## Sociala signaler')
        lines.append('')
        lines.append(f'**Totalt**: {social["signal_count"]} signaler '
                      f'({social["signal_count_30d"]} senaste 30 dagarna)')

        # Trend indicator
        lines.append('')
        lines.append('### 📊 30-dagars trend')
        lines.append('')
        lines.append(f'| Metrik | Värde |')
        lines.append(f'|--------|-------|')
        lines.append(f'| 📝 Inlägg (30d) | {social["signal_count_30d"]} |')
        lines.append(f'| ❤️ Genomsnittligt engagemang | {social["avg_engagement_30d"]} |')

        if social['top_topics']:
            top_str = ', '.join(
                f'{t["type"]} ({t["pct"]}%)'
                for t in social['top_topics'][:3]
            )
            lines.append(f'| 🔍 Toppämnen | {top_str} |')

        if social['sentiment']:
            sent_str = ', '.join(
                f'{k}: {v}%'
                for k, v in social['sentiment'].items()
                if v > 0
            )
            lines.append(f'| 📈 Sentiment | {sent_str} |')

        lines.append('')

        # Signal type distribution
        if social['signals_by_type']:
            lines.append('### 📋 Signaler per typ')
            lines.append('')
            for stype, signals in sorted(social['signals_by_type'].items()):
                label = dict(
                    self.env['competitor.social.signal']._fields['signal_type'].selection
                ).get(stype, stype)
                lines.append(f'- **{label}** ({len(signals)} st)')
                for s in signals[:3]:
                    lines.append(f'  - [{s["date"]}] {s["content"][:100]}')
            lines.append('')

        # Recent signal timeline
        if social['signal_summaries']:
            lines.append('### 🕐 Senaste signaler')
            lines.append('')
            lines.append('| Datum | Plattform | Typ | Innehåll |')
            lines.append('|-------|-----------|-----|----------|')
            for s in social['signal_summaries'][:10]:
                platform_icon = '💼' if s['platform'] == 'linkedin' else '📺'
                type_label = s['type'][:20] if len(s['type']) > 20 else s['type']
                content = s['content'][:60] if s['content'] else '—'
                lines.append(f'| {s["date"]} | {platform_icon} | {type_label} | {content} |')
            lines.append('')

        # SWOT insights from social data
        lines.append('### 🔍 SWOT-insikter från sociala signaler')
        lines.append('')

        # Threats: look for product launches, funding, partnership
        threat_types = {'product_launch', 'funding', 'partnership', 'positioning_shift'}
        threats = []
        opportunities = []
        for stype, signals in social['signals_by_type'].items():
            if stype in threat_types:
                for s in signals[:3]:
                    threats.append(f'- {s["content"][:100]} ({s["date"]})')
            if stype == 'complaint':
                opportunities.append(f'- {s["content"][:100]} ({s["date"]})')

        if threats:
            lines.append('**Hot** (nya rörelser från konkurrenten):')
            lines.extend(threats[:5])
            lines.append('')

        if opportunities:
            lines.append('**Möjligheter** (svagheter hos konkurrenten):')
            lines.extend(opportunities[:3])
            lines.append('')
        else:
            lines.append('*Inga tydliga svagheter identifierade från sociala signaler.*')
            lines.append('')

        # Engagement trend
        if social['signal_count_30d'] > 0:
            if social['avg_engagement_30d'] > 100:
                lines.append('- 🟢 **Högt engagemang** — deras inlägg får mycket uppmärksamhet')
            elif social['avg_engagement_30d'] > 20:
                lines.append('- 🟡 **Måttligt engagemang** — de når sin publik')
            else:
                lines.append('- 🔴 **Lågt engagemang** — svag publikrespons')
            lines.append('')

        lines.append('_Sociala signaler uppdateras var 6:e timme från LinkedIn och YouTube._')
        lines.append('')

        social_text = '\n'.join(lines)

        # Append to existing battle card (before the closing ---)
        current = self.battle_card or ''
        if current:
            # Insert before the last ---
            if current.rstrip().endswith('---'):
                # Remove final --- and replace with social data + ---
                current = current.rstrip()
                if current.endswith('---'):
                    current = current[:-3].rstrip()
            current += social_text
            current += '\n---'

        self.write({
            'battle_card': current or social_text,
            'battle_card_updated': fields.Datetime.now(),
        })

        _logger.info(
            'Battle card with social generated for %s (%d signals)',
            self.name, social['signal_count'],
        )
        return result
