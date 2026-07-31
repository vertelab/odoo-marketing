# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing World',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'World Monitor integration — omvärldsbevakning, events, triage, briefs, reports',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': [
        'marketing_core',
        'strategy_core',
        'ai_agent_core_strategy',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/marketing_world_security.xml',
        'data/world_cron.xml',
        'data/world_skill.xml',
        'data/world_report_templates.xml',
        'views/world_settings.xml',
        'views/world_event_views.xml',
        'views/world_brief_views.xml',
        'views/world_report_views.xml',
        'views/world_competitor_views.xml',
        'views/world_dashboard.xml',
        'views/world_menu_views.xml',
        'views/res_company_views.xml',
        'views/world_triage_views.xml',
        'wizards/world_triage_wizard_views.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
