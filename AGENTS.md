# DEPD Executive Analytics & GIS Dashboard: project rules

You are building a Streamlit dashboard for the Government of Sindh, Department of Empowerment of Persons with Disabilities (DEPD). Data: aggregate facility reports from a KoboToolbox form (XLSForm v7.0).

## Read first (in this order)
1. `docs/00_specification.md` (full specification v1.3)
2. `docs/kpi_rules.md` (authoritative KPI formulas) and `tests/reference_resolution.py`
3. `docs/field_dictionary.csv` (every form field, unit and aggregation rule)
4. `docs/facility_routing.csv`, `docs/device_mapping.csv`, `docs/open_decisions.md`
5. `data/depd_form_latest.xlsx` (the real schema), `docs/gis_map_styling.md`, `docs/deployment.md` and `prompts/dashboard_developer_prompt_v2.md`

## Non-negotiable rules
- Never invent data, fields, coordinates, boundaries or beneficiary identities.
- Synthetic data (`data/synthetic_submissions.csv`) must be labelled "SYNTHETIC TEST DATA" wherever it appears in the UI.
- Follow `docs/kpi_rules.md` exactly. If a rule seems wrong or unclear, stop and ask. Do not silently change it.
- Never sum cumulative or snapshot figures across periods. Never mix units.
- Do NOT trust `w_total` alone. Resolve Direct beneficiaries with the ladder in `docs/kpi_rules.md` (W first, then the section figure when W is blank, zero or copied from cumulative). The family estimate (Direct x 5) is always labelled "Estimated", and reported indirect reach is never added to Direct.
- Period = `rp_end`. `rp_start` is the facility inception date.
- Blank means not applicable; 0 means none. Show "No data", "Not applicable", "Not collected", "Not yet verified" and "Missing location" as distinct states.
- Aggregate data only. No names, CNICs, phone numbers or beneficiary-level markers. Contact, signature, picture and story fields are restricted to admin and manager roles.
- Never put map pins at guessed locations or district centroids.
- Enforce role permissions on the server, not by hiding widgets.
- No secrets in code, logs or the UI. Use Streamlit secrets or environment variables.

## Working style
- Work phase by phase using `prompts/`. Before coding each phase, write a short plan and wait for approval.
- Keep modules small: `src/ingest`, `src/kpi`, `src/geo`, `src/ui`, `src/quality`.
- Write unit tests for every KPI rule and every diagnostic. Run them before saying a phase is done.
- When a phase is finished, report: what was built, tests run and results, and any difference from the documents.

## Live data source and deployment (v1.3)
- Data is read from the saved Kobo export-settings XLSX URL in `KOBO_EXPORT_URL` with `KOBO_API_TOKEN` (see `.env.example`, `docs/deployment.md`, `src/ingest/kobo_live.py`). Never hard-code either; never log the token.
- Check the schema on every load; stop with a clear error if the export settings changed. Keep the last good copy marked "stale". Strip restricted columns at load.
- Regional Director (`regional_dir`) is office information only, not a service: exclude it from services, totals and counts (18 services).
- Map markers coloured by ownership: government green, partner organisation blue, other purple, unknown grey; service icons per `docs/gis_icon_map.csv`; neutral division polygons. See `docs/gis_map_styling.md`.
- Build a Summary Reports tab (who updated data: division, district, service type; beneficiaries; pending list).
- The app must be portable: Docker, configuration only from environment variables or secrets, so it can move to another server.
