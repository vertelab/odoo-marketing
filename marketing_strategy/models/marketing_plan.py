# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MarketingPlan(models.Model):
    """Bridge: link marketing.plan to Business Model Canvas from strategy_core."""

    _inherit = 'marketing.plan'

    bmc_id = fields.Many2one('business.model.canvas', 'Business Model Canvas',
        help="Auto-populates plan sections from BMC")

    @api.onchange('bmc_id')
    def _onchange_bmc(self):
        if self.bmc_id:
            bmc = self.bmc_id
            self.acquisition_strategy = bmc.customer_segments
            self.revenue_strategy = bmc.revenue_streams
