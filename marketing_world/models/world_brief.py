# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MarketingWorldBrief(models.Model):
    """AI-generated weekly world monitoring briefs per customer."""

    _name = 'marketing.world.brief'
    _description = 'World Monitor Brief'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_end desc, id desc'
    _rec_name = 'name'

    # ── Identity ──
    name = fields.Char('Name', required=True, compute='_compute_name', store=True)
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True,
        domain="[('is_company', '=', True)]",
        ondelete='cascade',
    )
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)

    # ── Content ──
    summary = fields.Text('Summary', help='AI-generated analysis text')
    event_ids = fields.Many2many(
        'marketing.world.event', 'world_brief_event_rel',
        'brief_id', 'event_id',
        string='Linked Events',
    )
    event_count = fields.Integer('Event Count', compute='_compute_event_count', store=True)
    risk_changes = fields.Text('Risk Changes',
                                help='Changes in risk posture since last brief')

    # ── AI Metadata ──
    ai_model = fields.Char('AI Model', help='Which AI model generated this brief')
    ai_prompt_tokens = fields.Integer('Prompt Tokens')
    ai_completion_tokens = fields.Integer('Completion Tokens')

    # ─── Markdown output ──
    body_markdown = fields.Text(
        'Markdown Body',
        help='Full brief in Markdown format for AI consumption and export',
    )

    # ── Links ──
    plan_ids = fields.Many2many(
        'strategy.plan', 'world_brief_strategy_plan_rel',
        'brief_id', 'plan_id',
        string='Linked Plans',
        help='All strategic plans that reference this brief',
    )
    previous_brief_id = fields.Many2one(
        'marketing.world.brief', string='Previous Brief',
        help='Previous brief for comparison',
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('customer_id', 'period_start', 'period_end')
    def _compute_name(self):
        for record in self:
            customer = record.customer_id
            customer_name = customer.name if customer else _('Unknown')
            if record.period_start and record.period_end:
                # ISO week number
                try:
                    week_num = record.period_start.isocalendar()[1]
                    year = record.period_start.year
                    record.name = _('Omvärldsanalys v%s — %s') % (week_num, customer_name)
                except (ValueError, AttributeError):
                    record.name = _('Omvärldsanalys — %s') % customer_name
            else:
                record.name = _('Omvärldsanalys — %s') % customer_name

    @api.depends('event_ids')
    def _compute_event_count(self):
        for record in self:
            record.event_count = len(record.event_ids)

    # ── Brief generation ──

    def _generate_body_markdown(self):
        """Generate Markdown representation from the brief data."""
        self.ensure_one()
        if not self.summary:
            self.body_markdown = ''
            return

        customer = self.customer_id
        lines = []
        lines.append('---')
        lines.append('title: "Omvärldsanalys"')
        lines.append(f'customer: "{customer.name}"')
        lines.append(f'customer_id: {customer.id}')
        lines.append(f'period_start: {self.period_start}')
        lines.append(f'period_end: {self.period_end}')
        lines.append(f'ai_model: "{self.ai_model or "N/A"}"')
        lines.append(f'source: "World Monitor"')
        lines.append(f'generated_at: "{fields.Datetime.now().isoformat()}"')
        lines.append(f'event_count: {self.event_count}')
        lines.append('---')
        lines.append('')
        lines.append(f'# Omvärldsanalys — {customer.name}')
        lines.append('')
        lines.append(f'**Period:** {self.period_start} — {self.period_end}')
        lines.append(f'**AI Model:** {self.ai_model or "N/A"}')
        lines.append(f'**Events Analyzed:** {self.event_count}')
        lines.append('')
        lines.append('## Sammanfattning')
        lines.append('')
        lines.append(self.summary or '*Ingen sammanfattning tillgänglig*')
        lines.append('')

        if self.event_ids:
            lines.append('## Väsentliga händelser')
            lines.append('')
            for event in self.event_ids.sorted(key=lambda e: e.date):
                severity_icon = {
                    'critical': '🔴', 'high': '🟠', 'medium': '🟡',
                    'low': '🟢', 'info': '🔵',
                }.get(event.severity, '⚪')
                lines.append(f'- {severity_icon} **[{event.severity.upper()}]** '
                              f'{event.name}')
                if event.summary:
                    lines.append(f'  - {event.summary[:200]}')
                if event.url:
                    lines.append(f'  - [Källa]({event.url})')
            lines.append('')

        if self.risk_changes:
            lines.append('## Riskförändringar')
            lines.append('')
            lines.append(self.risk_changes)
            lines.append('')

        # Recommendations section if we have events
        if self.event_ids:
            lines.append('## Rekommendationer')
            lines.append('')
            critical_events = self.event_ids.filtered(lambda e: e.severity == 'critical')
            high_events = self.event_ids.filtered(lambda e: e.severity == 'high')
            if critical_events:
                lines.append('### 🔴 Omedelbar åtgärd krävs')
                for e in critical_events:
                    if e.risk_ids:
                        lines.append(f'- {e.name} — se risk #{e.risk_ids[0].id}')
                    else:
                        lines.append(f'- {e.name}')
            if high_events:
                lines.append('### 🟠 Bevaka noga')
                for e in high_events:
                    lines.append(f'- {e.name}')
            lines.append('')

        self.body_markdown = '\n'.join(lines)

    # ── Cron methods ──

    @api.model
    def cron_generate_briefs(self):
        """Generate weekly briefs for all enabled customers.
        Called by ir.cron weekly on Monday 08:00.
        """
        now = fields.Date.today()
        period_end = now
        period_start = now - timedelta(days=7)

        # Find all companies with auto-brief enabled
        enabled_companies = self.env['res.company'].search([
            ('world_monitor_enabled', '=', True),
            ('world_monitor_auto_brief', '=', True),
        ])

        generated = 0
        for company in enabled_companies:
            try:
                # Find customers with relevant events this week
                events = self.env['marketing.world.event'].search([
                    ('state', 'in', ('relevant', 'escalated')),
                    ('date', '>=', fields.Datetime.to_datetime(period_start)),
                    ('date', '<=', fields.Datetime.to_datetime(period_end) + timedelta(days=1)),
                    ('company_id', '=', company.id),
                ])

                # Group by customer
                customer_events = {}
                for event in events:
                    cid = event.customer_id.id or 0
                    if cid not in customer_events:
                        customer_events[cid] = self.env['marketing.world.event']
                    customer_events[cid] |= event

                for cid, c_events in customer_events.items():
                    if not c_events:
                        continue

                    partner = self.env['res.partner'].browse(cid) if cid else False

                    # Find previous brief for this customer
                    previous_brief = self.search([
                        ('customer_id', '=', partner.id),
                        ('company_id', '=', company.id),
                    ], limit=1, order='period_end desc')

                    # Build summary from event data
                    summary_parts = []
                    by_category = {}
                    for event in c_events:
                        cat = event.category
                        if cat not in by_category:
                            by_category[cat] = []
                        by_category[cat].append(event)

                    for cat, cat_events in sorted(by_category.items()):
                        cat_label = dict(c_events.fields_get(['category'])['category']['selection']).get(cat, cat)
                        summary_parts.append(f'**{cat_label}** ({len(cat_events)} händelser):')
                        for e in cat_events[:5]:  # Top 5 per category
                            summary_parts.append(f'- {e.name} ({e.severity})')
                        if len(cat_events) > 5:
                            summary_parts.append(f'- ...och {len(cat_events)-5} till')

                    summary = '\n'.join(summary_parts)

                    # Risk changes
                    risk_changes = ''
                    escalated = c_events.filtered(lambda e: e.state == 'escalated')
                    if escalated:
                        risk_changes = 'Nya/escalerade risker:\n'
                        for e in escalated:
                            risk_changes += f'- {e.name} (severity: {e.severity})\n'

                    # Generate markdown
                    brief_vals = {
                        'customer_id': partner.id if partner else False,
                        'period_start': period_start,
                        'period_end': period_end,
                        'summary': summary or _('Inga väsentliga händelser denna vecka.'),
                        'event_ids': [(6, 0, c_events.ids)],
                        'risk_changes': risk_changes,
                        'company_id': company.id,
                        'previous_brief_id': previous_brief.id if previous_brief else False,
                        'ai_model': 'batch-generated',
                    }

                    brief = self.create(brief_vals)
                    brief._generate_body_markdown()
                    generated += 1

            except Exception as e:
                _logger.error('Brief generation failed for company %s: %s',
                               company.name, str(e))

        _logger.info('World Brief Generator: %d briefs generated', generated)
        return generated

    # ── Manual regeneration ──

    def action_regenerate(self):
        """Regenerate the brief's Markdown body."""
        for record in self:
            record._generate_body_markdown()

    def action_export_markdown(self):
        """Return the Markdown body for export/download."""
        self.ensure_one()
        self._generate_body_markdown()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/body_markdown/'
                   f'{self.name.replace("/", "_")}.md',
            'target': 'download',
        }
