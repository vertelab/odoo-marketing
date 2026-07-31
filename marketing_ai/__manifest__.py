# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing AI',
    'version': '18.0.1.1.0',
    'category': 'Marketing',
    'summary': 'AI coworkers and skills for marketing — bridge into ai_agent_core',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': ['marketing_core', 'ai_agent_core'],
    'data': [
        'security/ir.model.access.csv',
        'data/marketing_skills.xml',
        'data/marketing_coworkers.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
