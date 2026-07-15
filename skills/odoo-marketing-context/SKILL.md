---
name: odoo-marketing-context
description: Connect Pi agent to Odoo marketing skills and data via XML-RPC.
  Use when any marketing skill needs Odoo context — CRM data, sales data,
  customer profiles, or marketing plans. Automatically activated when
  Pi loads a marketing skill from Odoo.
metadata:
  version: 1.0.0
---

# Odoo Marketing Context

You are connected to an Odoo instance that serves as the runtime registry
for marketing skills. All 46+ skills live as `marketing.skill` records.

## Connection

```python
import xmlrpc.client

url = "https://{customer}.vertel.se"
db = "{customer}_db"
username = "pi_agent"
password = os.environ.get("ODOO_PI_PASSWORD")

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
```

## Loading Skills

```python
# All skills (marketing + strategy)
skills = models.execute_kw(db, uid, pwd,
    'marketing.skill', 'search_read',
    [[['is_active', '=', True]]],
    {'fields': ['name', 'description', 'category', 'skill_content']})

# Specific skill
skill = models.execute_kw(db, uid, pwd,
    'marketing.skill', 'search_read',
    [[['name', '=', 'marketing-plan']]],
    {'fields': ['skill_content']})
```

## Core Marketing Models

| Model | Access | Purpose |
|-------|--------|---------|
| `marketing.plan` | Read/Write | AARRR marketing plans |
| `marketing.context` | Read | Customer ICP, brand voice |
| `marketing.idea` | Read | 139 ideas by AARRR stage |
| `marketing.kpi` | Read | KPI definitions |

## Base Data (read-only)

- `res.partner` — customers, segments
- `crm.lead` — pipeline, conversion data
- `sale.order` — revenue, products
- `social_marketing.post` — social media history
- `mailing.trace` — email campaign stats

## Writing Results

```python
models.execute_kw(db, uid, pwd,
    'marketing.plan', 'create',
    [{'name': '...', 'customer_id': customer_id,
      'plan_markdown': generated_markdown, 'state': 'active'}])
```

## Security

- **Read-only**: res.partner, crm.lead, sale.order, social_marketing.*, mailing.*
- **Read/Write**: marketing.plan, marketing.plan.line
- **Never** modify user passwords or accounting data
