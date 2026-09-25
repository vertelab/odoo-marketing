# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MarketingWorldEvent(models.Model):
    """Structured world monitoring events from World Monitor."""

    _name = 'marketing.world.event'
    _description = 'World Monitor Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    # ── Identity & Source ──
    name = fields.Char('Title', required=True, tracking=True)
    source = fields.Char('Source', default='world_monitor',
                          help='Source identifier (world_monitor, manual, etc.)')
    url = fields.Char('URL', help='Original source URL')
    summary = fields.Text('Summary')
    full_text = fields.Text('Full Text')
    wm_raw = fields.Json('World Monitor Raw Data',
                          help='Complete WM response for future re-analysis')

    # ── Classification ──
    category = fields.Selection([
        ('geopolitical', 'Geopolitical'),
        ('economic', 'Economic'),
        ('cyber', 'Cyber Security'),
        ('climate', 'Climate & Environment'),
        ('health', 'Health'),
        ('tech', 'Technology'),
        ('supply_chain', 'Supply Chain'),
        ('regulatory', 'Regulatory'),
        ('competitor', 'Competitor'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other', tracking=True)

    severity = fields.Selection([
        ('info', 'Info'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='info', tracking=True)

    country_id = fields.Many2one('res.country', string='Country')

    # ── State Machine ──
    state = fields.Selection([
        ('new', 'New'),
        ('triaged', 'Triaged'),
        ('relevant', 'Relevant'),
        ('irrelevant', 'Irrelevant'),
        ('escalated', 'Escalated'),
        ('archived', 'Archived'),
    ], string='State', required=True, default='new', tracking=True)

    # ── AI Analysis ──
    ai_relevance = fields.Selection([
        ('direct', 'Direct Relevance'),
        ('indirect', 'Indirect Relevance'),
        ('monitor', 'Monitor Only'),
        ('none', 'No Relevance'),
    ], string='AI Relevance', readonly=True)
    ai_analysis = fields.Text('AI Analysis', readonly=True,
                               help="AI's reasoning for relevance assessment")
    ai_triaged_at = fields.Datetime('AI Triaged At', readonly=True)
    ai_model = fields.Char('AI Model', readonly=True)
    ai_prompt_tokens = fields.Integer('Prompt Tokens', readonly=True)
    ai_completion_tokens = fields.Integer('Completion Tokens', readonly=True)

    # ── Links ──
    risk_ids = fields.Many2many(
        'strategy.risk', 'world_event_strategy_risk_rel',
        'event_id', 'risk_id',
        string='Linked Risks',
        help='Strategy risks escalated from this event',
    )
    plan_id = fields.Many2one('strategy.plan', string='Strategic Plan',
                               ondelete='set null')
    customer_id = fields.Many2one('res.partner', string='Customer',
                                   domain="[('is_company', '=', True)]",
                                   ondelete='set null')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    # ── Time fields ──
    date = fields.Datetime('Event Date', required=True,
                            default=fields.Datetime.now)
    stale_at = fields.Datetime('Stale At',
                                help='When this event becomes stale per WM cache policy')
    source_updated_at = fields.Datetime('Source Updated At')

    # ── WM Metadata ──
    wm_event_id = fields.Char('WM Event ID', readonly=True,
                               help='World Monitor unique event identifier')
    wm_source_name = fields.Char('WM Source Name', readonly=True)
    wm_source_credibility = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Source Credibility', readonly=True)

    # ── Computed fields ──
    risk_count = fields.Integer('Risk Count', compute='_compute_risk_count', store=True)
    event_age_days = fields.Integer('Age (Days)', compute='_compute_event_age', store=False)

    _sql_constraints = [
        ('unique_wm_event_id',
         'UNIQUE(wm_event_id)',
         'A World Monitor event with this ID already exists. Duplicate detected.'),
    ]

    # ── Computes ──

    @api.depends('risk_ids')
    def _compute_risk_count(self):
        for record in self:
            record.risk_count = len(record.risk_ids)

    @api.depends('date')
    def _compute_event_age(self):
        now = fields.Datetime.now()
        for record in self:
            if record.date:
                delta = now - record.date
                record.event_age_days = delta.days
            else:
                record.event_age_days = 0

    # ── State transitions ──

    def action_triage(self):
        """Mark event as triaged (ready for AI assessment or manual review)."""
        for record in self:
            if record.state == 'new':
                record.state = 'triaged'

    def action_mark_relevant(self):
        """Mark event as relevant."""
        for record in self:
            if record.state in ('triaged', 'new'):
                record.state = 'relevant'

    def action_mark_irrelevant(self):
        """Mark event as irrelevant."""
        for record in self:
            if record.state in ('triaged', 'new'):
                record.state = 'irrelevant'

    def action_escalate(self):
        """Escalate event — creates draft strategy.risk if severity is high+."""
        self._escalate_to_risk()
        return True

    def action_archive(self):
        """Archive the event."""
        for record in self:
            if record.state not in ('archived',):
                record.state = 'archived'

    def action_reset_to_new(self):
        """Reset event to new state for re-triage."""
        for record in self:
            record.state = 'new'
            record.ai_relevance = False
            record.ai_analysis = False

    def _escalate_to_risk(self):
        """Create draft strategy.risk records for escalated events."""
        Risk = self.env['strategy.risk']
        for event in self:
            if event.state == 'escalated':
                continue
            if event.severity not in ('high', 'critical'):
                _logger.info(
                    'Event %s severity=%s — skipping escalation',
                    event.name, event.severity,
                )
                continue

            risk = Risk.create({
                'name': _('WM: %s') % event.name[:200],
                'category': self._map_category_to_risk(event.category),
                'probability': 'high' if event.severity == 'critical' else 'medium',
                'impact_description': event.summary or event.name,
                'company_id': event.company_id.id,
            })

            event.write({
                'risk_ids': [(4, risk.id)],
                'state': 'escalated',
            })

            _logger.info(
                'Escalated event %s → strategy.risk %s',
                event.name, risk.name,
            )

    @api.model
    def _map_category_to_risk(self, category):
        """Map world event category to strategy.risk category."""
        mapping = {
            'geopolitical': 'other',
            'economic': 'financial',
            'cyber': 'operational',
            'climate': 'operational',
            'health': 'operational',
            'tech': 'technology',
            'supply_chain': 'operational',
            'regulatory': 'regulatory',
            'competitor': 'competitive',
            'other': 'other',
        }
        return mapping.get(category, 'other')

    # ── Duplicate detection ──

    @api.model
    def find_by_wm_event_id(self, wm_event_id):
        """Find existing event by WM event ID for deduplication."""
        if not wm_event_id:
            return None
        return self.search([('wm_event_id', '=', wm_event_id)], limit=1)

    @api.model
    def find_existing(self, wm_event_id, name, date):
        """Find existing event by multiple criteria."""
        domain = ['|', ('wm_event_id', '=', wm_event_id or '')]
        if name:
            domain = ['|'] + domain + [('name', '=', name)]
        if date:
            domain = domain + [('date', '=', date)]
        return self.search(domain, limit=1)

    # ── Cron methods ──

    @api.model
    def cron_pull_events(self):
        """Pull latest events from World Monitor via cron.
        Called by ir.cron every 30 minutes.
        Uses company-specific filters from res.company settings.
        """
        since = fields.Datetime.now() - timedelta(hours=24)
        enabled_companies = self.env['res.company'].search([
            ('world_monitor_enabled', '=', True),
        ])
        total = {'created': 0, 'updated': 0, 'skipped': 0}
        for company in enabled_companies:
            try:
                company_ctx = self.with_company(company)
                result = company_ctx.pull_from_world_monitor(
                    since=since,
                )
                for k in total:
                    total[k] += result.get(k, 0)
            except Exception as e:
                _logger.error(
                    'World Monitor pull failed for company %s: %s',
                    company.name, str(e),
                )
        _logger.info(
            'World Monitor cron pull: %d created, %d updated, %d skipped',
            total['created'], total['updated'], total['skipped'],
        )
        return total

    @api.model
    def cron_triage_events(self):
        """Run AI triage on all new events via coworker.
        Called by ir.cron every 6 hours.
        """
        events = self.search([('state', '=', 'new')])
        if not events:
            _logger.info('World Monitor triage cron: no new events to process')
            return {'processed': 0}
        coworker = self.env['ai.coworker'].search([
            ('name', '=', 'World Intelligence Triage'),
        ], limit=1)
        if not coworker:
            _logger.warning('World Intelligence Triage coworker not found — marking events as triaged')
            events.write({'state': 'triaged'})
            return {'processed': len(events)}
        processed = 0
        for event in events:
            try:
                coworker.with_context(
                    record_model='marketing.world.event',
                    record_id=event.id,
                ).run(
                    prompt=(
                        f"Triage omvärldshändelse {event.name or event.wm_event_id}:\n"
                        f"{event.description or event.summary or ''}\n\n"
                        f"Klassificera relevans (direct/indirect/monitor) och "
                        f"föreslå ev. eskalering till strategy.risk."
                    ),
                    system_prompt=coworker.description or '',
                )
                processed += 1
            except Exception as e:
                _logger.error('Triage failed for event %s: %s', event.name, str(e))
        _logger.info(
            'World Monitor triage cron: %d/%d events sent for triage',
            processed, len(events),
        )
        return {'processed': processed}

    # ── Pull from World Monitor ──

    @api.model
    def pull_from_world_monitor(self, category=None, country=None, since=None):
        """Pull events from World Monitor and create/update records.

        Args:
            category: Filter by WM category
            country: Filter by country code
            since: Datetime — fetch events since this time

        Returns:
            dict with counts of created, updated, skipped
        """
        wm_api = self.env['world.monitor.api']
        events = wm_api.fetch_events(category=category, country=country, since=since)

        if not events:
            _logger.info('World Monitor pull: no events returned')
            return {'created': 0, 'updated': 0, 'skipped': 0}

        created = 0
        updated = 0
        skipped = 0

        for raw in events:
            wm_event_id = raw.get('id') or raw.get('wm_event_id') or ''
            name = raw.get('title') or raw.get('name') or _('Untitled Event')
            date_str = raw.get('published_at') or raw.get('date') or fields.Datetime.now()

            # Deduplicate
            existing = self.find_by_wm_event_id(wm_event_id) if wm_event_id else None
            if existing:
                # Update if stale
                if existing.state in ('new', 'triaged'):
                    existing.write({
                        'summary': raw.get('summary', existing.summary),
                        'full_text': raw.get('content', existing.full_text),
                        'url': raw.get('url', existing.url),
                        'severity': self._map_wm_severity(raw.get('severity', 'info')),
                        'source_updated_at': fields.Datetime.now(),
                    })
                    updated += 1
                else:
                    skipped += 1
                continue

            # Parse date
            try:
                if isinstance(date_str, str):
                    event_date = fields.Datetime.from_string(date_str.replace('Z', ''))
                else:
                    event_date = date_str
            except (ValueError, TypeError):
                event_date = fields.Datetime.now()

            # Create event
            vals = {
                'name': name[:256],
                'source': 'world_monitor',
                'url': raw.get('url', ''),
                'summary': raw.get('summary', ''),
                'full_text': raw.get('content', raw.get('full_text', '')),
                'wm_raw': raw,
                'wm_event_id': wm_event_id or '',
                'wm_source_name': raw.get('source_name', ''),
                'wm_source_credibility': self._map_wm_credibility(
                    raw.get('credibility', raw.get('source_credibility', 'medium'))
                ),
                'category': self._map_wm_category(raw.get('category', 'other')),
                'severity': self._map_wm_severity(raw.get('severity', 'info')),
                'country_id': self._resolve_country(raw.get('country', raw.get('country_code', ''))),
                'date': event_date,
                'state': 'new',
                'company_id': self.env.company.id,
            }
            self.create(vals)
            created += 1

        _logger.info(
            'World Monitor pull: %d created, %d updated, %d skipped',
            created, updated, skipped,
        )
        return {'created': created, 'updated': updated, 'skipped': skipped}

    @api.model
    def _map_wm_category(self, category):
        """Map WM category to our selection."""
        mapping = {
            'geopolitical': 'geopolitical', 'geopolitics': 'geopolitical',
            'economic': 'economic', 'economy': 'economic',
            'cyber': 'cyber', 'cybersecurity': 'cyber',
            'climate': 'climate', 'environment': 'climate',
            'health': 'health', 'healthcare': 'health',
            'tech': 'tech', 'technology': 'tech',
            'supply_chain': 'supply_chain', 'supplychain': 'supply_chain',
            'regulatory': 'regulatory', 'regulation': 'regulatory',
            'competitor': 'competitor', 'competitive': 'competitor',
        }
        return mapping.get(category.lower().strip(), 'other')

    @api.model
    def _map_wm_severity(self, severity):
        """Map WM severity to our selection."""
        mapping = {
            'info': 'info', 'informational': 'info',
            'low': 'low', 'minor': 'low',
            'medium': 'medium', 'moderate': 'medium',
            'high': 'high', 'major': 'high',
            'critical': 'critical', 'severe': 'critical',
        }
        return mapping.get(severity.lower().strip(), 'info')

    @api.model
    def _map_wm_credibility(self, credibility):
        """Map WM source credibility to our selection."""
        mapping = {
            '1': 'low', 'low': 'low',
            '2': 'medium', 'medium': 'medium',
            '3': 'high', 'high': 'high',
        }
        return mapping.get(str(credibility).lower().strip(), 'medium')

    @api.model
    def _resolve_country(self, country_code):
        """Resolve country code to res.country ID."""
        if not country_code:
            return False
        country = self.env['res.country'].search(
            [('code', '=ilike', country_code.strip())], limit=1
        )
        return country.id if country else False

    # ── Manual event creation ──

    @api.model
    def create_manual(self, vals):
        """Create a manually entered event (skips AI triage)."""
        vals.setdefault('source', 'manual')
        vals.setdefault('state', 'triaged')
        vals.setdefault('date', fields.Datetime.now())
        return self.create(vals)
