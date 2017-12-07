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

class product_template(models.Model):
    _inherit = "product.template"
    @api.multi
    def get_default_variant(self):
        self.ensure_one()
        intersect = self.product_variant_ids & self.get_campaign_variants(for_reseller=self.env.user.partner_id.commercial_partner_id.property_product_pricelist.for_reseller)
        if len(intersect)>0:
            return intersect[0]
        else:
            return super(product_template,self).get_default_variant()
