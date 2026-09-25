# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Post-install hook: create World Monitor coworkers."""

import logging

from odoo import fields

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Create AI coworkers for World Monitor integration after module installation.

    Creates:
    - "World Intelligence Triage" (cron, every 6h)
    - "World Brief Generator" (cron, weekly Monday 08:00)
    - "World Report Generator" (cron, daily)
    - "Meeting Prep World" (powerbox, linked to strategy.meeting)
    - "World Monitor Chat" (chat)
    """

    # ── Check idempotency ──
    existing = env['ai.coworker'].search([
        ('name', '=', 'World Intelligence Triage'),
    ])
    if existing:
        _logger.info('World Monitor coworkers already exist — skipping creation')
        return

    # ── Resolve skills ──
    Skill = env['ai.skill']
    skill_triage = Skill.search([('name', '=', 'market-intelligence-triage')], limit=1)
    skill_brief = Skill.search([('name', '=', 'world-brief-generator')], limit=1)
    skill_report = Skill.search([('name', '=', 'world-report-generator')], limit=1)
    skill_meeting = Skill.search([('name', '=', 'meeting-prep-world')], limit=1)
    skill_query = Skill.search([('name', '=', 'world-monitor-query')], limit=1)

    # ── Resolve model IDs ──
    strategy_meeting_model = env['ir.model'].search([
        ('model', '=', 'strategy.meeting'),
    ], limit=1)

    # ── 1. World Intelligence Triage (cron) ──
    triage = env['ai.coworker'].create({
        'name': 'World Intelligence Triage',
        'description': (
            'AI-driven relevance assessment for world monitoring events. '
            'Evaluates all untriaged events every 6 hours, '
            'classifies relevance (direct/indirect/monitor), '
            'and escalates critical risks to strategy.risk.'
        ),
        'sub_description': 'Automatic triage av omvärldshändelser',
        'init_type': 'cron',
        'status': 'active',
        'is_supervisor': False,
    })

    if skill_triage:
        env['ai.coworker.skill'].create({
            'coworker_id': triage.id,
            'source_skill_id': skill_triage.id,
        })

    if skill_query:
        env['ai.coworker.skill'].create({
            'coworker_id': triage.id,
            'source_skill_id': skill_query.id,
        })

    _logger.info('Created coworker "World Intelligence Triage"')

    # ── 2. World Brief Generator (cron, weekly) ──
    brief = env['ai.coworker'].create({
        'name': 'World Brief Generator',
        'description': (
            'Weekly world monitoring brief per customer. '
            'Generates structured omvärldsanalyser with summary, '
            'key events, risk changes, and recommendations. '
            'Runs every Monday 08:00.'
        ),
        'sub_description': 'Weekly omvärldsanalys per kund',
        'init_type': 'cron',
        'status': 'active',
        'is_supervisor': False,
    })

    if skill_brief:
        env['ai.coworker.skill'].create({
            'coworker_id': brief.id,
            'source_skill_id': skill_brief.id,
        })

    if skill_triage:
        env['ai.coworker.skill'].create({
            'coworker_id': brief.id,
            'source_skill_id': skill_triage.id,
        })

    _logger.info('Created coworker "World Brief Generator"')

    # ── 3. World Report Generator (cron, daily) ──
    report = env['ai.coworker'].create({
        'name': 'World Report Generator',
        'description': (
            'Generates formal world monitoring reports per template. '
            'Checks all active report templates daily and generates '
            'reports according to their periodicity (weekly/monthly/quarterly).'
        ),
        'sub_description': 'Formal report generation from templates',
        'init_type': 'cron',
        'status': 'active',
        'is_supervisor': False,
    })

    if skill_report:
        env['ai.coworker.skill'].create({
            'coworker_id': report.id,
            'source_skill_id': skill_report.id,
        })

    _logger.info('Created coworker "World Report Generator"')

    # ── 4. Meeting Prep World (powerbox) ──
    meeting = env['ai.coworker'].create({
        'name': 'Meeting Prep World',
        'description': (
            'Prepare world monitoring content for strategy meetings. '
            'Reads the most recent brief and risk changes, '
            'then creates agenda item "Omvärldsbevakning" '
            'on the strategy.meeting record.'
        ),
        'sub_description': 'Add world monitoring to meeting agenda',
        'init_type': 'powerbox',
        'status': 'active',
        'is_supervisor': False,
    })

    if strategy_meeting_model:
        meeting.write({
            'model_ids': [(6, 0, [strategy_meeting_model.id])],
        })

    if skill_meeting:
        env['ai.coworker.skill'].create({
            'coworker_id': meeting.id,
            'source_skill_id': skill_meeting.id,
        })

    if skill_brief:
        env['ai.coworker.skill'].create({
            'coworker_id': meeting.id,
            'source_skill_id': skill_brief.id,
        })

    _logger.info('Created coworker "Meeting Prep World"')

    # ── 5. World Monitor Chat (chat) ──
    chat = env['ai.coworker'].create({
        'name': 'World Monitor Chat',
        'description': (
            'Ad-hoc world monitoring questions. Ask about global events, '
            'geopolitical risks, market intelligence, or competitor movements. '
            'The AI queries World Monitor directly via MCP tools.'
        ),
        'sub_description': 'Ask about world events and intelligence',
        'init_type': 'chat',
        'status': 'active',
        'is_supervisor': False,
    })

    if skill_query:
        env['ai.coworker.skill'].create({
            'coworker_id': chat.id,
            'source_skill_id': skill_query.id,
        })

    _logger.info('Created coworker "World Monitor Chat"')

    # ── 6. World Competitor Battle Card (powerbox) ──
    skill_battle_card = Skill.search([
        ('name', '=', 'world-competitor-battle-card'),
    ], limit=1)

    competitor_model = env['ir.model'].search([
        ('model', '=', 'marketing.world.competitor'),
    ], limit=1)

    battle_card = env['ai.coworker'].create({
        'name': 'World Competitor Battle Card',
        'description': (
            'Generate structured battle cards for tracked competitors. '
            'Combines World Monitor news intelligence with Odoo event data '
            'to produce competitive SWOT analysis, recent movements timeline, '
            'positioning assessment, and concrete counter-strategies.'
        ),
        'sub_description': 'AI-powered competitor battle cards',
        'init_type': 'powerbox',
        'status': 'active',
        'is_supervisor': False,
    })

    if competitor_model:
        battle_card.write({
            'model_ids': [(6, 0, [competitor_model.id])],
        })

    if skill_battle_card:
        env['ai.coworker.skill'].create({
            'coworker_id': battle_card.id,
            'source_skill_id': skill_battle_card.id,
        })

    _logger.info('Created coworker "World Competitor Battle Card"')

    # ── Summary ──
    _logger.info(
        'marketing_world post_init_hook: 6 coworkers created '
        '(1 triage, 1 brief, 1 report, 1 meeting, 1 chat, 1 battle card)'
    )
