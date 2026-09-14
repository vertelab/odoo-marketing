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


# ────────────────────────────────────────────────────────────────────────
# Background Jobs — cron-administration (samma mönster som ai_agent_core)
# ────────────────────────────────────────────────────────────────────────

MARKETING_WORLD_CRON_NAMES = [
    'World Monitor Pull',
    'World Intelligence Triage',
    'World Brief Generator',
    'World Report Generator',
]


class ResConfigSettingsWorldCron(models.TransientModel):
    _inherit = 'res.config.settings'

    marketing_world_cron_line_ids = fields.One2many(
        'marketing.world.cron.line', 'settings_id', string='Cron-rader')

    @api.model
    def get_values(self):
        res = super().get_values()
        crons = self.env['ir.cron'].search(
            [('cron_name', 'in', MARKETING_WORLD_CRON_NAMES)], order='cron_name')
        res['marketing_world_cron_line_ids'] = [(0, 0, {
            'cron_id': cron.id,
            'cron_active': cron.active,
            'cron_interval_number': cron.interval_number,
            'cron_interval_type': cron.interval_type,
        }) for cron in crons]
        return res

    def set_values(self):
        super().set_values()
        for line in self.marketing_world_cron_line_ids:
            if line.cron_id:
                line.cron_id.write({
                    'active': line.cron_active,
                    'interval_number': line.cron_interval_number,
                    'interval_type': line.cron_interval_type,
                })


class MarketingWorldCronLine(models.TransientModel):
    """Per-cron konfigurationsrad i Background Jobs-blocket."""
    _name = 'marketing.world.cron.line'
    _description = 'Marketing World cron configuration line'

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
