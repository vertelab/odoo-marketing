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


class crm_campaign_product(models.Model):
    _name = 'crm.campaign.product'
    _order = 'sequence'

    sequence = fields.Integer()
    campaign_id = fields.Many2one(comodel_name="crm.tracking.campaign")
    product_id = fields.Many2one(comodel_name="product.product")
    name = fields.Char(related='product_id.name')
    default_code = fields.Char(related='product_id.default_code')
    type = fields.Selection(related='product_id.type')
    list_price = fields.Float(related='product_id.list_price')
    qty_available = fields.Float(related='product_id.qty_available')
    virtual_available = fields.Float(related='product_id.virtual_available')

class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    product_ids = fields.Many2many(comodel_name='product.product', relation="crm_campaign_product", column1='campaign_id',column2='product_id', string='Products')
    campaign_product_ids = fields.One2many(comodel_name='crm.campaign.product', inverse_name='campaign_id', string='Products')

    @api.one
    def update_campaign_product_ids(self):
        self.env['crm.campaign.product'].search([('campaign_id', '=', self.id)]).unlink()
        for o in self.object_ids.sorted(lambda o: o.sequence):
            _logger.error(getattr(o,'create_campaign_product', False))  
            if getattr(o,'create_campaign_product', False):
                o.create_campaign_product(self)

class product_template(models.Model):
    _inherit = 'product.template'

    campaign_ids = fields.Many2many(comodel_name='crm.tracking.campaign', relation="crm_campaign_product", column1='product_id', column2='campaign_id',string='Campaigns')


class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    object_id = fields.Reference(selection_add=[('product.template', 'Product Template'), ('product.product', 'Product Variant')])
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

    @api.one
    def create_campaign_product(self,campaign):
        if self.object_id._name == 'product.template':
			_logger.warn('Lukas in product.template')
			for product in self.object_id.product_variant_ids:
				self.env['crm.campaign.product'].create({
					'campaign_id': campaign.id,
					'product_id': product.id,
					'sequence': len(campaign.product_ids) + 1,
				})
				
        elif self.object_id._name == 'product.product':
            _logger.warn('Lukas in product.product')
            self.env['crm.campaign.product'].create({
                'campaign_id': campaign.id,
                #'product_id': self.object_id.id,
                'product_id': self.object_id.product_tmpl_id.id,
                'sequence': len(campaign.product_ids) + 1,
            })
            _logger.warn('Lukas self.object_id.id is %s' % self.object_id.id)
            
        elif self.object_id._name == 'product.public.category':
            _logger.warn('Lukas in product.category')
            for template in self.env['product.template'].search([('public_categ_ids', 'in', self.object_id.id)]):
				for product in template.product_variant_ids:
					self.env['crm.campaign.product'].create({	
						'campaign_id': campaign.id,
						'product_id': product.id,
						'sequence': len(campaign.product_ids) + 1,
					})
        else:
            super(crm_campaign_object, self).create_campaign_product(campaign)
