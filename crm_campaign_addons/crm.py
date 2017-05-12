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

    color = fields.Integer('Color Index')
    date_start = fields.Date(string='Start Date')
    date_stop = fields.Date(string='Start Stop')
    object_ids = fields.One2many(comodel_name='crm.campaign.object', inverse_name='campaign_id', string='Objects')
    @api.one
    def _object_names(self):
        self.object_names = ', '.join(self.object_ids.mapped('name'))
    object_names = fields.Char(compute='_object_names')
    @api.one
    def _object_count(self):
        self.object_count = len(self.object_ids)
    object_count = fields.Integer(compute='_object_count')

    @api.model
    def get_campaigns(self):
        return self.env['crm.tracking.campaign'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today())])

    @api.model
    def get_objects(self):
        objects = self.env['crm.campaign.object'].browse([])
        for campaign in self.get_campaigns():
            objects |= campaign.object_ids
        return objects

class crm_campaign_object(models.Model):
    _name = 'crm.campaign.object'

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    image = fields.Binary(string='Image')
    sequence = fields.Integer()
    color = fields.Integer('Color Index')
    campaign_id = fields.Many2one(comodel_name='crm.tracking.campaign', string='Campaign')
    object_id = fields.Reference(selection=[], string='Object')
    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        return None
