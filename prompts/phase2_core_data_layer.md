Phase 2: Core data layer and KPIs.

Read `prompts/dashboard_developer_prompt_v2.md` (Sections 2 to 4), `tests/reference_resolution.py`, `tests/expected_sample_107.json`, `tests/expected_summary_report.csv`, `docs/kpi_rules.md`, `docs/facility_routing.csv`, `docs/device_mapping.csv` and `tests/test_cases.md`.

Task:
1. Build `src/kpi/` with: latest valid submission per facility and period; overlap detection; accepted-status filter; the canonical KPIs exactly as in `kpi_rules.md`; device totals using `device_mapping.csv`; facility registry stub with alias matching (placeholder file, no invented facilities).
2. Join district to division from `data/district_division.csv` and `data/divisions.csv`. Prefer the district mapping over the submitted division and flag mismatches.
3. Implement the Direct / Indirect (family) / Total reach rules exactly as in `kpi_rules.md`, as tested library code that matches `reference_resolution.py`. Direct must NOT be a plain sum of `w_total`.
4. Write pytest tests for every case in `tests/test_cases.md` (52 cases). The reference numbers are in `tests/expected_kpis.json`; the code must reproduce them, and the 107-row results in `tests/expected_sample_107.json` (Direct 7,728; Indirect 38,640; Total 46,368). Exclude `regional_dir` from services; `assistive_ip` Direct = device recipients; apply the sanity ceiling (one cumulative value is 3.37e215).

First write a short plan and wait for my approval.
