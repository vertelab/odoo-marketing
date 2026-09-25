# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MarketingWorldReportTemplate(models.Model):
    """Template for structured world monitoring reports."""

    _name = 'marketing.world.report.template'
    _description = 'World Report Template'
    _order = 'name'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    periodicity = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('per_meeting', 'Per Meeting'),
    ], string='Periodicity', required=True, default='monthly')
    period_day = fields.Integer('Period Day', default=1,
                                 help='Day of week (1-7) or day of month (1-31)')
    active = fields.Boolean('Active', default=True)

    # ── DMS integration ──
    dms_directory_id = fields.Many2one(
        'dms.directory', string='DMS Directory',
        help='DMS directory where generated reports are stored',
    )

    # ── Sections ──
    section_ids = fields.One2many(
        'marketing.world.report.section', 'template_id',
        string='Sections',
        copy=True,
    )

    # ── Links ──
    customer_id = fields.Many2one(
        'res.partner', string='Customer',
        domain="[('is_company', '=', True)]",
        ondelete='set null',
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )

    # ── Computed ──
    last_report_date = fields.Date('Last Report Date', compute='_compute_last_report_date')
    next_run_date = fields.Date('Next Run Date', compute='_compute_next_run_date')

    def _compute_last_report_date(self):
        Report = self.env['marketing.world.report']
        for record in self:
            last = Report.search([
                ('template_id', '=', record.id),
            ], limit=1, order='period_end desc')
            record.last_report_date = last.period_end if last else False

    def _compute_next_run_date(self):
        today = fields.Date.today()
        for record in self:
            if not record.active:
                record.next_run_date = False
                continue
            last = record.last_report_date or today
            if record.periodicity == 'weekly':
                next_date = last + timedelta(days=7)
            elif record.periodicity == 'monthly':
                next_date = last + timedelta(days=30)
            elif record.periodicity == 'quarterly':
                next_date = last + timedelta(days=90)
            else:
                next_date = last
            record.next_run_date = next_date if next_date > today else today


class MarketingWorldReportSection(models.Model):
    """Section within a report template."""

    _name = 'marketing.world.report.section'
    _description = 'World Report Section'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    template_id = fields.Many2one(
        'marketing.world.report.template', string='Template',
        ondelete='cascade', required=True,
    )
    ai_prompt = fields.Text(
        'AI Prompt',
        help='Instructions for the AI on how to generate this section.\n'
             'Example: "Analysera veckans händelser inom ekonomi och bedöm påverkan '
             'på kundens bransch. Motivera din bedömning."',
    )


class MarketingWorldReport(models.Model):
    """Generated report based on a template."""

    _name = 'marketing.world.report'
    _description = 'World Monitor Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period_end desc, id desc'
    _rec_name = 'name'

    # ── Identity ──
    name = fields.Char('Name', compute='_compute_name', store=True)
    template_id = fields.Many2one(
        'marketing.world.report.template', string='Template',
        required=True, ondelete='cascade',
    )
    customer_id = fields.Many2one(
        'res.partner', string='Customer',
        domain="[('is_company', '=', True)]",
        ondelete='set null',
    )
    period_start = fields.Date('Period Start')
    period_end = fields.Date('Period End')

    # ── Content ──
    section_data = fields.Json(
        'Section Data',
        help='AI-generated content per section, with assessment and reasoning',
    )

    # ── State ──
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'In Review'),
        ('approved', 'Approved'),
        ('signed', 'Signed'),
        ('archived', 'Archived'),
    ], string='State', required=True, default='draft', tracking=True)

    # ── DMS / File ──
    dms_file_id = fields.Many2one(
        'dms.file', string='DMS File',
        help='The generated PDF stored in DMS',
    )
    ir_attachment_id = fields.Many2one(
        'ir.attachment', string='Attachment',
        help='Fallback when DMS is not available',
    )
    sign_request_id = fields.Many2one(
        'sign.request', string='Sign Request',
        help='Digital signing request for this report',
    )

    # ── Metadata ──
    generated_at = fields.Datetime('Generated At', readonly=True)
    generated_by_id = fields.Many2one('res.users', string='Generated By')
    version = fields.Integer('Version', default=1, readonly=True)

    # ── Links ──
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    event_ids = fields.Many2many(
        'marketing.world.event', 'world_report_event_rel',
        'report_id', 'event_id',
        string='Source Events',
    )

    @api.depends('template_id', 'customer_id', 'period_end')
    def _compute_name(self):
        for record in self:
            parts = [record.template_id.name or '']
            if record.customer_id:
                parts.append(record.customer_id.name)
            if record.period_end:
                parts.append(str(record.period_end))
            record.name = ' — '.join(parts)

    # ── State transitions ──

    def action_request_review(self):
        """Move to review state."""
        for record in self:
            if record.state == 'draft':
                record.state = 'review'

    def action_approve(self):
        """Approve the report."""
        for record in self:
            if record.state == 'review':
                record.state = 'approved'

    def action_request_changes(self):
        """Send back to draft for changes."""
        for record in self:
            if record.state == 'review':
                record.state = 'draft'

    def action_archive(self):
        """Archive the report."""
        for record in self:
            if record.state not in ('archived',):
                record.state = 'archived'

    # ── Generation ──

    def action_generate_sections_from_template(self):
        """Generate section placeholders from template."""
        for report in self:
            if report.state != 'draft':
                raise UserError(_('Can only generate sections in draft state.'))
            sections = []
            for section in report.template_id.section_ids:
                sections.append({
                    'sequence': section.sequence,
                    'name': section.name,
                    'content': '',
                    'assessment': '',
                    'reasoning': '',
                    'source_event_ids': [],
                })
            report.section_data = {'sections': sections}

    # ── Cron ──

    @api.model
    def cron_generate_reports(self):
        """Generate reports per template schedule.
        Called by ir.cron daily.
        """
        today = fields.Date.today()
        templates = self.env['marketing.world.report.template'].search([
            ('active', '=', True),
        ])
        generated = 0
        for template in templates:
            try:
                next_run = template.next_run_date
                if not next_run or next_run > today:
                    continue

                period_start, period_end = self._compute_period(template)
                report = self.create({
                    'template_id': template.id,
                    'customer_id': template.customer_id.id,
                    'period_start': period_start,
                    'period_end': period_end,
                    'state': 'draft',
                    'generated_at': fields.Datetime.now(),
                    'generated_by_id': self.env.ref('base.user_root').id,
                    'company_id': template.company_id.id,
                })
                report.action_generate_sections_from_template()
                generated += 1
            except Exception as e:
                _logger.error(
                    'Report generation failed for template %s: %s',
                    template.name, str(e),
                )
        _logger.info('World Report Generator: %d reports created', generated)
        return generated

    @api.model
    def _compute_period(self, template):
        """Compute period start/end based on template periodicity."""
        today = fields.Date.today()
        if template.periodicity == 'weekly':
            end = today
            start = today - timedelta(days=7)
        elif template.periodicity == 'monthly':
            end = today
            start = today - timedelta(days=30)
        elif template.periodicity == 'quarterly':
            end = today
            start = today - timedelta(days=90)
        else:
            end = today
            start = today - timedelta(days=7)
        return start, end
