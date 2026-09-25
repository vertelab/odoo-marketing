# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class StrategyRisk(models.Model):
    """Extend strategy.risk with World Monitor event link."""

    _inherit = 'strategy.risk'

    world_event_id = fields.Many2one(
        'marketing.world.event', string='World Monitor Event',
        ondelete='set null',
        help='The world monitoring event that triggered this risk',
    )
    world_event_name = fields.Char(
        'Event Name',
        related='world_event_id.name',
        readonly=True,
        store=False,
    )
    world_event_severity = fields.Selection(
        related='world_event_id.severity',
        string='Event Severity',
        readonly=True,
        store=False,
    )

    def action_open_world_event(self):
        """Open the linked world event."""
        self.ensure_one()
        if not self.world_event_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('World Monitor Event'),
            'res_model': 'marketing.world.event',
            'view_mode': 'form',
            'res_id': self.world_event_id.id,
        }
