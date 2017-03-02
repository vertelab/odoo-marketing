# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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
from openerp import models, fields, api, _
from openerp import http
from openerp.http import request
from openerp.addons.website.controllers.main import Website
import datetime
import logging
_logger = logging.getLogger(__name__)


class marketing_campaign(models.Model):
    _inherit = 'marketing.campaign'

    date_start = fields.Date(string='Start Date')
    date_stop = fields.Date(string='Start Stop')
    website_description = fields.Html(string='Website Description')
    pricelist = fields.Many2one(comodel_name='product.pricelist', string='Pricelist')
    reseller_pricelist = fields.Many2one(comodel_name='product.pricelist', string='Reseller Pricelist')

class website_campaign(Website):
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        res = super(website_campaign, self).index(**kw)
        campaign = request.env['marketing.campaign'].search([('date_start', '<=', datetime.date.today()), ('date_stop', '>=', datetime.date.today()), '|', ('reseller_pricelist', '!=', False), ('pricelist', '!=', False)])
        if len(campaign) > 0:
            return request.website.render("sale_campaign.current_campaign_view", {
                'campaign': campaign[0],
            })
        else:
            return res

