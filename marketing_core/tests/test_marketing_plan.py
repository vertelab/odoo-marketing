# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMarketingPlan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})

    def test_create_plan(self):
        plan = self.env['marketing.plan'].create({
            'name': 'Test Plan',
            'customer_id': self.partner.id,
        })
        self.assertEqual(plan.state, 'draft')

    def test_plan_lifecycle(self):
        plan = self.env['marketing.plan'].create({
            'name': 'Lifecycle Plan',
            'customer_id': self.partner.id,
        })
        plan.action_activate()
        self.assertEqual(plan.state, 'active')

        plan.action_complete()
        self.assertEqual(plan.state, 'completed')

        plan.action_archive()
        self.assertEqual(plan.state, 'archived')

        plan.action_draft()
        self.assertEqual(plan.state, 'draft')

    def test_plan_generated_by(self):
        plan = self.env['marketing.plan'].create({
            'name': 'Agent Plan',
            'customer_id': self.partner.id,
            'generated_by': 'pi-agent',
            'skill_version': '2.0.0',
        })
        self.assertEqual(plan.generated_by, 'pi-agent')
        self.assertEqual(plan.skill_version, '2.0.0')
