# odoo-marketing — gren 19.0

> **Denna gren är avsiktligt tom.** Modulerna är INTE portade till Odoo 19.
> Grenen finns så att dev-miljöer (`hansolo19`) kan klona den utan att falla,
> men den påstår ingenting om att koden är portad.

## Baseline

| | |
|---|---|
| Källa | `20.0` |
| Moduler | **6** |
| Grenar i repot | `13.0`, `14.0`, `16.0`, `18.0`, `20.0`, `campaign_landsite_3`, `master`, `master10` |

## Moduler

- `marketing_ai`
- `marketing_competitor_monitor`
- `marketing_core`
- `marketing_dashboard`
- `marketing_strategy`
- `marketing_world`

## Blockerare

**2 externa beroenden saknas** i Odoo 19-kärnan och OCA 19.0:

| Beroende | Behövs av |
|---|---|
| `dashboard_vrtl` | `marketing_dashboard` |
| `strategy_core` | `marketing_strategy`, `marketing_world` |

### Prioritering

Ett beroende som blockerar många moduler ger mest nytta att lösa först:

- `strategy_core` — frisläpper **2** modul(er)
- `dashboard_vrtl` — frisläpper **1** modul(er)

## Nästa steg

Portering sker på `*-pfile`-maskin med versionsagnostisk kod
(`.p.py` / `.p.xml`). Se `/skill:odoo-pfiles`.
