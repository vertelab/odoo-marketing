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

{
    'name': 'Sale Campaign',
    'version': '0.1',
    'category': 'crm',
    'description': """
Different pricelists on campaign
================================
* Hook product.template with crm.tracking.campaign
* Start and stop date on a campaign
* Show current campaign as first page on website

crm_campaign
    crm.tracking.campaign
    crm.tracking.campaign.object  (title,description,image)
    start/stop-date
    pricelists
    campaign_objects
     get_campaign_objs
crm_campaign_product
     get_campaign_products
crm_campaign_blog
website_crm_campaign

""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': ['website_sale', 'sale_crm', 'crm_campaign_product'],
    'data': [
        'views/campaign_view.xml',
    ],
    'installable': True,
}

