# Odoo Marketing — Developer Guide

## Dependencies

- `marketing_core`: `base`, `mail`, `crm`, `sale_management`, `social_marketing`, `strategy_core`
- `marketing_ai`: `marketing_core`, `ai_agent`
- `marketing_dashboard`: `marketing_core`, `dashboard_vrtl`

## Conventions

- All secrets in Salt pillar, never in files
- Skills stored as SKILL.md in `skills/`, imported via `data/marketing_skill.xml`
- Module author: Vertel Sverige AB, license: AGPL-3
- English-only code, sv.po for user-facing strings
- NEVER store plans or customer context in git — those are Odoo-only
