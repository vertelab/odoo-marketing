# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MarketingSkill(models.Model):
    """Runtime skill registry — the single source of truth for Pi agents.
    Base skills imported from module data files at install/upgrade.
    Instance-specific skills added via Odoo UI (is_base=False).
    Strategy skills from odoo-strategy are also imported here."""

    _name = 'marketing.skill'
    _description = 'Marketing Skill (SKILL.md in Odoo)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'category, name'
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Skill name must be unique'),
    ]

    name = fields.Char('Skill Name', required=True, index=True)
    description = fields.Text('Description', required=True)
    category = fields.Selection([
        ('strategy', 'Strategy & Planning'),
        ('content', 'Content & Copy'),
        ('acquisition', 'Acquisition'),
        ('seo', 'SEO'),
        ('conversion', 'Conversion'),
        ('retention', 'Retention'),
        ('analytics', 'Analytics & Insights'),
        ('referral', 'Referral & Partners'),
        ('social', 'Social Media'),
    ], string='Category', required=True, index=True)

    # SKILL.md content — THE key field for Pi agents
    skill_content = fields.Text('Skill Content (SKILL.md)',
        help="Full SKILL.md markdown — what Pi agents read and execute")
    skill_content_html = fields.Html('Rendered', compute='_compute_html')

    # Metadata from SKILL.md frontmatter
    version = fields.Char('Version', default='1.0.0')
    triggers = fields.Text('Trigger Phrases',
        help="When this skill should be activated")

    # Dependencies
    tools_needed = fields.Many2many('ai.tool', string='Tools Required')
    odoo_models_used = fields.Many2many('ir.model', string='Odoo Models Used')

    # Status
    is_active = fields.Boolean('Active', default=True)
    is_base = fields.Boolean('Base Skill', default=True,
        help="Imported from module data. False = instance-specific")
    is_verified = fields.Boolean('Verified', default=False)

    # Source tracking
    skill_path = fields.Char('Source Path',
        help="Relative path in skills/ directory")
    module_origin = fields.Char('Module Origin',
        help="Which Odoo module imported this skill")

    # Relations
    plan_ids = fields.One2many('marketing.plan', 'skill_id',
        string='Generated Plans')

    @api.depends('skill_content')
    def _compute_html(self):
        for rec in self:
            if rec.skill_content:
                try:
                    import markdown
                    rec.skill_content_html = markdown.markdown(rec.skill_content)
                except ImportError:
                    rec.skill_content_html = f'<pre>{rec.skill_content}</pre>'
