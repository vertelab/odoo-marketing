# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Marketing Strategy Bridge',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Bridge between Marketing Core and Strategy Core — BMC auto-population',
    'description': """
Marketing Strategy Bridge
=========================

Connects `marketing_core` with `strategy_core` without coupling the
core module to the strategy stack.

- Adds a Business Model Canvas (BMC) link on marketing.plan
- Auto-populates Acquisition/Revenue plan sections from the BMC on change

Auto-installed when both marketing_core and strategy_core are present.
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-marketing',
    'license': 'AGPL-3',
    'depends': ['marketing_core', 'strategy_core'],
    'data': [
        'security/ir.model.access.csv',
        'views/marketing_plan_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
