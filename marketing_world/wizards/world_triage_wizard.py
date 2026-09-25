# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorldTriageWizard(models.TransientModel):
    """Wizard for manual triage of world events."""

    _name = 'world.triage.wizard'
    _description = 'World Monitor Triage Wizard'

    # ── Context: which event(s) to triage ──
    event_ids = fields.Many2many(
        'marketing.world.event',
        string='Events',
        required=True,
        default=lambda self: self._default_events(),
    )
    event_count = fields.Integer(
        string='Event Count',
        compute='_compute_event_count',
    )

    # ── Triage actions ──
    action_type = fields.Selection([
        ('mark_relevant', 'Mark as Relevant'),
        ('mark_irrelevant', 'Mark as Irrelevant'),
        ('escalate_to_risk', 'Escalate to Risk'),
        ('archive', 'Archive'),
    ], string='Action', required=True, default='mark_relevant')

    # ── Escalation specifics ──
    escalation_severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Escalation Severity', default='medium')

    escalation_category = fields.Selection([
        ('market', 'Market Risk'),
        ('competitive', 'Competitive Risk'),
        ('financial', 'Financial Risk'),
        ('operational', 'Operational Risk'),
        ('regulatory', 'Regulatory Risk'),
        ('technology', 'Technology Risk'),
        ('other', 'Other'),
    ], string='Risk Category', default='market')

    escalation_notes = fields.Text('Escalation Notes')

    # ── Batch operations ──
    send_notification = fields.Boolean(
        string='Send Notification',
        default=True,
        help='Notify relevant users when events are escalated',
    )

    @api.model
    def _default_events(self):
        """Default to active event IDs passed in context."""
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            return [(6, 0, active_ids)]
        return [(5,)]

    @api.depends('event_ids')
    def _compute_event_count(self):
        for record in self:
            record.event_count = len(record.event_ids)

    def action_execute(self):
        """Execute the selected triage action on all events."""
        self.ensure_one()

        events = self.event_ids

        if not events:
            raise UserError(_('Please select at least one event to triage.'))

        action_map = {
            'mark_relevant': events.action_mark_relevant,
            'mark_irrelevant': events.action_mark_irrelevant,
            'escalate_to_risk': self._execute_escalation,
            'archive': events.action_archive,
        }

        action_fn = action_map.get(self.action_type)
        if action_fn:
            action_fn()

        if self.send_notification:
            self._send_triage_notification(events)

        return {
            'type': 'ir.actions.act_window_close',
        }

    def _execute_escalation(self):
        """Escalate selected events to strategy.risk."""
        Risk = self.env['strategy.risk']
        for event in self.event_ids:
            risk = Risk.create({
                'name': _('WM: %s') % event.name[:200],
                'category': self.escalation_category,
                'probability': 'high' if self.escalation_severity in ('high', 'critical') else 'medium',
                'impact_description': self.escalation_notes or event.summary or event.name,
                'company_id': event.company_id.id,
            })
            event.write({
                'risk_ids': [(4, risk.id)],
                'state': 'escalated',
                'ai_relevance': 'direct',
                'ai_analysis': _('Manually escalated by %s\n\nNotes: %s') % (
                    self.env.user.display_name,
                    self.escalation_notes or 'No notes',
                ),
            })

    def _send_triage_notification(self, events):
        """Send Odoo notification about triaged events."""
        if self.action_type == 'escalate_to_risk':
            # Notify users with "Strategic Risk Manager" group
            risk_group = self.env.ref('strategy_core.group_strategy_risk_manager',
                                       raise_if_not_found=False)
            if not risk_group:
                _logger.warning('Risk manager group not found — skipping notification')
                return

            users = risk_group.users
            if not users:
                _logger.info('No users in risk manager group — skipping notification')
                return

            for event in events:
                event.message_post(
                    subject=_('Risk Escalated: %s') % event.name[:100],
                    body=_(
                        '<p>Event <b>%s</b> has been escalated to a strategic risk.</p>'
                        '<p><b>Severity:</b> %s</p>'
                        '<p><b>Category:</b> %s</p>'
                        '<p><b>Notes:</b> %s</p>'
                    ) % (
                        event.name,
                        self.escalation_severity,
                        self.escalation_category,
                        self.escalation_notes or '—',
                    ),
                    partner_ids=[(4, u.partner_id.id) for u in users],
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
        else:
            # Simple bulk notification
            for event in events:
                event.message_post(
                    subject=_('Event %s: %s') % (
                        dict(events.fields_get(['state'])['state']['selection']).get(
                            event.state, event.state
                        ),
                        event.name[:100],
                    ),
                    body=_('Event has been marked as <b>%s</b> by %s.') % (
                        dict(events.fields_get(['state'])['state']['selection']).get(
                            event.state, event.state
                        ),
                        self.env.user.display_name,
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
