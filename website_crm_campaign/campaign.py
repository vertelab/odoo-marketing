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
import werkzeug
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_sale.controllers.main import website_sale, QueryURL, table_compute
import datetime
PPG = 20 # Products Per Page
PPR = 4  # Products Per Row
import logging
_logger = logging.getLogger(__name__)

class crm_campaign_object(models.Model):
    _inherit = 'crm.campaign.object'

    website_description = fields.Html(string='Website Description')
    website_published = fields.Boolean(string='Available in the website', default=False, copy=False)
    website_url = fields.Char(string='Website url', compute='_website_url')

    @api.one
    def _website_url(self):
        self.website_url = '/campaign/%s' %self.id

    object_id = fields.Reference(selection_add=[('product.public.category', 'Product Category')])
    @api.one
    @api.onchange('object_id')
    def get_object_value(self):
        if self.object_id:
            if self.object_id._name == 'product.public.category':
                self.res_id = self.object_id.id
                self.name = self.object_id.name
                self.description = self.object_id.description
                self.image = self.object_id.image
        return super(crm_campaign_object, self).get_object_value()

class product_public_category(models.Model):
    _inherit = 'product.public.category'

    description = fields.Text(string='Description')
    mobile_icon = fields.Char(string='Mobile Icon', help='This icon will display on smaller devices')

class website_campaign(Website):
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        res = super(website_campaign, self).index(**kw)
        campaign = request.env['crm.tracking.campaign'].get_campaigns()
        if len(campaign) > 0:
            return werkzeug.utils.redirect('/campaign', 302)
        else:
            return res

class website_sale(website_sale):
    @http.route([
        '/campaign',
        '/campaign/<model("crm.tracking.campaign"):campaign>',
    ], type='http', auth="public", website=True)
    def campaign_shop(self, page=0, category=None, campaign=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
        if attrib_list:
            post['attrib'] = attrib_list
            
        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/campaign', category=category and int(category), search=search, attrib=attrib_list)

        url = "/campaign"
        product_count = request.env['product.template'].search_count(domain)
        if search:
            post["search"] = search
        if category:
            category = request.env['product.public.category'].browse(int(category))
            url = "/shop/category/%s" % slug(category)

        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        campaign = request.env['crm.tracking.campaign'].get_campaigns()
        if not campaign:
            return werkzeug.utils.redirect('/', 302)
        campaign.ensure_one()

        #~ if campaign:
            #~ products = self.get_products(campaign.object_ids)
        #~ else:
            #~ campaign = request.env['crm.tracking.campaign'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today()), ('website_published', '=', True)])
            #~ if not campaign:
                #~ return werkzeug.utils.redirect('/', 302)
            #~ campaign = campaign[0]
            #~ products = self.get_products(campaign.object_ids)

        styles = request.env['product.style'].search([])
        categs = request.env['product.public.category'].search([('parent_id', '=', False)])
        attributes = request.env['product.attribute'].search([])

        from_currency = request.env['product.price.type']._get_field_currency('list_price')
        to_currency = pricelist.currency_id
        compute_currency = lambda price: request.env['res.currency']._compute(from_currency, to_currency, price)

        return request.website.render("website_sale.products", {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': campaign.get_pricelist(),
            'products': campaign.product_ids,
            'bins': table_compute().process(campaign.product_ids),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
            'campaign': campaign,
        })
