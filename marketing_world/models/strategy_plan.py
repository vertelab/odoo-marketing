# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class StrategyPlan(models.Model):
    """Extend strategy.plan with World Monitor integration."""

    _inherit = 'strategy.plan'

    world_brief_ids = fields.One2many(
        'marketing.world.brief',
        compute='_compute_world_brief_ids',
        string='World Monitor Briefs',
        help='Omvärldsanalyser linked to this plan via the plan_ids M2M',
    )
    world_brief_count = fields.Integer(
        'World Brief Count',
        compute='_compute_world_brief_count',
        store=True,
    )
    world_event_count = fields.Integer(
        'World Event Count',
        compute='_compute_world_event_count',
        store=True,
    )
    world_last_brief_date = fields.Datetime(
        'Last Brief Date',
        compute='_compute_world_last_brief_date',
        store=False,
    )

    @api.depends('customer_id')
    def _compute_world_brief_ids(self):
        for record in self:
            if record.customer_id:
                record.world_brief_ids = self.env['marketing.world.brief'].search([
                    ('customer_id', '=', record.customer_id.id),
                ], limit=10)
            else:
                record.world_brief_ids = False

    @api.depends('world_brief_ids')
    def _compute_world_brief_count(self):
        for record in self:
            record.world_brief_count = len(record.world_brief_ids)

    @api.depends('customer_id')
    def _compute_world_event_count(self):
        for record in self:
            if record.customer_id:
                record.world_event_count = self.env['marketing.world.event'].search_count([
                    ('customer_id', '=', record.customer_id.id),
                    ('state', 'in', ('relevant', 'escalated')),
                ])
            else:
                record.world_event_count = 0

    @api.depends('world_brief_ids')
    def _compute_world_last_brief_date(self):
        for record in self:
            briefs = record.world_brief_ids
            if briefs:
                record.world_last_brief_date = briefs[0].create_date
            else:
                record.world_last_brief_date = False

    def action_open_world_briefs(self):
        """Open briefs for this plan's customer."""
        self.ensure_one()
        if not self.customer_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('World Monitor Briefs'),
            'res_model': 'marketing.world.brief',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.customer_id.id)],
            'context': {
                'default_customer_id': self.customer_id.id,
                'search_default_group_period': 1,
            },
        }

    def action_open_world_events(self):
        """Open events for this plan's customer."""
        self.ensure_one()
        if not self.customer_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('World Monitor Events'),
            'res_model': 'marketing.world.event',
            'view_mode': 'tree,form,kanban',
            'domain': [('customer_id', '=', self.customer_id.id)],
            'context': {
                'default_customer_id': self.customer_id.id,
                'search_default_filter_active': 1,
            },
        }
