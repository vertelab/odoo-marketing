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
import logging
_logger = logging.getLogger(__name__)


class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    @api.one
    def _product_ids(self):
        products = self.env['product.template'].browse([])
        for o in self.object_ids:
            if o.object_id._name == 'product.template':
                products |= o.object_id
            elif o.object_id._name == 'product.product':
                products |= o.object_id.product_tmpl_id
            elif o.object_id._name == 'product.public.category':
                products |= self.env['product.template'].search([('public_categ_ids', 'in', o.object_id.id)])
        self.product_ids = products
    product_ids = fields.Many2many(comodel_name='product.template', compute='_product_ids',string='Products')


class product_template(models.Model):
    _inherit = 'product.template'

    @api.one
    @api.depends('')
    def _campaign_ids(self):
        self.campaign_ids = [(6, 0, self.env['crm.campaign.object'].search([('object_id', '=', self.id)]).filtered(lambda o: o.object_id._name == 'product.template').mapped('campaign_id').mapped('id'))]
    campaign_ids = fields.Many2many(comodel_name='crm.tracking.campaign', string='Campaign')


class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    object_id = fields.Reference(selection_add=[('product.template', 'Product Template'), ('product.product', 'Product Variant'),])
    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        if self.object_id:
            if self.object_id._name == 'product.template' or self.object_id._name == 'product.product':
                self.res_id = self.object_id.id
                self.name = self.object_id.name
                self.description = self.object_id.description_sale
                self.image = self.object_id.image
        return super(crm_campaign_object, self).get_object_value()
