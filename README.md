# DEPD Executive Analytics & GIS Dashboard: project folder

Government of Sindh, Department of Empowerment of Persons with Disabilities (DEPD).

## What is in this folder
| Path | Purpose |
|---|---|
| `GEMINI.md`, `AGENTS.md`, `.agent/rules/` | Project rules for the AI agent (same text in each) |
| `docs/00_specification.md` | Full specification v1.3 (also PDF and Word for people) |
| `docs/kpi_rules.md` | Short authoritative KPI formulas |
| `docs/field_dictionary.csv` | All 218 form fields with unit and aggregation rule |
| `docs/facility_routing.csv` | 19 facility types (18 services; regional_dir is office information only) |
| `docs/device_mapping.csv` | Section R and NOWPDP P5 device mapping |
| `docs/open_decisions.md` | Open decisions and their defaults |
| `docs/form_master_prompt.md` | Prompt used to build the Kobo form |
| `data/depd_form_latest.xlsx` | The latest Kobo XLSForm shared (latest shared) |
| `data/choices.csv`, `district_division.csv`, `divisions.csv` | Choice lists |
| `data/synthetic_submissions.csv` | SYNTHETIC test data, 24 rows, includes edge cases |
| `tests/test_cases.md`, `expected_kpis.json` | 52 test cases and reference numbers |
| `tests/reference_resolution.py` | Reference code for Direct / family / total rules |
| `tests/expected_breakdown.csv`, `sample_cases_geography.csv` | Expected numbers by facility type, division and district (sample) |
| `tests/expected_sample_107.json`, `expected_sample_107_rows.csv`, `expected_summary_report.csv` | Current 107-row export: expected results (Direct 7,728; Indirect 38,640; Total 46,368) |
| `tests/sample_cases.csv`, `expected_sample_summary.json` | Older 43-row sample (extra tests) |
| `docs/dashboard_layout.md`, `docs/final_checklist.md` | Page wireframes; stack, results and open items |
| `docs/gis_map_styling.md`, `docs/gis_icon_map.csv`, `data/ownership_by_type.csv` | Ownership class colours, shapes, icons, map panels |
| `docs/deployment.md`, `Dockerfile`, `docker-compose.yml`, `.env.example` | Live Kobo source and portable deployment |
| `src/ingest/kobo_live.py`, `tests/test_kobo_live.py` | Reference live loader with tests |
| `src/export/exporters.py`, `tests/test_exporters.py` | Reference Excel / JPG table export and full-Sindh map extent, with tests |
| `tests/expected_summary_sheet.csv` | Expected Summary Sheet (106 rows) |
| `prompts/dashboard_developer_prompt_v2.md` | The improved master prompt (read this first) |
| `prompts/` | One prompt per build phase |
| `.streamlit/` | Theme and a secrets template (placeholders only) |

## Start
1. Open this folder in Antigravity.
2. Paste `prompts/00_START_HERE_antigravity_kickoff.md` into Antigravity (it reads the documents and plans Phase 1). Then follow `prompts/00_how_to_use.md` phase by phase.
3. Continue phase by phase. Approve each plan before the agent codes.

## Not included (needs input from DEPD)
Kobo API token (put it in `.env` yourself), an approved facility registry with coordinates, and district boundary GeoJSON (place in `data/boundaries/`). The agent must use placeholders and must not invent them.
