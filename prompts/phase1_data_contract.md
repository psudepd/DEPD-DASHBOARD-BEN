Phase 1: Data contract.

Read `GEMINI.md`, `docs/00_specification.md` (Sections 2, 5, 9), `docs/field_dictionary.csv` and `data/depd_form_latest.xlsx`.

Task:
1. Read the XLSForm survey, choices and settings sheets and build `src/ingest/schema.py` that loads them.
2. Compare the real schema with `docs/field_dictionary.csv`. Report every field that is missing, extra or has a different type. Do not fix the documents yourself; list the differences.
3. Write the adapter `src/ingest/kobo_adapter.py` that (a) reads a CSV or JSON export, (b) strips group prefixes such as `sec_w/`, (c) maps columns to canonical names, (d) normalises select_multiple (space-separated or 0/1 columns), (e) keeps raw values, (f) keeps blank distinct from 0.
4. Review and extend `src/ingest/kobo_live.py` (the live reader for the Kobo export-settings XLSX URL in `KOBO_EXPORT_URL`, token in `KOBO_API_TOKEN`). Keep its tests passing, add the schema check against `docs/field_dictionary.csv`, caching with a stale marker, and the "Last refreshed" status. It must not run without real configuration and must never log the token or URL credentials.
5. Test with `data/synthetic_submissions.csv` and `tests/expected_sample_107_rows.csv`; run `pytest`.

First write a short plan and wait for my approval. Do not start coding before that.
