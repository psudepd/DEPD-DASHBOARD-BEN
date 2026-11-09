# START HERE: paste this into Antigravity (Planning mode) to begin development

You are a senior Python / Streamlit engineer, GIS analyst and public-sector data architect. Build the **DEPD Executive Analytics & GIS Dashboard** for the Government of Sindh, Department of Empowerment of Persons with Disabilities. Data comes live from KoboToolbox. Stack: Python 3.11, Streamlit, pandas, Plotly, GeoPandas + Matplotlib (static map), Folium (interactive map), httpx, openpyxl / XlsxWriter, Kaleido. It must be portable (Docker) so it can later move to another server.

## Step 0: read before doing anything (in this order)
1. `GEMINI.md` (project rules, non-negotiable)
2. `prompts/dashboard_developer_prompt_v2.md` (the full requirements)
3. `docs/00_specification.md` (specification v1.3), `docs/kpi_rules.md`, `docs/gis_map_styling.md`, `docs/dashboard_layout.md`, `docs/deployment.md`, `docs/open_decisions.md`
4. `tests/reference_resolution.py`, `tests/test_cases.md` (52 cases), `tests/expected_sample_107.json`, `tests/expected_summary_sheet.csv`
5. `src/ingest/kobo_live.py` and `src/export/exporters.py` (reference code that already has passing tests; extend, do not rewrite)

## What the dashboard must do (summary; details are in the files above)
- **Headline numbers:** Main total beneficiaries (Direct), Total indirect beneficiaries (Estimated = Direct x 5), Total reach (Estimated = Direct + indirect). Never use `w_total` alone: resolve Direct per report with the ladder in `docs/kpi_rules.md` (W first, then the section figure, then zero report). `assistive_ip` Direct = device recipients. `regional_dir` is office information only (not a service).
- **Pages:** Executive Overview, Geographic Coverage (map), Beneficiaries & Gender, Service Performance, Partner Programs, Facility Directory, Pivot & Reports, Summary Reports (with the Summary Sheet: service type, region, district, organisation name, beneficiaries), Data Quality.
- **Filters on every tab including the map:** service type, ownership class (Government / Partner / Other), region (division), district, facility, period, Active / Cumulative toggle.
- **Map:** colour = ownership class by service type (`data/ownership_by_type.csv`: green government, blue partner, purple other, grey unknown), shape = category (circle health, rounded square education, hexagon training, house hostel, triangle devices, diamond registration / legal), icon = service, plus text. Neutral grey division polygons. Pins only at valid coordinates, never guessed. Panels beside the map: headline cards, Direct by service type, Data received.
- **Downloads:** every table as Excel and JPG; map as a JPG of the complete Sindh extent every time (not the current zoom).
- **Live data:** read the saved Kobo export-settings XLSX URL from `KOBO_EXPORT_URL` with `KOBO_API_TOKEN` (see `.env.example`). Schema check on every load, 15-minute cache, stale-copy fallback, restricted columns removed at load. Unknown new columns are ignored with a warning.

## Hard rules
- Never invent data, fields, coordinates, boundaries or facility identities. Missing token, registry or boundary files: use a clearly marked placeholder and tell me what is missing.
- Never hard-code or log the token or URL. I will put the token in `.env` myself. Do not ask me to paste it into chat.
- Do not change a KPI rule silently. If a rule looks wrong or unclear, stop and ask me.
- Do not deduplicate by facility name (same names are different centres). Count all, flag groups.
- Blank = not applicable, 0 = none; show "No data", "Not applicable" and "No reports" as distinct states.
- Aggregate data only; no personal fields on any page except admin and manager views. Enforce roles on the server.
- Label synthetic data "SYNTHETIC TEST DATA" wherever it appears.

## How to work
- Work in phases `prompts/phase1_data_contract.md` to `phase6_security_qa.md`. Before each phase write a short plan and **wait for my approval**.
- Modules: `src/ingest`, `src/kpi`, `src/geo`, `src/ui`, `src/export`, `src/quality`, `app.py`.
- Write pytest tests for every KPI rule and diagnostic. A phase is done only when tests pass and you have reported: what was built, tests run, differences from the documents.
- Acceptance numbers on the 7 Nov export (107 rows, 106 service reports): Direct 7,728; Indirect 38,640; Total 46,368; government 76 reports / 4,803; partner 30 / 2,925; 27 of 30 districts and 6 of 6 divisions reported. Your code must reproduce these exactly.

## Your first task now (Phase 1 only)
1. Confirm you have read the files above. List anything unclear or contradictory between them (do not fix the documents yourself).
2. Read `data/depd_form_latest.xlsx` and compare it with `docs/field_dictionary.csv`; the live export has about 660 columns the dictionary does not list, so report every difference.
3. Propose the Phase 1 plan: project skeleton, schema loader, adapter (canonical names, select_multiple 0/1 columns, blank vs 0), extension of `kobo_live.py` (schema check, cache, stale marker, "Last refreshed"), and tests using `data/synthetic_submissions.csv` and `tests/expected_sample_107_rows.csv`.
4. Stop and wait for my approval before writing code.
