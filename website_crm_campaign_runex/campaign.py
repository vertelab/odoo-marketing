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

    pricelist = fields.Many2one(comodel_name='product.pricelist', string='Pricelist')
    reseller_pricelist = fields.Many2one(comodel_name='product.pricelist', string='Reseller Pricelist')

    @api.model
    def get_campaigns(self):
        return super(crm_tracking_campaign, self).get_campaigns().filtered(lambda c: c.reseller_pricelist or c.pricelist)

    @api.multi
    def get_pricelist(self):
        self.ensure_one()
        return self.env['product.pricelist'].browse(self.context['pricelist'])
        #~ if not context.get('pricelist'):
            #~ pricelist = self.get_pricelist()
            #~ context['pricelist'] = int(pricelist)
        #~ else:
            #~ pricelist = request.env['product.pricelist'].browse(request.context['pricelist'])


class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_pricelist(self):
        return self.env.ref('product.list0')
    partner_product_pricelist = fields.Many2one(comodel_name='product.pricelist', domain=[('type','=','sale')], string='Sale Pricelist', help="This pricelist will be used, instead of the default one, for sales to the current partner", default=default_pricelist)
    #property_product_pricelist = fields.Many2one(comodel_name='product.pricelist', string='Sale Pricelist', compute='get_pricelist', search='search_pricelist')

    @api.model
    def search_pricelist(self, operator, value):
        return [('partner_product_pricelist', operator, value)]

    @api.one
    def get_pricelist(self):
        pricelist = self.partner_product_pricelist
        if pricelist:
            if pricelist.is_fixed:
                self.sudo().property_product_pricelist = pricelist
            else:
                current_campaign = self.env['crm.tracking.campaign'].get_campaigns()
                if len(current_campaign) > 0:
                    if pricelist.is_reseller:
                        self.sudo().property_product_pricelist = current_campaign[0].reseller_pricelist.id if current_campaign[0].reseller_pricelist else current_campaign[0].pricelist.id
                    else:
                        self.sudo().property_product_pricelist = current_campaign[0].pricelist.id if current_campaign[0].pricelist else pricelist
                else:
                    self.sudo().property_product_pricelist = pricelist
        else:
            self.sudo().property_product_pricelist = None

class product_pricelist(models.Model):
    _inherit = 'product.pricelist'

    is_reseller = fields.Boolean(string='Reseller')
    is_fixed = fields.Boolean(string='Fixed')

class product_product(models.Model):
    _inherit = 'product.product'

    @api.one
    def XXX_product_price(self,):  # Not yet
        pricelist = None
        raise Warning(self._context)
        if self._context.get('partner'):
            partner = self.env('res.partner').browse(int(self._context.get('partner')))
            pricelist = partner.get_pricelist()
        self.price = super(product_product, product).with_context({'pricelist': pricelist})._product_price(name,arg)[self.id]


class product_public_category(models.Model):
    _inherit = 'product.public.category'

    description = fields.Text(string='Description')
    #~ mobile_icon = fields.Char(string='Mobile Icon', help='This icon will display on smaller devices')

#~ class website_campaign(Website):
    #~ @http.route('/', type='http', auth="public", website=True)
    #~ def index(self, **kw):
        #~ res = super(website_campaign, self).index(**kw)
        #~ campaign = request.env['crm.tracking.campaign'].get_campaigns()
        #~ if len(campaign) > 0:
            #~ return werkzeug.utils.redirect('/campaign', 302)
        #~ else:
            #~ return res

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

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = request.env['product.pricelist'].browse(context['pricelist'])

        url = "/campaign"
        product_count = request.env['product.template'].search_count(domain)
        if search:
            post["search"] = search
        if category:
            category = request.env['product.public.category'].browse(int(category))
            url = "/shop/category/%s" % slug(category)

        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        campaign = request.env['crm.tracking.campaign'].with_context(context).get_campaigns()
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

        from_currency = request.env['product.price.type']._get_field_currency('list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: request.env['res.currency']._compute(from_currency, to_currency, price)

        return request.website.render("website_sale.products", {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
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
