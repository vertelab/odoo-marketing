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

    #~ @api.one
    #~ def _get_product_ids(self):
        #~ self.product_ids = [(6,_,self.env['crm.campaign.product'].search([('')]))
        #~ products = self.env['product.template'].browse([])
        #~ for o in self.object_ids:
            #~ if o.object_id._name == 'product.template':
                #~ products |= o.object_id
                #~ self.env['product.template'].browse(o.object_id.id).write({'campaign_sequence': o.sequence})
            #~ elif o.object_id._name == 'product.product':
                #~ products |= o.object_id.product_tmpl_id
            #~ elif o.object_id._name == 'product.public.category':
                #~ products |= self.env['product.template'].search([('public_categ_ids', 'in', o.object_id.id)])
        #~ self.product_ids = products
    #~ @api.one
    #~ def _set_product_ids(self):
        
        #~ products = self.env['product.template'].browse([])
        #~ for o in self.object_ids:
            #~ if o.object_id._name == 'product.template':
                #~ products |= o.object_id
                #~ self.env['product.template'].browse(o.object_id.id).write({'campaign_sequence': o.sequence})
            #~ elif o.object_id._name == 'product.product':
                #~ products |= o.object_id.product_tmpl_id
            #~ elif o.object_id._name == 'product.public.category':
                #~ products |= self.env['product.template'].search([('public_categ_ids', 'in', o.object_id.id)])
        #~ self.product_ids = products
        
    #~ product_ids = fields.One2many(comodel_name='product.template', compute="_get_product_ids", inverse='_set_product_ids',string='Products')


    @api.one
    @api.onchange('object_ids.object_id')
    def _update_product_ids(self):
        if self.object_id._name == ''
            pass


    @api.model
    def _object2campaign_product(self,campaign_id,obj,sequence):
        if obj.object_id._name == 'product.template':
            return [{
                    'campaign_id': campaign_id,
                    'product_id': obj.object_id.id,
                    'sequence': sequence,
                    }]
        elif obj.object_id._name == 'product.product':
            return [{
                    'campaign_id': campaign_id,
                    'product_id': obj.object_id.product_tmpl_id.id,
                    'sequence': sequence,
                }]
        elif obj.object_id._name == 'product.public.category':
            return [{
                    'campaign_id': campaign_id,
                    'product_id': p.id,
                    'sequence': sequence += 1,
                } for p in self.env['product.template'].search([('public_categ_ids', 'in', obj.object_id.id)])]
                            
    @api.one
    def _create_product_ids(self):
        self.env['crm.campaign.product'].search([('campaign_id','=',self.id)]).unlink()
        i = 10
        for o in self.object_ids:
            self.env['crm.campaign.product'].create(self._object2campaign_product(self.id,o,i))  # eventuellt forsnurra
            i += 10

class product_template(models.Model):
    _inherit = 'product.template'

    @api.one
    @api.depends('')
    def _campaign_ids(self):
        self.campaign_ids = [(6, 0, self.env['crm.campaign.object'].search([('object_id', '=', self.id)]).filtered(lambda o: o.object_id._name == 'product.template').mapped('campaign_id').mapped('id'))]
    campaign_ids = fields.Many2many(comodel_name='crm.tracking.campaign', string='Campaign')
    campaign_sequence = fields.Integer()




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


class crm_campaign_product(models.Model):
    _name = 'crm.campaign.product'

    product_id = fields.Many2one(comodel_name="product.template")
    campaign_id = fields.Many2one(comodel_name="crm.tracking.campaign")
    
    object_id = fields.Many2one(comodel_name='crm.campaign.object')
    sequence = fields.Integer()
    partner_id = fields.Many2one(comodel_name="res.partner")

