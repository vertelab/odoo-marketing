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

    phase_ids = fields.One2many(comodel_name='crm.tracking.phase', inverse_name='campaign_id', string='Phases')

    
class crm_tracking_phase(models.Model):
    _name = "crm.tracking.phase"
    _order = 'campaign_id, sequence, name'

    campaign_id = fields.Many2one(comodel_name='crm.tracking.campaign', string='Campaign')
    name = fields.Char(string='Name')
    phase_type = fields.Many2one(comodel_name="crm.tracking.phase.type",string="Type")
    sequence = fields.Integer()
    @api.one
    def _start_date(self):
        self.start_date = fields.Date.now()
    start_date = fields.Date(computed='_start_date')
    end_date = fields.Date()
    
class crm_tracking_phase_type(models.Model):
    _name = "crm.tracking.phase.type"

    name = fields.Char(string='Name')
    start_days = fields.Integer()
    start_days_from_start = fields.Boolean()
    end_days = fields.Integer()
    end_days_from_start = fields.Boolean()
