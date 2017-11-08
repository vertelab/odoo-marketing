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

    @api.multi
    def get_phase(self, date, is_reseller):
        self.ensure_one()
        return filter(None, self.phase_ids.filtered(lambda p: p.start_date <= date and p.end_date >= date and p.reseller_pricelist == is_reseller))


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
        for phase in self:
            if date >= phase.start_date and date <= phase.end_date and phase.env['product.product'].browse(prod_id).product_tmpl_id.id in phase.campaign_id.product_ids.mapped('id') and \
                    phase.pricelist_id and (phase.reseller_pricelist and is_reseller or not phase.reseller_pricelist):
                        return phase.pricelist_id
        return None

    @api.multi
    def get_phase(self,date,is_reseller):
        self.ensure_one()
        if date >= self.start_date and date <= self.end_date and is_reseller == self.reseller_pricelist:
            return self


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
        is_reseller = self.sudo().env.ref('base.public_user').property_product_pricelist != self.env['res.partner'].browse(partner).property_product_pricelist
        price = [p[0] for key, p in self.price_rule_get(prod_id, qty, partner=partner).items()][0]
        campaign_price = 999999999999999999999999999999.0
        date = self.env.context['date'] if self.env.context.get('date') else fields.Date.today()
        for pricelist in self.env['crm.tracking.campaign'].search([('state','=','open')]).mapped('phase_ids').mapped(lambda p: p.get_pricelist(date,prod_id,is_reseller)):
            try:
                campaign_price = [p[0] for key, p in pricelist.price_rule_get(prod_id, qty, partner=partner).items()][0]
            except:
                pass
        return {self.id:campaign_price if campaign_price < price else price}

class product_template(models.Model):
    _inherit = "product.template"

    @api.model
    def get_campaign_products(self,for_reseller=False):
        products = self.env['product.template'].browse([])
        for campaign in self.env['crm.tracking.campaign'].search([('state','=','open')]):
            if len(campaign.get_phase(fields.Date.today(),for_reseller))>0:
                products |= campaign.product_ids
        return products

    @api.multi
    def get_campaign_image(self,for_reseller=False):
        self.ensure_one()
        for campaign in self.env['crm.tracking.campaign'].search([('state','=','open')]).filtered(lambda c: self.id in c.product_ids.mapped('id')):
            if len(campaign.get_phase(fields.Date.today(),for_reseller))>0:
                return campaign.image

    @api.model
    def get_campaign_date(self,for_reseller=False):
        self.ensure_one()
        date = None
        if for_reseller:
            for phase in self.env['crm.tracking.campaign'].search([('state','=','open')]).filtered(lambda c: self.id in c.product_ids.mapped('id')).mapped(lambda p: p.get_phase(fields.Date.today(),for_reseller)):
                if phase.end_date > date:
                    date = phase.end_date
        else:
            for campaign in self.env['crm.tracking.campaign'].search([('state','=','open'),('date_start','>=',fields.Date.today()),('date_stop','<=',fields.Date.today())]).filtered(lambda c: self.id in c.product_ids.mapped('id')):
                if campaign.date_stop > date:
                    date = campaign.date_stop
        return date

class product_product(models.Model):
    _inherit = "product.product"

    @api.model
    def get_campaign_products(self,for_reseller=False):
        products = self.env['product.product'].browse([])
        for campaign in self.env['crm.tracking.campaign'].search([('state','=','open')]):
            if len(campaign.get_phase(fields.Date.today(),for_reseller))>0:
                for variant in self.env['product.product'].search([('product_tmpl_id','in',campaign.product_ids.mapped('id'))]):
                    products |= variant
        return products

    @api.multi
    def get_campaign_image(self,for_reseller=False):
        self.ensure_one()
        for campaign in self.env['crm.tracking.campaign'].search([('state','=','open')]).filtered(lambda c: self.product_tmpl_id.id in c.product_ids.mapped('id')):
            if len(campaign.get_phase(fields.Date.today(),for_reseller))>0:
                return campaign.image

    @api.model
    def get_campaign_date(self,for_reseller=False):
        self.ensure_one()
        date = None
        if for_reseller:
            for phase in self.env['crm.tracking.campaign'].search([('state','=','open')]).filtered(lambda c: self.product_tmpl_id.id in c.product_ids.mapped('id')).mapped(lambda p: p.get_phase(fields.Date.today(),for_reseller)):
                if phase.end_date > date:
                    date = phase.end_date
        else:
            for campaign in self.env['crm.tracking.campaign'].search([('state','=','open'),('date_start','>=',fields.Date.today()),('date_stop','<=',fields.Date.today())]).filtered(lambda c: self.product_tmpl_ids.id in c.product_ids.mapped('id')):
                if campaign.date_stop > date:
                    date = campaign.date_stop
        return date
