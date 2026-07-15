# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MarketingContext(models.Model):
    """Customer-specific marketing context — ICP, brand voice, positioning.
    Odoo-only — never exported to filesystem (confidential)."""

    _name = 'marketing.context'
    _description = 'Marketing Context'

    customer_id = fields.Many2one('res.partner', 'Customer',
        domain=[('customer_rank', '>', 0)], required=True)
    product_context = fields.Html('Product Context')
    icp = fields.Html('Ideal Customer Profile')
    brand_voice = fields.Html('Brand Voice')
    positioning = fields.Html('Positioning')
    current_kpis = fields.Html('Current KPIs')
    active_channels = fields.Html('Active Channels')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('customer_unique', 'UNIQUE(customer_id)',
         'Only one context per customer'),
    ]


class MarketingIdea(models.Model):
    """139 marketing ideas mapped to AARRR stages."""

    _name = 'marketing.idea'
    _description = 'Marketing Idea'
    _order = 'aarrr_stage, name'

    name = fields.Char('Idea', required=True)
    description = fields.Text('Description')
    aarrr_stage = fields.Selection([
        ('acquisition', 'Acquisition'),
        ('activation', 'Activation'),
        ('retention', 'Retention'),
        ('referral', 'Referral'),
        ('revenue', 'Revenue'),
    ], string='AARRR Stage', required=True, index=True)
    difficulty = fields.Selection([
        ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard'),
    ], string='Difficulty')
    impact = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Potential Impact')
    is_used = fields.Boolean('Used in Active Plan')


class MarketingKPI(models.Model):
    """Marketing KPI definitions."""

    _name = 'marketing.kpi'
    _description = 'Marketing KPI'
    _order = 'category, name'

    name = fields.Char('KPI Name', required=True)
    description = fields.Text('Description')
    category = fields.Selection([
        ('acquisition', 'Acquisition'),
        ('activation', 'Activation'),
        ('retention', 'Retention'),
        ('referral', 'Referral'),
        ('revenue', 'Revenue'),
    ], string='AARRR Stage', required=True)
    source_model = fields.Many2one('ir.model', 'Source Model')
    formula = fields.Text('Formula')
    unit = fields.Char('Unit', default='SEK')
    target_value = fields.Float('Target')
    current_value = fields.Float('Current')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
