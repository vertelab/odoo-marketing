# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2023 Vertel AB (<robin.calvin@vertel.se>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
#
# https://www.odoo.com/documentation/16.0/reference/module.html
#
{
    'name': 'Marketing: CRM Dashboard Translation',
    'version': '0.0',
    # Version ledger: XX.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Swedish translations for CRM Dashboard',
    'category': 'Marketing',
    'description': """
    
    """,
    #'sequence': '1'
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-marketing/crm_dashboard_translation',
    'repository': 'https://github.com/vertelab/odoo-marketing',
    'images': ['static/description/banner.png'], # 560x280 px.
    # * * * * 
    
    'depends': ['crm_dashboard'],
    'data': [],
    'demo': [],
    'application': False,
    'installable': True,    
    'auto_install': True,
}
