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
        if self.object_id:
            if self.object_id._name == 'res.partner':
                self.res_id = self.object_id.id
                self.name = self.object_id.name
        return super(crm_campaign_object, self).get_object_value()


class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    def values_to_create(self, o, sequence):
        super(crm_tracking_campaign, self).values_to_create(o, sequence)
        if o.object_id._name == 'res.partner':
            cps = []
            for product in self.env['product.template'].search([('seller_ids.name', '=', o.object_id.id)]):
                cps.append({
                    'campaign_id': self.id,
                    'product_id': product.id,
                    'sequence': sequence + 1,
                })
            return cps
