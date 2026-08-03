# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing Competitor Monitor',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Social media monitoring for competitors — LinkedIn, YouTube, signal scoring, battle card integration',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': [
        'marketing_world',
        'mail',
    ],
    'external_dependencies': {
        'python': ['linkedin_api'],
    },
    'data': [
        'security/ir.model.access.csv',
        'security/marketing_competitor_security.xml',
        'data/competitor_cron.xml',
        'views/competitor_social_signal_views.xml',
        'views/competitor_views.xml',
        'views/competitor_menu_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
