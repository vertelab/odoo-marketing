# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing AI',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'AI agent definitions and quest wrappers for marketing skills',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': ['marketing_core', 'ai_agent'],
    'data': [
        'security/ir.model.access.csv',
        'data/marketing_agent_data.xml',
        'data/marketing_tool_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
