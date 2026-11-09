# Test cases
Cases 1 to 20 use `data/synthetic_submissions.csv` (facility names start with "TEST"). Cases 21 to 38 use `sample_cases.csv` (43 real submissions, anonymised) and `reference_resolution.py`.
Note for cases 5, 6 and 18: the period is now `rp_end` only. Select rp_end = 2026-09-30; the expected numbers are unchanged.

Reference numbers for the main selection are in `expected_kpis.json`.

| # | Case (see `test_purpose` column) | Expected behaviour |
|---|---|---|
| 1 | One normal row per facility type (15 types) | Correct section routing and new/waiting source per `facility_routing.csv` |
| 2 | pcrdp, assistive_ip, regional_dir | No W fields: beneficiary KPIs show "Not applicable", not 0 |
| 3 | rcmhc | New and waiting come from c_new and c_waiting |
| 4 | inclusive | New and waiting come from n_new and n_waiting |
| 5 | Duplicate (same facility and period, later submission) | Latest wins (73 active, not 72); older row kept in audit view |
| 6 | Overlapping period (Deaf Reach, Aug to Oct) | Overlap diagnostic; new beneficiaries not double counted |
| 7 | _validation_status = not_approved | Excluded from accepted KPIs; shown in diagnostics |
| 8 | NOWPDP with both R and P5 devices | Use P5 only; flag "device double-count risk" |
| 9 | SIPMR with R devices | Counted once from R; Section U workshop counts not added |
| 10 | Missing GIS | No pin; district shading and facility list only |
| 11 | GIS outside Sindh | Flag invalid location; no pin |
| 12 | Division karachi with district sukkur | Flag mismatch; analytics use district mapping |
| 13 | c_active differs from w_total | Active headcount mismatch diagnostic; KPI uses w_total |
| 14 | c_active above c_cumulative | Impossible-value diagnostic |
| 15 | academy waiting = 0 | Shows 0 (applies, none), not "Not applicable" |
| 16 | ipmr, hostel, vtc, carts | Cumulative KPI shows "Not collected" |
| 17 | Cumulative figures across two periods | Never summed; latest snapshot only |
| 18 | Selection 2026-07-01 to 2026-09-30, accepted only | Equals `expected_kpis.json` exactly |
| 19 | Filters | Division change clears district and facility; every number comes from one filtered dataframe |
| 20 | Roles | Viewer cannot see contact_name, contact_info, signature, pictures or story files, even through exports |
| 21 | W = 0 but section c_active > 0 (sample cases 18, 21, 24) | Direct = c_active; flag W_zero; source "section:c_active" |
| 22 | W blank, section figure present | Direct = section figure; flag W_blank |
| 23 | W equals c_cumulative while c_active differs (607 vs 78; 422 vs 65) | Direct = c_active; flag W_copied_from_cumulative |
| 24 | W and c_active differ by more than 20% (7 sample cases) | Direct = W; flag review; both numbers shown |
| 25 | All-zero report (3 sample cases) | Direct = 0; flag all_zero_report; shown in Data Quality; not dropped |
| 26 | Reach block | Indirect = Direct x 5, Total = Direct x 6, both labelled "Estimated"; changing F in settings changes both; F shown in tooltip and exports |
| 27 | Reported indirect reach fields filled | Shown as a separate cumulative card; never added to Direct, Indirect or Total |
| 28 | Cumulative basis | Uses C only (c_cumulative, n_integrated, t_cum, u_cum, p_cum, legal and certificate fields); W ignored; dis_cer and legal-support facilities appear only here |
| 29 | Whole sample file | Equals `expected_sample_summary.json`: Direct 2205, Family 11025, Total 13230; fallback rows 5; review rows 7; all-zero rows 3 |
| 30 | Name contains "Deaf Reach" but type is gov_se (12 sample rows) | Flag "suggested type deaf_reach"; stored type unchanged until an override is approved |
| 31 | rp_start equals rp_end (8 sample rows) | No zero-length period; period comes from rp_end |
| 32 | Near-duplicate names (same district, type and rp_end, e.g. spelling variants) | Duplicate candidate flag; latest submission wins after review |
| 33 | Gender with a fallback row | When Direct came from the section figure, gender shows "Not reported" (W was not trusted) |
| 34 | Breakdown by facility type | Matches `expected_breakdown.csv` (level = service); all 18 services listed; rows add up to the grand total |
| 35 | Breakdown by division | Division from the district mapping; matches `expected_breakdown.csv`; Karachi and Mirpurkhas show "No reports", not 0 |
| 36 | Breakdown by district | All 30 districts listed; 15 have reports in the sample; clicking a district sets the global filter |
| 37 | "With suggested corrections" toggle | The 12 Deaf Reach reports move from gov_se to deaf_reach; totals unchanged; default stays "as filed" |
| 38 | New above active (Shikarpur 500 vs 152; Badin 90 vs 1) | Flagged for review; values not changed |
| 39 | Regional Director report | Excluded from services, totals and counts; appears only in the admin Offices view and as a green dashed office marker |
| 40 | assistive_ip report | Direct = recipients (208 in the sample), flag period_count_not_stock |
| 41 | 107-row export | Direct 7,728; Indirect 38,640; Total 46,368; matches `expected_sample_107.json` |
| 42 | Summary Reports tab | Matches `expected_summary_report.csv`; 27 of 30 districts and 6 of 6 divisions updated; pending list shows the 3 missing districts |
| 43 | Ownership class, shape and icon | Class from `ownership_by_type.csv` (green / blue / purple / grey); shape by category (circle, rounded square, hexagon, house, triangle, diamond); icon and text always shown; "submitted ownership differs" flag raised for the 37 gov_se rows filed as partner; class totals match `expected_sample_107.json` |
| 44 | Implausible value (cumulative 3.37e215) | Excluded from sums and flagged |
| 45 | Live loader | Missing required column raises a schema error; failure message never contains the token; restricted columns removed at load |
| 46 | Same name, district and month (12 groups, 32 reports) | All counted by default; each group flagged for review; no automatic removal |
| 47 | Unknown new columns in the export | Ignored with a warning in Data Quality; never break the load; listed so the dictionary can be updated |
| 48 | Summary Sheet | 106 rows; columns service type, category, ownership class, region, district, organisation name, period, Direct, Indirect, Total; subtotals and grand total reconcile (7,728); matches `expected_summary_sheet.csv` |
| 49 | Table downloads | Every table has Excel and JPG; Excel holds all filtered rows with a header (title, filters, period, basis, source, refreshed); JPG is a valid image; no restricted columns |
| 50 | Map download | JPG covers the complete Sindh extent whatever the zoom, pan or selection; shows filtered markers, legend, filters, period, source, refreshed time |
| 51 | Filters on every tab | Service type, ownership class, region and district filters exist on every tab including the map and give identical results across tabs |
| 52 | dis_cer ownership | Disability certificate facilities are government (green, diamond) |
