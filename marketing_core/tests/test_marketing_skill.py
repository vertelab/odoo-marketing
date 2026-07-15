# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMarketingSkill(TransactionCase):

    def test_create_skill(self):
        skill = self.env['marketing.skill'].create({
            'name': 'test-skill',
            'description': 'A test skill',
            'category': 'strategy',
            'skill_content': '# Test Skill\n\nThis is a test.',
        })
        self.assertTrue(skill.is_base)
        self.assertTrue(skill.is_active)

    def test_skill_unique_name(self):
        self.env['marketing.skill'].create({
            'name': 'unique-skill',
            'description': 'First',
            'category': 'strategy',
        })
        with self.assertRaises(Exception):
            self.env['marketing.skill'].create({
                'name': 'unique-skill',
                'description': 'Duplicate',
                'category': 'strategy',
            })

    def test_skill_version_tracking(self):
        skill = self.env['marketing.skill'].create({
            'name': 'versioned-skill',
            'description': 'Test',
            'category': 'strategy',
            'version': '2.1.0',
        })
        self.assertEqual(skill.version, '2.1.0')
