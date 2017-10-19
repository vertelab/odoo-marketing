# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)



class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    phase_ids = fields.One2many(comodel_name='crm.tracking.phase', inverse_name='campaign_id', string='Phases')

    #~ @api.multi
    #~ def get_pricelist(self,date,prod_id,is_reseller):
        #~ self.ensure_one()
        #~ return self.phase_ids.mapped(lambda p: p.get_pricelist(date,prod_id,is_reseller))
    
class crm_tracking_phase(models.Model):
    _name = "crm.tracking.phase"
    _order = 'campaign_id, sequence, name'

    campaign_id = fields.Many2one(comodel_name='crm.tracking.campaign', string='Campaign')
    name = fields.Char(string='Name')
    phase_type = fields.Many2one(comodel_name="crm.tracking.phase.type",string="Type")
    sequence = fields.Integer()
    @api.one
    def _start_date(self):
        if self.phase_type.start_days_from_start:
            self.start_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_start) + timedelta(days = self.phase_type.start_days))
        else:
            self.start_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_stop) + timedelta(days = self.phase_type.start_days))
    start_date = fields.Date(compute='_start_date')
    @api.one
    def _end_date(self):
        if self.phase_type.end_days_from_start:        
            self.end_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_start) + timedelta(days = self.phase_type.end_days))
        else:
            self.end_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_stop) + timedelta(days = self.phase_type.end_days))
    end_date = fields.Date(compute='_end_date')
    reseller_pricelist = fields.Boolean(string="Reseller",help="Use this pricelist for resellers, otherwise instead of default pricelist")
    pricelist_id = fields.Many2one(comodel_name="product.pricelist",string="Pricelist")
    
    @api.multi
    def get_pricelist(self,date,prod_id,is_reseller):
        self.ensure_one()
        if date >= self.start_date and date <= self.end_date and self.env['product.product'].browse(prod_id).product_tmpl_id.id in self.campaign_id.product_ids.mapped('id') and \
                self.pricelist_id and (self.reseller_pricelist and is_reseller or not self.reseller_pricelist):
                    return self.pricelist_id
        return None

class crm_tracking_phase_type(models.Model):
    _name = "crm.tracking.phase.type"

    name = fields.Char(string='Name',required=True)
    start_days = fields.Integer()
    start_days_from_start = fields.Boolean(help="Checked: days are counted from start date otherwise from end date")
    end_days = fields.Integer()
    end_days_from_start = fields.Boolean(help="Checked: days are counted from start date otherwise from end date")

class product_pricelist(models.Model):
    _inherit = "product.pricelist"
    
    @api.multi
    def price_get(self,prod_id, qty, partner=None):
        self.ensure_one()
        is_reseller = self.env.ref('base.public_user').property_product_pricelist != self.env['res.partner'].browse(partner).property_product_pricelist
        price = [p[0] for key, p in self.price_rule_get(prod_id, qty, partner=partner).items()][0]
        campaign_price = 999999999999999999999999999999.0   
        for pricelist in self.env['crm.tracking.campaign'].search([('state','=','open')]).mapped('phase_ids').mapped(lambda p: p.get_pricelist(self.env.context['date'],prod_id,is_reseller)):
            try:
                campaign_price = [p[0] for key, p in pricelist.price_rule_get(prod_id, qty, partner=partner).items()][0]
            except:
                pass
        #~ for c in self.env['crm.tracking.campaign'].search([('state','=','open')]):
            #~ for p in c.phase_ids:
                #~ try:
                    #~ campaign_price = [p[0] for key, p in p.get_pricelist(self.env.context['date'],prod_id,is_reseller).price_rule_get(prod_id, qty, partner=partner).items()][0]
                #~ except:
                    #~ campaign_price = 999999999999999999999999999999.0   
        return {self.id:campaign_price if campaign_price < price else price}
