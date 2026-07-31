# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """Extend res.config.settings with World Monitor configuration."""

    _inherit = 'res.config.settings'

    # ── System-wide settings ──

    world_monitor_enabled = fields.Boolean(
        string='World Monitor Enabled',
        default=False,
        config_parameter='world_monitor.enabled',
    )
    world_monitor_api_key = fields.Char(
        string='World Monitor API Key',
        config_parameter='world_monitor.api_key',
        password=True,
        help='API key for World Monitor service. Get yours at worldmonitor.vertel.se',
    )
    world_monitor_base_url = fields.Char(
        string='World Monitor Base URL',
        default='https://worldmonitor.vertel.se',
        config_parameter='world_monitor.base_url',
    )
    world_monitor_tier = fields.Selection([
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ], string='World Monitor Tier',
        default='basic',
        config_parameter='world_monitor.tier',
    )
    world_monitor_verify_ssl = fields.Boolean(
        string='Verify SSL',
        default=True,
        config_parameter='world_monitor.verify_ssl',
    )

    # ── Computed connection status ──

    world_monitor_connection_status = fields.Char(
        string='Connection Status',
        compute='_compute_world_monitor_connection_status',
        readonly=True,
    )

    @api.depends('world_monitor_api_key', 'world_monitor_base_url')
    def _compute_world_monitor_connection_status(self):
        """Check and display WM connection status."""
        for record in self:
            if not record.world_monitor_api_key:
                record.world_monitor_connection_status = '⚪ Not configured'
                continue
            try:
                wm_api = self.env['world.monitor.api']
                result = wm_api.check_connection()
                if result['status'] == 'ok':
                    record.world_monitor_connection_status = \
                        '🟢 Connected'
                else:
                    record.world_monitor_connection_status = \
                        f'🔴 Disconnected ({result.get("message", "Unknown error")[:50]})'
            except Exception:
                record.world_monitor_connection_status = '🔴 Disconnected'

    # ── Validation ──

    @api.onchange('world_monitor_api_key')
    def _onchange_world_monitor_api_key(self):
        """Validate API key when changed in the UI."""
        if self.world_monitor_api_key and self.world_monitor_enabled:
            self._test_world_monitor_connection()

    def _test_world_monitor_connection(self):
        """Test World Monitor connection and return status."""
        wm_api = self.env['world.monitor.api']
        result = wm_api.check_connection()
        if result['status'] == 'ok':
            return {'status': 'ok'}
        elif result['status'] == 'not_configured':
            return {'status': 'warning', 'message': _('No API key configured')}
        else:
            return {'status': 'error', 'message': result.get('message', '')}

    @api.constrains('world_monitor_api_key', 'world_monitor_enabled')
    def _check_world_monitor_api_key(self):
        """Validate API key on save."""
        for record in self:
            if record.world_monitor_enabled and record.world_monitor_api_key:
                try:
                    wm_api = self.env['world.monitor.api']
                    result = wm_api.check_connection()
                    if result['status'] == 'error':
                        # Don't block save — just warn
                        _logger.warning(
                            'World Monitor connection test failed: %s',
                            result.get('message', ''),
                        )
                except Exception:
                    pass  # Connection issues shouldn't block settings save

    def action_test_world_monitor_connection(self):
        """Test button that validates the API key immediately."""
        wm_api = self.env['world.monitor.api']
        result = wm_api.check_connection()
        if result['status'] == 'ok':
            raise UserError(_('Connection successful! World Monitor is reachable.'))
        elif result['status'] == 'not_configured':
            raise UserError(_('Please enter a World Monitor API key first.'))
        else:
            raise UserError(
                _('Connection failed: %s') % result.get('message', _('Unknown error'))
            )

    def set_values(self):
        """Override to validate API key on save."""
        super().set_values()
        # If enabled and api key is set, do a quick validation
        if self.world_monitor_enabled and self.world_monitor_api_key:
            try:
                wm_api = self.env['world.monitor.api']
                result = wm_api.check_connection()
                if result['status'] == 'not_configured':
                    _logger.info('World Monitor: no API key configured')
                elif result['status'] == 'error':
                    _logger.warning(
                        'World Monitor: connection test failed: %s',
                        result.get('message', ''),
                    )
            except Exception as e:
                _logger.warning(
                    'World Monitor: connection test raised: %s',
                    str(e),
                )
