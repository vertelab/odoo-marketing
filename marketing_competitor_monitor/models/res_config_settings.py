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
