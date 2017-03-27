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


class crm_tracking_campaign(models.Model):
    _inherit = 'crm.tracking.campaign'

    website_description = fields.Html(string='Website Description')
    pricelist = fields.Many2one(comodel_name='product.pricelist', string='Pricelist')
    reseller_pricelist = fields.Many2one(comodel_name='product.pricelist', string='Reseller Pricelist')
    #~ product_ids = fields.One2many(comodel_name='product.template', inverse_name='campaign_id', string='Products')
    website_published = fields.Boolean(string='Available in the website', default=False, copy=False)
    website_url = fields.Char(string='Website url', compute='_website_url')

    @api.one
    def _website_url(self):
        self.website_url = '/crm_tracking_campaign/%s' %self.id

class product_public_category(models.Model):
    _inherit = 'product.public.category'

    mobile_icon = fields.Char(string='Mobile Icon', help='This icon will display on smaller devices')

class website_campaign(Website):
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        res = super(website_campaign, self).index(**kw)
        campaign = request.env['crm.tracking.campaign'].search([('date_start', '<=', datetime.date.today()), ('date_stop', '>=', datetime.date.today()), ('website_published', '=', True), '|', ('reseller_pricelist', '!=', False), ('pricelist', '!=', False)])
        if len(campaign) > 0:
            return werkzeug.utils.redirect('/crm_tracking_campaign', 302)
        else:
            return res

class website_sale(website_sale):
    @http.route([
        '/crm_tracking_campaign',
        '/crm_tracking_campaign/<model("crm.tracking.campaign"):campaign>',
    ], type='http', auth="public", website=True)
    def campaign_shop(self, page=0, category=None, campaign=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')

        url = "/shop"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)
        if attrib_list:
            post['attrib'] = attrib_list
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)

        if campaign:
            products = self.get_products(campaign.object_ids)
        else:
            campaign = request.env['crm.tracking.campaign'].search([('date_start', '<=', fields.Date.today()), ('date_stop', '>=', fields.Date.today()), ('website_published', '=', True)])
            if not campaign:
                return werkzeug.utils.redirect('/', 302)
            campaign = campaign[0]
            products = self.get_products(campaign.object_ids)

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
            'campaign': campaign,
        }
        return request.website.render("website_sale.products", values)

    @api.model
    def get_products(self, object_ids):
        products = self.env['product.template'].browse([])
        for o in object_ids:
            model = o.object_id._name
            if model == 'product.template':
                products |= o.object_id
            elif model == 'product.product':
                products |= o.object_id.product_tmpl_id
            elif model == 'product.public.category':
                products |= self.env['product.template'].search([('public_categ_ids', 'in', o.object_id.id)])
        return products
