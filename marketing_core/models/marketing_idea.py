# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MarketingIdea(models.Model):
    """Idea Bank — a marketing idea to try, with AARRR stage and scoring."""

    _name = 'marketing.idea'
    _description = 'Marketing Idea (Idea Bank)'
    _order = 'create_date desc, name'

    name = fields.Char('Idea', required=True)
    description = fields.Text('Description')
    aarrr_stage = fields.Selection([
        ('acquisition', 'Acquisition'),
        ('activation', 'Activation'),
        ('retention', 'Retention'),
        ('referral', 'Referral'),
        ('revenue', 'Revenue'),
    ], string='AARRR Stage', default='acquisition')
    difficulty = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Difficulty', default='medium')
    impact = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Impact', default='medium')
    is_used = fields.Boolean('Used', default=False,
        help="Mark when the idea has been executed / is in use.")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Responsible',
        default=lambda self: self.env.user)
