# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2019 Vertel AB (<http://vertel.se>).
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
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
import werkzeug
from odoo.addons.website.controllers.main import Website
import datetime
import logging
_logger = logging.getLogger(__name__)


class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    website_description = fields.Html(string='Website Description')
    website_published = fields.Boolean(string='Available in the website', default=False, copy=False)
    website_url = fields.Char(string='Website url', compute='_website_url')

    @api.one
    def _website_url(self):
        self.website_url = '/campaign/%s' %self.id

    @api.multi
    def get_campaigns(self):
        return super(crm_tracking_campaign, self).get_campaigns().filtered(lambda c: c.website_published)


class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    object_id = fields.Reference(selection_add=[('product.public.category', 'Product Category')])
    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        if self.object_id:
            if self.object_id._name == 'product.public.category':
                self.res_id = self.object_id.id
                self.name = self.object_id.name
                self.description = self.object_id.description
                self.image = self.object_id.image
        return super(crm_campaign_object, self).get_object_value()


class product_public_category(models.Model):
    _inherit = 'product.public.category'

    description = fields.Text(string='Description')
    mobile_icon = fields.Char(string='Mobile Icon', help='This icon will display on smaller devices')


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        campaign = self.env['crm.tracking.campaign'].get_campaigns()
        if len(campaign):
            if not vals.get('campaign_id'):
                vals['campaign_id'] = campaign[0].id
        return super(sale_order, self).create(vals)

