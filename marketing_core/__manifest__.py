# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing Core',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Marketing skill registry, AARRR plans, idea bank, KPIs',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': ['base', 'mail', 'crm', 'sale_management', 'social_marketing'],
    'data': [
        'security/marketing_security.xml',
        'security/ir.model.access.csv',
        'data/marketing_skill.xml',
        'views/marketing_skill_views.xml',
        'views/marketing_plan_views.xml',
        'views/marketing_context_views.xml',
        'wizards/skill_import_wizard_views.xml',
        'views/marketing_menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
