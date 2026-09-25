# Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import time
from datetime import datetime, timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CACHE_TTL = 60  # seconds
RATE_LIMIT = 50  # requests per minute
MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # seconds


class WorldMonitorAPI(models.AbstractModel):
    """Abstract model for World Monitor REST API communication.

    Encapsulates all HTTP communication with the World Monitor service.
    Supports caching, rate limiting, retry with exponential backoff,
    and provides typed fetch methods for WM endpoints.
    """

    _name = 'world.monitor.api'
    _description = 'World Monitor API Client'

    # ── In-memory cache (not stored in DB) ──
    _cache = {}
    _rate_limit_log = []

    # ── Configuration helpers ──

    def _get_base_url(self):
        """Read base URL from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('world_monitor.base_url', 'https://worldmonitor.vertel.se')

    def _get_api_key(self):
        """Read API key from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('world_monitor.api_key', '')

    def _get_verify_ssl(self):
        """Read SSL verification setting."""
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('world_monitor.verify_ssl', 'True').lower() == 'true'

    def _get_tier(self):
        """Read the WM tier from settings."""
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('world_monitor.tier', 'basic')

    def _get_headers(self):
        """Build standard request headers."""
        api_key = self._get_api_key()
        if not api_key:
            raise UserError(_(
                'World Monitor API key is not configured. '
                'Go to Settings → Marketing → World Monitor to set it up.'
            ))
        return {
            'X-WorldMonitor-Key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    # ── Rate limiting ──

    def _check_rate_limit(self):
        """Ensure we don't exceed 50 requests per minute (sliding window)."""
        now = time.time()
        # Purge entries older than 60 seconds
        cutoff = now - 60
        self._rate_limit_log = [t for t in self._rate_limit_log if t > cutoff]

        if len(self._rate_limit_log) >= RATE_LIMIT:
            wait = self._rate_limit_log[0] + 60 - now
            if wait > 0:
                _logger.info('Rate limit reached — waiting %.1f seconds', wait)
                time.sleep(wait)
                # Re-check after waiting
                self._rate_limit_log = [t for t in self._rate_limit_log if t > (time.time() - 60)]

        self._rate_limit_log.append(time.time())

    # ── Caching ──

    def _cache_key(self, method, endpoint, params):
        """Generate a cache key for a request."""
        return f'{method}:{endpoint}:{json.dumps(params, sort_keys=True)}'

    def _get_cached(self, key):
        """Return cached response if fresh, else None."""
        entry = self._cache.get(key)
        if entry and entry['timestamp'] + CACHE_TTL > time.time():
            return entry['response']
        return None

    def _set_cache(self, key, response):
        """Store response in cache."""
        self._cache[key] = {
            'timestamp': time.time(),
            'response': response,
        }

    def _clear_cache(self):
        """Clear all cached responses."""
        self._cache.clear()

    # ── Core HTTP call ──

    def call(self, method='GET', endpoint='/', params=None, data=None,
             use_cache=True, timeout=30):
        """Make an HTTP request to the World Monitor API.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path (e.g. '/api/news/v1/list-feed-digest')
            params: URL query parameters (dict)
            data: Request body for POST (dict)
            use_cache: Whether to use/update cache
            timeout: Request timeout in seconds

        Returns:
            dict: Parsed JSON response from WM

        Raises:
            UserError: On invalid API key or unreachable service
        """
        base_url = self._get_base_url()
        api_key = self._get_api_key()
        verify_ssl = self._get_verify_ssl()

        if not api_key:
            raise UserError(_(
                'World Monitor is not configured. '
                'Go to Settings → Marketing → World Monitor to set up your API key.'
            ))

        # Check cache
        if use_cache:
            cache_key = self._cache_key(method, endpoint, params)
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = f'{base_url.rstrip("/")}{endpoint}'
        headers = self._get_headers()

        last_exception = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                self._check_rate_limit()

                if method.upper() == 'GET':
                    resp = requests.get(
                        url, headers=headers, params=params,
                        timeout=timeout, verify=verify_ssl,
                    )
                elif method.upper() == 'POST':
                    resp = requests.post(
                        url, headers=headers, params=params, json=data,
                        timeout=timeout, verify=verify_ssl,
                    )
                else:
                    raise ValueError(f'Unsupported HTTP method: {method}')

                # 401 — invalid key
                if resp.status_code == 401:
                    raise UserError(_(
                        'Invalid World Monitor API key. '
                        'Please update your API key in Settings → Marketing → World Monitor.'
                    ))

                # 429 — rate limited, retry with backoff
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', BACKOFF_BASE ** (attempt + 1)))
                    _logger.warning(
                        'WM rate limited (attempt %d/%d). Waiting %ds.',
                        attempt + 1, MAX_RETRIES, retry_after,
                    )
                    time.sleep(retry_after)
                    continue

                # Other non-2xx
                if not resp.ok:
                    _logger.error(
                        'WM API error %d: %s', resp.status_code, resp.text[:500]
                    )
                    result = {'error': resp.status_code, 'message': resp.text[:500]}
                    if use_cache:
                        self._set_cache(cache_key, result)
                    return result

                # Success
                result = resp.json()

                if use_cache:
                    self._set_cache(cache_key, result)

                return result

            except (requests.ConnectionError, requests.Timeout) as e:
                last_exception = e
                _logger.warning(
                    'WM unreachable (attempt %d/%d): %s',
                    attempt + 1, MAX_RETRIES, str(e),
                )
                if attempt < MAX_RETRIES:
                    sleep_time = BACKOFF_BASE ** (attempt + 1)
                    time.sleep(sleep_time)
                continue

        # All retries exhausted
        _logger.error('WM API unreachable after %d attempts: %s', MAX_RETRIES, last_exception)

        # Try to return stale cache
        if use_cache:
            cache_key = self._cache_key(method, endpoint, params)
            stale = self._cache.get(cache_key)
            if stale:
                _logger.warning('Returning stale cached data for %s', endpoint)
                stale['response']['stale'] = True
                return stale['response']

        raise UserError(_(
            'World Monitor is currently unreachable. '
            'Please try again later. If the issue persists, contact support.'
        ))

    # ── Typed fetch methods ──

    def fetch_events(self, category=None, country=None, since=None, limit=100):
        """Fetch news feed events from World Monitor.

        Args:
            category: Filter by category (string or None)
            country: Filter by country code (e.g. 'SE')
            since: Fetch events since this datetime
            limit: Max number of events to return

        Returns:
            list[dict]: Events from WM
        """
        params = {'limit': min(limit, 500)}
        if category:
            params['category'] = category
        if country:
            params['country'] = country
        if since:
            if isinstance(since, datetime):
                since = since.isoformat()
            params['since'] = since

        result = self.call('GET', '/api/news/v1/list-feed-digest', params=params)
        return result.get('data', result.get('events', [result]
                                             if isinstance(result, dict) and 'id' in result
                                             else []))

    def fetch_world_brief(self, geo_context=None):
        """Fetch AI-summarized world intelligence brief.

        Args:
            geo_context: Optional geographic context (e.g. 'SE', 'EU')

        Returns:
            dict: Brief content with summary, events, risks
        """
        params = {}
        if geo_context:
            params['geo_context'] = geo_context

        return self.call('GET', '/api/news/v1/list-feed-digest', params=params)

    def fetch_country_brief(self, country_code):
        """Fetch per-country intelligence brief.

        Args:
            country_code: ISO country code (e.g. 'SE', 'US')

        Returns:
            dict: Country-specific intelligence
        """
        return self.call(
            'GET', '/api/intelligence/v1/get-country-intel-brief',
            params={'country_code': country_code},
        )

    def fetch_news_intelligence(self, query, limit=20):
        """Fetch cross-source news intelligence.

        Args:
            query: Search query string
            limit: Max results to return

        Returns:
            list[dict]: News intelligence results
        """
        result = self.call(
            'GET', '/api/intelligence/v1/list-cross-source-signals',
            params={'query': query, 'limit': min(limit, 100)},
        )
        return result.get('data', result.get('results', [result]
                                             if isinstance(result, dict) and 'id' in result
                                             else []))

    def check_connection(self):
        """Test API connectivity by calling health endpoint.

        Returns:
            dict with 'status' (ok/error) and optional 'message'
        """
        api_key = self._get_api_key()
        if not api_key:
            return {'status': 'not_configured', 'message': _('No API key configured')}

        try:
            result = self.call('GET', '/api/health/v1/health', use_cache=False, timeout=10)
            return {'status': 'ok', 'data': result}
        except UserError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
