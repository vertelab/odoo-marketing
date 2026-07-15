# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields


class MarketingQuest(models.Model):
    """ai.quest wrapper — enables marketing skill execution from Odoo UI."""

    _inherit = 'ai.quest'

    marketing_skill_id = fields.Many2one(
        'marketing.skill', 'Marketing Skill',
        help="The marketing skill to execute for this quest"
    )
    marketing_plan_id = fields.Many2one(
        'marketing.plan', 'Marketing Plan',
        help="The plan this quest relates to"
    )

    def execute_marketing_skill(self, skill_name):
        """Load and execute a marketing skill via ai.quest."""
        skill = self.env['marketing.skill'].search([
            ('name', '=', skill_name), ('is_active', '=', True)
        ], limit=1)
        if not skill:
            return False

        self.marketing_skill_id = skill.id

        # Build context from Odoo data
        context = self._build_marketing_context()
        system_prompt = skill.skill_content
        user_prompt = context

        agent = self._get_marketing_agent()
        if agent:
            return agent.trigger_prompt(
                message=f"{system_prompt}\n\n---\n\nContext:\n{user_prompt}"
            )
        return False

    def _build_marketing_context(self):
        """Build context from Odoo data for the skill."""
        parts = []
        if self.marketing_plan_id:
            plan = self.marketing_plan_id
            parts.append(f"Customer: {plan.customer_id.name}")
            parts.append(f"Plan: {plan.name}")
            if plan.bmc_id:
                bmc = plan.bmc_id
                parts.append(f"Customer Segments: {bmc.customer_segments}")
                parts.append(f"Value Propositions: {bmc.value_propositions}")
            context = self.env['marketing.context'].search([
                ('customer_id', '=', plan.customer_id.id)
            ], limit=1)
            if context:
                parts.append(f"ICP: {context.icp}")
                parts.append(f"Brand Voice: {context.brand_voice}")
        return '\n'.join(parts)

    def _get_marketing_agent(self):
        """Find or create a marketing AI agent."""
        return self.env['ai.agent'].search([
            ('ai_type', '=', 'marketing'),
            ('status', '=', 'active'),
        ], limit=1)
