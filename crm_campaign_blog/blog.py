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
import re
import logging
_logger = logging.getLogger(__name__)


class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    object_id = fields.Reference(selection_add=[('blog.post', 'BLog Post')])
    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        if self.object_id:
            if self.object_id._name == 'blog.post':
                self.res_id = self.object_id.id
                self.name = self.object_id.name
                self.description = self.object_id.subtitle
                try:
                    self.image = self.env['ir.attachment'].browse(int(re.search('ir.attachment/(.+?)_', self.object_id.background_image).group(1))).datas
                    #~ self.image = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id)]).datas
                except AttributeError:
                    self.image = None
        return super(crm_campaign_object, self).get_object_value()
