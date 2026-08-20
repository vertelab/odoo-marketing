# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MarketingKpi(models.Model):
    """KPI — a marketing metric to track, with target and current value."""

    _name = 'marketing.kpi'
    _description = 'Marketing KPI'
    _order = 'create_date desc, name'

    name = fields.Char('KPI Name', required=True)
    category = fields.Char('Category')
    unit = fields.Char('Unit')
    target_value = fields.Float('Target')
    current_value = fields.Float('Current')
    description = fields.Text('Description')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Responsible',
        default=lambda self: self.env.user)
