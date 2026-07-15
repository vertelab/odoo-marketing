# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os
import yaml
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MarketingSkillImport(models.TransientModel):
    _name = 'marketing.skill.import'
    _description = 'Import Marketing Skills from SKILL.md files'

    def action_import(self):
        skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'skills'
        )
        if not os.path.isdir(skills_dir):
            return {'type': 'ir.actions.act_window_close'}

        imported = 0
        updated = 0

        for skill_name in sorted(os.listdir(skills_dir)):
            skill_path = os.path.join(skills_dir, skill_name, 'SKILL.md')
            if not os.path.isfile(skill_path):
                continue

            try:
                frontmatter, body = self._parse_skill_md(skill_path)
            except Exception as e:
                _logger.warning('Failed to parse %s: %s', skill_path, e)
                continue

            name = frontmatter.get('name', skill_name)
            desc = frontmatter.get('description', '')
            # Auto-detect category from skill name/description
            category = self._detect_category(name, desc)

            existing = self.env['marketing.skill'].search([
                ('name', '=', name)
            ], limit=1)

            vals = {
                'name': name,
                'description': desc,
                'category': category,
                'version': (frontmatter.get('metadata') or {}).get('version', '1.0.0'),
                'skill_content': body,
                'skill_path': 'skills/%s/SKILL.md' % skill_name,
                'is_base': True,
                'is_active': True,
                'module_origin': 'marketing_core',
            }

            if existing:
                existing.write(vals)
                updated += 1
            else:
                self.env['marketing.skill'].create(vals)
                imported += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Skills Imported'),
                'message': _('%d new, %d updated') % (imported, updated),
                'type': 'success',
            },
        }

    def _parse_skill_md(self, path):
        with open(path, 'r') as f:
            content = f.read()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                return frontmatter, body
        return {}, content.strip()

    def _detect_category(self, name, description):
        desc_lower = (name + ' ' + description).lower()
        if any(w in desc_lower for w in ['strateg', 'plan', 'idea', 'launch', 'pric']):
            return 'strategy'
        if any(w in desc_lower for w in ['content', 'copy', 'social', 'video', 'image']):
            return 'content'
        if any(w in desc_lower for w in ['ad', 'cold', 'prospect', 'lead', 'email']):
            return 'acquisition'
        if any(w in desc_lower for w in ['seo', 'schema', 'site-architect']):
            return 'seo'
        if any(w in desc_lower for w in ['cro', 'ab-test', 'signup', 'onboard', 'popup', 'paywall']):
            return 'conversion'
        if any(w in desc_lower for w in ['churn', 'retention', 'sms']):
            return 'retention'
        if any(w in desc_lower for w in ['analyt', 'competitor', 'research', 'revops']):
            return 'analytics'
        if any(w in desc_lower for w in ['referral', 'co-market', 'communit', 'free-tool', 'pr', 'sales-enable']):
            return 'referral'
        return 'strategy'
