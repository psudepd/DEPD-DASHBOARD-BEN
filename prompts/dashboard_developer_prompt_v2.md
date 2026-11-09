# DEPD Executive Analytics & GIS Dashboard: Developer Prompt v2 (final, v1.3)

Act as a senior Python / Streamlit engineer, GIS analyst and public-sector data architect. Build the DEPD Executive Analytics & GIS Dashboard described in `docs/00_specification.md` (v1.3). Work phase by phase using `prompts/phase*.md`. Write a plan first and wait for approval before coding each phase.

## 1. Inputs (read first)
- `GEMINI.md` (project rules) and `docs/00_specification.md`
- `docs/kpi_rules.md` (authoritative formulas) and `tests/reference_resolution.py` (reference code for the beneficiary rules)
- `docs/field_dictionary.csv`, `docs/facility_routing.csv`, `docs/device_mapping.csv`, `docs/open_decisions.md`
- `data/depd_form_latest.xlsx` (the real Kobo schema; it may be newer than the dictionary, so compare and report differences)
- `tests/expected_sample_107.json`, `tests/expected_sample_107_rows.csv`, `tests/expected_summary_report.csv` (the current 107-row export, with expected results). `tests/sample_cases.csv` and `tests/expected_sample_summary.json` are the older 43-row set (kept as extra tests)
- `docs/gis_map_styling.md`, `docs/gis_icon_map.csv`, `docs/deployment.md`, `src/ingest/kobo_live.py` (reference loader) and `.env.example`

## 1A. Live data source (read this before writing the loader)
- Source: the saved Kobo export setting, an XLSX of all submissions: `https://kf.kobotoolbox.org/api/v2/assets/agqkhZsLaqUQyLK8UwKrsx/export-settings/esqPMKgPTD8ZYEERvWqhw9K/data.xlsx`. Read it from `KOBO_EXPORT_URL`; send `Authorization: Token <KOBO_API_TOKEN>`. Never hard-code or log either.
- The export has XML column names, no group prefixes, select_multiple as `field/choice` 0/1 columns, and Kobo fields (`_id`, `_uuid`, `_submission_time`, `_validation_status`, `_GIS_latitude`, `_GIS_longitude`). Read cells as text first so blank stays distinct from 0.
- Check required columns on every load. If missing, stop with a schema error (the export settings were probably changed).
- Cache 15 minutes, retries with back-off, timeout 120 s, visible "Last refreshed" and a "stale" marker if Kobo is unreachable. Admin-only manual refresh.
- Strip contact, signature, picture and story columns at load; keep them for admin and manager views only.
- Extend `src/ingest/kobo_live.py`; do not rewrite it. It is unit-tested with a mocked server. The first live call must be verified with a real token.
- Target: portable Docker deployment (`docs/deployment.md`) so the app can later move to another server.

## 2. What the real data taught us (these are requirements)
In the first 43 real submissions (the 107-row export confirms the same pattern: 93 use W, 8 fall back to the section figure, 4 are zero reports, 8 mismatches) many users did not fill Section W correctly. They typed 0 and put the real numbers in their own section, or copied the cumulative total into W.
- 3 reports have W = 0 but their section holds real active figures (for example c_active = 113, 95).
- 2 reports copied the cumulative figure into W (W = 607 while c_active = 78; W = 422 while c_active = 65).
- 7 reports have W and the section figure differing by more than 20%.
- 3 reports are all zero. One of them also gives out devices, so the zero is probably missing data.
- Regional Director reports hold office information only. It is not a service; exclude it (section 4E).
- "DEPD Digital Classes Deaf Reach" reports are filed as `gov_se` instead of `deaf_reach` (12 of 43; 20 of 107).
- Facility names are free text: spelling variants of the same centre appear (for example "RCMHC (DEPD) JACOBABAD" and "RCMHC (DEPD JACOBABAD").
- 8 reports have `rp_start` equal to `rp_end`. The form now labels `rp_start` "Since Date of Center/Institution Inception", so it is no longer a period start.
A dashboard that simply sums `w_total` would be wrong. The rules below are therefore mandatory.

## 3. Direct, family (indirect) and total beneficiaries
Show one "Reach summary" block with three numbers, calculated for a **basis** chosen by a toggle: **Active** (default, at reporting end) or **Cumulative** (since establishment).

| Number | Formula | Label |
|---|---|---|
| Direct beneficiaries | resolved unique persons (ladder below) | "Direct (facility-reported)" |
| Indirect (family) beneficiaries | Direct x F, with F = 5 | "Estimated, Direct x 5" |
| Total reach | Direct + Indirect = Direct x (1 + F) | "Estimated total reach" |

- F is a setting (admin only), default 5. Show the factor on the card tooltip and in every export.
- The family estimate is a model, not a count. Label it "Estimated" everywhere. Never present it as reported data.
- **Reported indirect reach** is a different thing: the numbers facilities enter themselves (`Total_indirect_reach_since_inception`, `Beneficiary_students_inception_In_Direct`, `Total_Indirect_Reach_ablishment_Indirect`). Show it as a separate card, cumulative only. Never add it to Direct, to the family estimate or to Total reach.
- C-ARTS V5 parent trainees and any device, session, visit, case or certificate counts are never part of Direct.

### 3.1 Resolving Direct (Active basis), per submission
Inputs: `W` = `w_total`; `S` = the section-level active figure for the facility type (table below); `C` = the cumulative figure.

1. facility type is `pcrdp` or `regional_dir` -> **Not applicable** (not 0). `assistive_ip` has no W: Direct = people who received devices in the period (R male + female + transgender + other), source `R_recipients`, flag `period_count_not_stock` (decision 23).
2. If `W` > 0 and `W` is not a copy of `C` (W = C while S is present and S != C) -> use **W**.
   - If S > 0 and |W - S| / max(W, S) > 20% -> keep W but flag **review** (show both numbers).
3. Else if S > 0 -> use **S** and flag why: `W_blank`, `W_zero` or `W_copied_from_cumulative`.
4. Else if W = 0 or S = 0 -> **0**, flag `all_zero_report` (low confidence; never silently drop it).
5. Else -> **No data**.

| facility_type | S (section active) | Cumulative C |
|---|---|---|
| rcmhc, rcph, gov_se, gia, pcrdp | c_active | c_cumulative |
| inclusive | n_enrolled | n_integrated |
| carts | largest of v1_active..v4_active (lower bound, low confidence; V5 excluded) | none |
| nowpdp | largest of p2_active, p3_active (lower bound, low confidence) | p_cum |
| deaf_reach | none | t_cum |
| sipmr | none | u_cum |
| dis_cer, sindh_persons_with_disabilitie | none | Cumulative_Disabilit_sued_Since_Inception |
| legal_support__beneficiaries | none | Total_Direct_Benefic_since_establishment |
| hostel, vtc, academy, ipmr | none | none ("Not collected") |

On the **Cumulative basis** use C only (first non-blank in the order above). W is never used there.

### 3.2 Aggregation
- Latest valid submission per facility and period (key: facility_id + `rp_end`). Take Direct per facility, then sum across facilities. Never sum snapshots across time.
- Label every total "sum of facility-reported unique headcounts". Cross-facility deduplication is not possible.
- Under each card show the source mix, for example: "34 facilities from Section W, 5 from section data, 3 zero reports, 7 need review". Clicking opens the facility list with W, S, the resolved value, the source and the flags.
- Reproduce `tests/expected_sample_summary.json` exactly (Direct 2205, Family 11025, Total 13230 on the 43 sample rows before de-duplication) and `tests/expected_kpis.json` for the synthetic set.

## 4. Other rules from the real data
- **Reporting period:** use `rp_end` only (year, quarter, month). Do not use `rp_start` for periods or overlaps; treat it as the facility inception date. A second report from the same facility in the same month or quarter is a possible duplicate: latest wins, flag it.
- **Facility identity:** governed registry with aliases and fuzzy matching on normalised names (case, punctuation, "&" vs "and"). Do not rely on names alone.
- **Misclassified type:** if the name contains "deaf reach" and the type is `gov_se`, show a "suggested type: deaf_reach" flag. Never change the stored value silently; apply it only through a reviewed override table.
- **Contact fields:** `contact_name`, `contact_info`, `officer_designation` sometimes hold phone numbers or "0". Admin and manager roles only; flag, never display to viewers.
- **Zero vs blank:** blank = not applicable; 0 = applies, none. Section W typed as 0 while the section has data is handled by 3.1.
- **Primary recipient question** (`Who_is_the_primary_r_d_materials_services`, for nowpdp, gia, sipmr, assistive_ip): "Outreach" recipients are people outside the facility's own enrolment; "Internal" recipients are already in its active count. Report them separately and never add Internal to Direct.

## 4A. Breakdown views (facility type, region, district)
Provide three breakdown tables. Each reconciles to the grand total of the Reach summary under the same filters, and each follows the Active / Cumulative toggle.
- **By facility type (service):** group by `facility_type` as filed. Offer a toggle "with suggested corrections" that applies only reviewed overrides (for example the 12 "Deaf Reach" reports filed as `gov_se`). Default is "as filed" with a banner showing how many corrections are suggested. List all 18 service types (Regional Director is office information only, see 4E); types with no reports show "No reports yet".
- **By region (division):** derive the division from the district using `data/district_division.csv`. Never use the submitted `division` field for totals (flag mismatches). Always list all 6 divisions; a division with no reports shows "No reports", not 0.
- **By district:** always list all 30 districts with their division. Clicking a district sets the global filter. Districts with no reports are greyed "No report".
- **Columns in every table:** reports, distinct facilities, Direct, Indirect (family, Estimated), Total reach (Estimated), new, waiting, cumulative, male / female / other (only from reports where W was usable), and a source-mix flag (W / section / zero report / review).
- **Cross views:** service x division heatmap of Direct; division -> district -> facility drill-down.
- Reproduce `tests/expected_breakdown.csv` and `tests/expected_sample_107.json` (the 43-row set below is the older sample; the 107-row set is the current one). Older 43 sample reports: 4 of 6 divisions and 15 of 30 districts have reports; Hyderabad 998, Sukkur 739, Larkana 414, Shaheed Benazirabad 54; Karachi and Mirpurkhas none).
- Flag "new above active" (for example new 500 with active 152) for review.

## 4B. GIS map: colour, shape and icon (see docs/gis_map_styling.md, docs/gis_icon_map.csv, data/ownership_by_type.csv)
- **Colour = ownership class, fixed by service type** (not by the submitted `ownership` field). Government green #2E7D32: RCMHC, RCPH, gov_se, C-ARTS, VTC, SPDPA, disability certificate (dis_cer), inclusive, Regional Director. Partner organisation blue #1F5FBF: assistive_ip, GIA, Deaf Reach. Other purple #7B3FA0: all remaining types (SIPMR, IPMR, hostel, academy, NOWPDP, PCRDP, legal support; proposed). Unknown grey #6B7280.
- **Shape = service category:** health / rehabilitation circle; education / school rounded square; training / vocational hexagon; hostel house shape; assistive devices triangle; registration / legal diamond; office dashed square.
- **Icon = service:** medical cross (health), school building or book (education / school), tools, graduation cap or briefcase (training), bed (hostel), wheelchair (devices), identity card or scales (registration / legal), office building (Regional Director).
- Always show shape + icon + colour + text label together; the legend lists all. Division polygons use neutral grey tints only.
- The submitted `ownership` field is a check only: when it differs from the class (37 of 58 gov_se say partner; 20 of 25 Deaf Reach say other), keep the class colour and flag "submitted ownership differs". A reviewed facility-level override wins when supplied. Never recolour silently.
- Coordinates: registry first; submission GIS only if inside Sindh and inside the submitted district; otherwise no pin.

## 4C. Panels beside the map (and on the Executive page)
1. Main total beneficiaries (Direct), Total indirect beneficiaries (Estimated, x5), Total reach (Estimated).
2. Direct beneficiaries for each service type (all 19, "No reports" where empty) with reports, male / female / other (W only), new, waiting.
3. Data received: reports, facilities, districts reporting x of 30, last submission time, source mix, latest 10 reports (no contact or personal fields).
4. Click a marker or a service card to filter everything else.

## 4D. New fields and data traps in the 107-row export
- New columns: `Provincial`, `Office_Address_Details` (administrative; 7 filled), and four reported-indirect categories for inclusive education (parents/family, peer students, community, school staff). Store them as reported indirect reach, shown separately, never added to Direct or to the x5 estimate.
- `assistive_ip` has no W. Its Direct = people who received devices in the period (R male + female + transgender + other), flagged "period count, not stock", and not mixed into stock totals without a label.
- Deaf Reach (Section T) is now fully filled: show cumulative students, placed in jobs, awaiting job, transport, km, teachers, PSL interpreters.
- Plausibility guard: one RCMHC row has cumulative 3.37e215. Reject any integer above a sanity ceiling (default 1,000,000 per facility, admin setting), exclude it from sums, and flag "implausible value". Also flag "new above active".
- Cumulative sums must use the latest submission per facility only.
- **Same name is not a duplicate (important).** In the export, 12 groups (32 reports) share the same centre name, district and month, for example 6 "FESF/ Deaf Reach Satellite School" reports in Khairpur with different figures. These are almost certainly different satellite schools, because the form has no centre name or code field. Do NOT deduplicate by name. Default: count every submission ("as submitted"). Flag each group "same name, district and period: possible duplicate or several centres" for review, and let an admin mark a reviewed duplicate to exclude it. If all 32 reports were treated as duplicates (latest wins), Direct would be 7,112 instead of 7,728; show this only as a range in Data Quality. A true duplicate needs a facility ID or a centre code added to the form (decision 24).
- **SPDPA row:** one `sindh_persons_with_disabilitie` report (Ida Rieu Welfare Association, ownership "other") fills W = 1,054 and only 1 registration in G1. It looks like an NGO filed under the wrong type. Keep the value, flag "type may be wrong" (decision 25).

## 4E. Regional Director is office information, not a service
- `regional_dir` is a Regional Director office that manages several services. It holds office details only (office, address, contact role). It has no beneficiaries and no service figures.
- Exclude it from: all service lists and cards, Direct / Indirect / Total, breakdown tables, service icons and the "all types" list (list 18 services), the service colour legend and service report counts.
- Keep it in an admin "Offices" view: office name, division, district, address, last update. It may appear on the map as a neutral office marker (office-building icon, grey, label "Office"), never counted as a service. The map's service legend and totals ignore it.
- Do not flag it as "all-zero report" or "no data".

## 4F. Tab: Summary Reports (who has updated data)
One tab answering "which region, district and service types have updated data, and how many beneficiaries".
1. **Coverage strip:** divisions updated x of 6, districts updated x of 30, service types updated x of 18, facilities reporting, reports received, last submission (Asia/Karachi), for the selected period.
2. **Division table:** all 6 divisions with status (Updated / No report), districts updated, services updated, reports, Direct, Indirect (Estimated), Total reach, last update.
3. **District table:** all 30 districts with division, status, service types that reported (as chips with icons), reports, Direct, Indirect, Total, last update. "No report" rows are shown in grey and listed, never hidden.
4. **Service-type table:** all 18 services with status, divisions and districts covered, reports, Direct, Indirect, Total, new, waiting.
5. **Matrix:** district (rows) x service type (columns), cell = Direct beneficiaries, "-" = no report, with a toggle to show report counts.
6. **Pending list:** districts and services with no report in the period, exportable (CSV) for follow-up.
7. Every table reconciles to the grand total and follows the global filters, the period and the Active / Cumulative toggle. Status is based on `rp_end` falling in the selected period, not on submission time.
8. **Summary Sheet (register) on the same tab:** one row per service report with Service type, Service category, Ownership class, Region (division), District, Organisation / institute name (`facility_name`; for assistive_ip use `r_org`), Reporting period, Direct, Indirect (Estimated), Total reach (Estimated), Source flag. Sorted by service type, region, district; subtotal per service type; grand total reconciles to Direct. Institution names only, no contact or personal fields.
Reproduce `tests/expected_summary_report.csv` and `tests/expected_summary_sheet.csv` (107-row sample: regional_dir excluded, 106 service reports; government 76 reports / 4,803 Direct; partner 30 / 2,925).

## 4G. Filters and downloads on every tab
- **Filter bar on every tab, including the map:** service type (multi-select), ownership class (Government / Partner organisation / Other), region (division), district, facility, period, Active / Cumulative toggle. One filtered dataframe feeds every table, chart and the map. Active-filter chips and Reset All.
- **Every table has Download Excel and Download JPG.** Excel holds all rows on screen (title, filters, period, basis, source, refreshed time in the header rows). JPG shows the first 60 rows and says so. Use `src/export/exporters.py` (tested in `tests/test_exporters.py`).
- **Map download = JPG of the complete Sindh extent every time**, independent of zoom, pan or selection: use the total bounds of the approved boundary file plus a margin. Filtered markers, legend (colour, shape, icon), title, filters, period, source and refreshed time are drawn on it. Render on the server with GeoPandas + Matplotlib (the browser view is not used). If boundaries are missing, show a clear message; never draw guessed boundaries.
- Charts download as JPG / PNG (2x or 3x, Kaleido). Exports respect the viewer role and exclude restricted fields.

## 5. Build order
Phase 1 data contract -> 2 core data layer (implement `reference_resolution.py` logic as tested library code) -> 3 executive dashboard -> 4 GIS -> 5 programme dashboards -> 6 security and QA. After each phase report what was built, tests run, and any difference from the documents.

## 6. Never
Invent data, fields, coordinates or boundaries. Sum cumulative figures over time. Mix units. Show the family estimate without the word "Estimated". Add reported indirect reach to Direct. Put secrets in code or logs. Rely on hidden widgets for security.

## 7. Questions to ask me before Phase 2 (defaults in brackets)
1. Is Total reach = Direct + Direct x 5, or should it be Direct x 5 only? [Direct + Direct x 5]
2. Should a facility's own reported indirect reach replace the x5 estimate for that facility? [No, show both separately]
3. Is W the right source when it disagrees with the section figure by more than 20%? [Keep W, flag for review]
4. Should dis_cer, SPDPA and legal-support facilities see Section W at all? [Yes for now; they report on the Cumulative basis]
5. Confirm that Assistive Devices recipients count as Direct (decision 23). [Yes, flagged as a period count]
6. Confirm the classes for the types shown purple (SIPMR, IPMR, hostel, academy, NOWPDP, PCRDP, legal support) and whether a facility-level ownership override table will be supplied. [Purple = other; no override table, the service-type rule applies]
7. Should the service breakdown default to "as filed" or "with suggested corrections"? [As filed, with a banner and a toggle]
