# odoo-marketing
Marketing addons

## AI-integration (bridges)

**Princip: AI-förmågor (coworkers, skills, sessions) läggs ENBART i `_ai`-moduler — aldrig i domän-core.**

| Modul | Roll |
|-------|------|
| `marketing_core` | Ren domänlogik (AARRR, skills-registry, ideas, KPI) — **ingen AI-kod** |
| `marketing_ai` | **AI-brygga**: 5 coworkers (Content Strategist, SEO Specialist, Ads Manager, Marketing Analyst, Marketing Planner) + 8 `ai.skill`-poster (data-XML, mönster `social_ai`) |
| `marketing_world` | World Monitor: events, triage, briefs, rapporter; `cron_triage_events()` anropar coworker `World Intelligence Triage` via `coworker.run()` |

### Lägga till ny AI-förmåga
1. Lägg coworker-data i `marketing_ai/data/marketing_coworkers.xml` (model `ai.coworker`)
2. Lägg skill-data i `marketing_ai/data/marketing_skills.xml` (model `ai.skill`)
3. Koppla `skill_ids` på coworkern (M2M)
4. Använd giltiga `category`-värden: `accounting, development, infrastructure, analysis, communication, research, general`
