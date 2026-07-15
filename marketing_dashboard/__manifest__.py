# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Unified AARRR marketing dashboard',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': ['marketing_core', 'dashboard_vrtl'],
    'data': [
        'security/ir.model.access.csv',
        'data/dashboards/marketing_overview.yaml',
        'views/marketing_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
