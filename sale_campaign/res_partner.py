# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2017- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _
import datetime
from openerp.tools.safe_eval import safe_eval as eval
import logging
_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_pricelist(self):
        return self.env.ref('product.list0')
    partner_product_pricelist = fields.Many2one(comodel_name='product.pricelist', domain=[('type','=','sale')], string='Sale Pricelist', help="This pricelist will be used, instead of the default one, for sales to the current partner", default=default_pricelist)
    property_product_pricelist = fields.Many2one(comodel_name='product.pricelist', string='Sale Pricelist', compute='get_pricelist')

    @api.one
    def get_pricelist(self):
        pricelist = self.partner_product_pricelist
        if pricelist:
            if pricelist.is_fixed:
                self.property_product_pricelist = pricelist
            else:
                current_campaign = self.env['marketing.campaign'].search([('date_start', '<=', datetime.date.today()), ('date_stop', '>=', datetime.date.today()), '|', ('reseller_pricelist', '!=', False), ('pricelist', '!=', False)])
                if len(current_campaign) > 0:
                    if pricelist.is_reseller:
                        self.property_product_pricelist = current_campaign[0].reseller_pricelist.id if current_campaign[0].reseller_pricelist else current_campaign[0].pricelist.id
                    else:
                        self.property_product_pricelist = current_campaign[0].pricelist.id if current_campaign[0].pricelist else pricelist
                else:
                    self.property_product_pricelist = pricelist
        else:
            self.property_product_pricelist = None
