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
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime, timedelta
from babel.dates import format_date
import logging
_logger = logging.getLogger(__name__)


class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    phase_ids = fields.One2many(comodel_name='crm.tracking.phase', inverse_name='campaign_id', string='Phases')
    country_ids = fields.Many2many(comodel_name='res.country', string='Country')

    @api.multi
    def get_phase(self, date, is_reseller):
        self.ensure_one()
        return self.phase_ids.filtered(lambda p: p.start_date <= date and p.end_date >= date and p.reseller_pricelist == is_reseller)

    @api.multi
    def get_current_phase(self, is_reseller):
        self.ensure_one()
        return self.get_phase(fields.Date.today(), is_reseller)

    @api.multi
    def is_current(self, date, is_reseller):
        self.ensure_one()
        if is_reseller:
            if not self.country_ids or (self.env.user.partner_id.commercial_partner_id.country_id in self.country_ids):
                if self.date_stop:
                    return len(filter(None, self.phase_ids.filtered(lambda p: p.start_date <= date and p.end_date >= date and p.reseller_pricelist == is_reseller))) > 0
                else:
                    return len(filter(None, self.phase_ids.filtered(lambda p: p.start_date <= date and p.reseller_pricelist == is_reseller))) > 0
            else:
                return False
        else:
            if self.date_stop:
                return self.date_start <= date and self.date_stop >= date
            else:
                return self.date_start <= date

    @api.multi
    def check_product(self, prod_id):
        self.ensure_one()
        return prod_id in self.env['product.product'].search([('id', 'in', self.env['product.template'].search([('id', 'in', self.campaign_product_ids.mapped('product_id').mapped('id'))]).mapped('product_variant_ids').mapped('id'))]).mapped('id')

    @api.one
    def get_period(self, is_reseller):
        def pretty_date(date):
            return format_date(fields.Date.from_string(date), 'd MMM', locale=self.env.context.get('lang', 'sv_SE')).replace('.', '')
        phase = self.get_phase(fields.Date.today(), is_reseller)
        date_start = phase.start_date
        date_stop = phase.end_date
        if not date_stop:
            return _('until further notice')
        elif date_start:
            return '%s - %s' % (pretty_date(date_start),pretty_date(date_stop))
        else:
            return '- %s' % pretty_date(date_stop)

    @api.model
    def get_campaigns(self):
        return super(crm_tracking_campaign, self).get_campaigns().filtered(lambda c: self.env.user.partner_id.commercial_partner_id.country_id in c.country_ids) 


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
            if self.campaign_id.date_start:
                self.start_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_start) + timedelta(days = self.phase_type.start_days))
        else:
            if self.campaign_id.date_stop:
                self.start_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_stop) + timedelta(days = self.phase_type.start_days))
    start_date = fields.Date(compute='_start_date')

    @api.one
    def _end_date(self):
        if self.phase_type.end_days_from_start:
            self.end_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_start) + timedelta(days = self.phase_type.end_days))
        else:
            if self.campaign_id.date_stop:
                self.end_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_stop) + timedelta(days = self.phase_type.end_days))
            else:
                if self.phase_type.start_days_from_start and self.phase_type.end_days_from_start:
                    if self.phase_type.end_days >= self.phase_type.start_days:
                        self.end_date = fields.Date.to_string(fields.Date.from_string(self.campaign_id.date_start) + timedelta(days = self.phase_type.end_days))
                    else:
                        self.phase_type.end_days = self.phase_type.start_days
                        raise Warning('End days must be greater than or equal to start days')

    end_date = fields.Date(compute='_end_date')
    reseller_pricelist = fields.Boolean(string="Reseller",help="Use this pricelist for resellers, otherwise instead of default pricelist")
    pricelist_id = fields.Many2one(comodel_name="product.pricelist",string="Pricelist")

    @api.multi
    def get_pricelist(self,date,prod_id,is_reseller):
        for phase in self:
            if date >= phase.start_date and date <= phase.end_date and phase.campaign_id.check_product(prod_id) and \
                    phase.pricelist_id and (phase.reseller_pricelist and is_reseller or not phase.reseller_pricelist):
                        return phase.pricelist_id
        return self.env['product.pricelist'].browse()

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

    @api.onchange('end_days')
    def end_days_check(self):
        if self.start_days_from_start and self.end_days_from_start:
            if self.end_days < self.start_days:
                raise Warning('End days must be greater than or equal to start days')


class product_pricelist(models.Model):
    _inherit = "product.pricelist"

    @api.multi
    def price_get(self,prod_id, qty, partner=None):
        self.ensure_one()
        # A bug in sale_stock means partner can sometimes be a partner record instead of the expected integer.
        if type(partner) == type(self.env['res.partner']):
            partner = partner.id
        else:
            partner = self.sudo().env.ref('base.public_partner').id
        is_reseller = self.sudo().env.ref('base.public_user').property_product_pricelist != self.env['res.partner'].sudo().browse(partner).property_product_pricelist
        price = [p[0] for key, p in self.sudo().price_rule_get(prod_id, qty, partner=partner).items()][0]
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
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')])
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)])
        for campaign in campaigns:
            if campaign.is_current(fields.Date.today(),for_reseller):
                products |= campaign.product_ids.filtered(lambda p: len(self.env.user.partner_id.commercial_partner_id.access_group_ids & p.access_group_ids) > 0)
        return products

    @api.model
    def get_campaign_variants(self,for_reseller=False):
        products = self.env['product.product'].browse([])
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')])
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)])
        for campaign in campaigns:
            if campaign.is_current(fields.Date.today(),for_reseller):
                for o in campaign.object_ids:
                    if o.object_id._name == 'product.product':
                        if self.env['product.product'].search([('id', '=', o.object_id.id)]) and self.env['product.template'].search([('id', '=', o.object_id.product_tmpl_id.id)]):
                        # ~ if len(o.object_id.sudo().access_group_ids) == 0 or len(self.env.user.partner_id.commercial_partner_id.access_group_ids & o.object_id.sudo().access_group_ids) > 0:
                            products |= o.object_id
        return products

    @api.model
    def get_campaign_tmpl(self,for_reseller=False):
        products = self.env['product.template'].browse([])
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')])
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)])
        for campaign in campaigns:
            if campaign.is_current(fields.Date.today(),for_reseller):
                for o in campaign.object_ids:
                    if o.object_id._name == 'product.template':
                        if self.env['product.template'].search([('id', '=', o.object_id.id)]):
                        # ~ if len(o.object_id.sudo().access_group_ids) == 0 or len(self.env.user.partner_id.commercial_partner_id.access_group_ids & o.object_id.sudo().access_group_ids) > 0:
                            products |= o.object_id
        return products

    @api.multi
    def get_campaign_image(self,for_reseller=False):
        self.ensure_one()
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')]).filtered(lambda c: self.id in c.product_ids.mapped('id'))
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)]).filtered(lambda c: self.id in c.product_ids.mapped('id'))
        for campaign in campaigns:
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
            for campaign in self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True), ('date_start','>=',fields.Date.today()), ('date_stop','<=',fields.Date.today())]).filtered(lambda c: self.id in c.product_ids.mapped('id')):
                if campaign.date_stop > date:
                    date = campaign.date_stop
        return date

class product_product(models.Model):
    _inherit = "product.product"
    is_offer_product_consumer = fields.Boolean(compute='_is_offer_product')
    is_offer_product_reseller = fields.Boolean(compute='_is_offer_product')


    @api.model
    def get_campaign_products(self,for_reseller=False):
        products = self.env['product.product'].browse([])
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')])
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)])

        for campaign in campaigns.filtered(lambda c: self.env.user.partner_id.commercial_partner_id.country_id in c.country_ids):
            if campaign.is_current(fields.Date.today(),for_reseller):
                for o in self.env['product.product'].search([('product_tmpl_id','in',campaign.product_ids.mapped('id'))]):
                    products |= o.object_id.filtered(lambda p: len(self.env.user.partner_id.commercial_partner_id.access_group_ids & p.access_group_ids) > 0)
        return products

    @api.one
    def _is_offer_product(self):
        self.is_offer_product_consumer = self in self.get_campaign_products(for_reseller = False)
        self.is_offer_product_reseller = self in self.get_campaign_products(for_reseller = True)

    @api.model
    def _search_is_offer_product_reseller(self, op, value):
        # only supports op: =; value: True, False
        
        return bool(self.get_campaign_products(for_reseller = value))


    @api.model
    def get_campaign_variants(self,for_reseller=False):
        products = self.env['product.product'].browse([])
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')])
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)])
        for campaign in campaigns:
            if campaign.is_current(fields.Date.today(),for_reseller):
                variant_ids = [int(d['object_id'].split(',')[1]) for d in self.env['crm.campaign.object'].search_read([('campaign_id', '=', campaign.id), ('object_id', '=like', 'product.product,%')], ['object_id'])]
                products |= products.search([('id', 'in', variant_ids)])
                #~ for o in campaign.object_ids:
                    #~ if o.object_id._name == 'product.product':
                        #~ if len(o.object_id.sudo().access_group_ids) == 0 or len(self.env.user.partner_id.commercial_partner_id.access_group_ids & o.object_id.sudo().access_group_ids) > 0:
                            #~ products |= o.object_id
        return products

    @api.multi
    def get_campaign_image(self,for_reseller=False):
        self.ensure_one()
        if for_reseller:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open')]).filtered(lambda c: self.product_tmpl_id.id in c.product_ids.mapped('id'))
        else:
            campaigns = self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True)]).filtered(lambda c: self.product_tmpl_id.id in c.product_ids.mapped('id'))
        for campaign in campaigns:
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
            for campaign in self.env['crm.tracking.campaign'].search([('state','=','open'), ('website_published', '=', True), ('date_start','>=',fields.Date.today()), ('date_stop','<=',fields.Date.today())]).filtered(lambda c: self.product_tmpl_ids.id in c.product_ids.mapped('id')):
                if campaign.date_stop > date:
                    date = campaign.date_stop
        return date
