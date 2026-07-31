# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    """Extend res.company with World Monitor per-company settings."""

    _inherit = 'res.company'

    world_monitor_enabled = fields.Boolean(
        string='World Monitor Enabled',
        default=False,
        help='Enable world monitoring for this company',
    )
    world_monitor_filter_industry = fields.Char(
        string='Filter Industry',
        help='Comma-separated industries to filter by (e.g. IT, Healthcare, Finance)',
    )
    world_monitor_filter_countries = fields.Many2many(
        'res.country',
        'res_company_world_monitor_country_rel',
        'company_id',
        'country_id',
        string='Filter Countries',
        help='Limit world monitoring to these countries. Leave empty for all.',
    )
    world_monitor_auto_brief = fields.Boolean(
        string='Auto-generate Weekly Brief',
        default=True,
        help='Automatically generate weekly omvärldsanalys briefs',
    )
    world_monitor_alert_on_critical = fields.Boolean(
        string='Alert on Critical Events',
        default=True,
        help='Send notifications when critical events are detected',
    )
