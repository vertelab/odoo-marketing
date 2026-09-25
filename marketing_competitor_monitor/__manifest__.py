# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing Competitor Monitor',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Social media monitoring for competitors — LinkedIn, YouTube, signal scoring, battle card integration.',
    'description': '''
Marketing Competitor Monitor
============================

    Social media monitoring for competitors — LinkedIn, YouTube, signal scoring, battle card integration.

    Features:

        - Automation: Scheduled jobs: Social Monitor Pull, Social ID Resolution.
        - UI Integration: Extends 4 view(s) in the Odoo interface.
        - Extends Odoo: Builds on competitor.social.signal, display_name, mail.thread, marketing.competitor.cron.line.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing/marketing_competitor_monitor',
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
