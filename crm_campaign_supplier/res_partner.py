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


class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    object_id = fields.Reference(selection_add=[('res.partner', 'Supplier')])
    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        if self.object_id and self.object_id._name == 'res.partner':
            self.name = self.object_id.name
            self.description = self.object_id.comment
            self.image = self.object_id.image
        return super(crm_campaign_object, self).get_object_value()


    @api.one
    def create_campaign_product(self,campaign):
        if self.object_id._name == 'res.partner':
            for product in self.env['product.template'].search([('seller_ids.name', '=', self.object_id.id)]):
                self.env['crm.campaign.product'].create({
                    'campaign_id': campaign.id,
                    'product_id': product.id,
                    'sequence': len(campaign.product_ids) + 1,
                })
        else:
            super(crm_campaign_object, self).create_campaign_product(campaign)
