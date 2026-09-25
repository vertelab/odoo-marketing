# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """Extend res.config.settings with competitor monitor configuration."""

    _inherit = 'res.config.settings'

    # ── LinkedIn Monitor ──
    competitor_linkedin_email = fields.Char(
        string='LinkedIn Email',
        config_parameter='competitor_linkedin.email',
        help='LinkedIn account email for competitor monitoring',
    )
    competitor_linkedin_password = fields.Char(
        string='LinkedIn Password',
        config_parameter='competitor_linkedin.password',
        password=True,
        help='LinkedIn account password (stored encrypted in database)',
    )
    competitor_linkedin_connected = fields.Boolean(
        string='LinkedIn Connected',
        compute='_compute_linkedin_connected',
        readonly=True,
    )

    # ── YouTube Monitor ──
    competitor_youtube_api_key = fields.Char(
        string='YouTube API Key',
        config_parameter='competitor_youtube.api_key',
        help='YouTube Data API v3 key (optional — RSS works without it)',
    )

    @api.depends('competitor_linkedin_email', 'competitor_linkedin_password')
    def _compute_linkedin_connected(self):
        for record in self:
            record.competitor_linkedin_connected = bool(
                record.competitor_linkedin_email and record.competitor_linkedin_password
            )

    def action_test_linkedin_connection(self):
        """Test LinkedIn connection by attempting to search for a known company."""
        if not self.competitor_linkedin_email or not self.competitor_linkedin_password:
            raise UserError(_('Please enter LinkedIn email and password first.'))

        try:
            from linkedin_api import Linkedin
            api = Linkedin(
                self.competitor_linkedin_email,
                self.competitor_linkedin_password,
            )
            # Try to search for a company to verify connectivity
            results = api.search_companies(keywords=['LinkedIn'])
            if results is not None:
                raise UserError(
                    _('✅ LinkedIn connection successful! '
                      'Found %d company results.') % len(results)
                )
            else:
                raise UserError(_('Connected but no search results returned.'))
        except ImportError:
            raise UserError(
                _('The linkedin_api library is not installed. '
                  'Please install it: pip install linkedin-api')
            )
        except Exception as e:
            error_msg = str(e)
            if 'CHALLENGE' in error_msg:
                raise UserError(
                    _('⚠️ LinkedIn CHALLENGE detected. '
                      'LinkedIn requires manual verification. '
                      'Log in manually in a browser and try again.\n\n'
                      'Error: %s') % error_msg[:200]
                )
            raise UserError(
                _('❌ LinkedIn connection failed: %s') % error_msg[:200]
            )

    def action_resolve_all_social(self):
        """Resolve LinkedIn and YouTube IDs for all competitors."""
        signal_model = self.env['competitor.social.signal']
        result = signal_model.cron_resolve_all()
        raise UserError(
            _('Social ID resolution completed. Check competitor records for results.')
        )


# ────────────────────────────────────────────────────────────────────────
# Background Jobs — cron-administration (samma mönster som ai_agent_core)
# ────────────────────────────────────────────────────────────────────────

MARKETING_COMPETITOR_CRON_NAMES = [
    'Social Monitor Pull',
    'Social ID Resolution',
]


class ResConfigSettingsCompetitorCron(models.TransientModel):
    _inherit = 'res.config.settings'

    marketing_competitor_cron_line_ids = fields.One2many(
        'marketing.competitor.cron.line', 'settings_id', string='Cron-rader')

    @api.model
    def get_values(self):
        res = super().get_values()
        crons = self.env['ir.cron'].search(
            [('cron_name', 'in', MARKETING_COMPETITOR_CRON_NAMES)], order='cron_name')
        res['marketing_competitor_cron_line_ids'] = [(0, 0, {
            'cron_id': cron.id,
            'cron_active': cron.active,
            'cron_interval_number': cron.interval_number,
            'cron_interval_type': cron.interval_type,
        }) for cron in crons]
        return res

    def set_values(self):
        super().set_values()
        for line in self.marketing_competitor_cron_line_ids:
            if line.cron_id:
                line.cron_id.write({
                    'active': line.cron_active,
                    'interval_number': line.cron_interval_number,
                    'interval_type': line.cron_interval_type,
                })


class MarketingCompetitorCronLine(models.TransientModel):
    """Per-cron konfigurationsrad i Background Jobs-blocket."""
    _name = 'marketing.competitor.cron.line'
    _description = 'Marketing Competitor Monitor cron configuration line'

    settings_id = fields.Many2one('res.config.settings', ondelete='cascade')
    cron_id = fields.Many2one('ir.cron', string='Cron', required=True,
                              ondelete='cascade')
    cron_name = fields.Char(related='cron_id.cron_name', string='Namn',
                            readonly=True)
    cron_active = fields.Boolean(string='Aktiv', default=True)
    cron_interval_number = fields.Integer(string='Intervall', default=1)
    cron_interval_type = fields.Selection([
        ('minutes', 'Minuter'),
        ('hours', 'Timmar'),
        ('days', 'Dagar'),
        ('weeks', 'Veckor'),
        ('months', 'Månader'),
    ], string='Period', default='days')
    cron_lastcall = fields.Datetime(related='cron_id.lastcall',
                                    string='Senaste körning', readonly=True)
    cron_failure_count = fields.Integer(related='cron_id.failure_count',
                                        string='Fel', readonly=True)
    cron_code = fields.Text(related='cron_id.code', string='Metod',
                            readonly=True)

    def action_run_now(self):
        """Kör cron direkt."""
        self.ensure_one()
        if not self.cron_id:
            return False
        model_name = self.cron_id.model
        code = self.cron_id.code
        if model_name and code:
            model = self.env[model_name]
            if code.startswith('model.'):
                method = code[len('model.'):]
                if hasattr(model, method):
                    getattr(model, method)()
        self.cron_id._trigger(at=fields.Datetime.now())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cron triggad',
                'message': f'{self.cron_name} körs nu.',
                'type': 'success',
            },
        }
