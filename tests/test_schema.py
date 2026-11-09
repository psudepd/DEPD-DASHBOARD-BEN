"""Tests for the XLSForm schema loader (src/ingest/schema.py)."""
import os

import pytest

from src.ingest.schema import (
    DEFAULT_DICTIONARY_PATH,
    DEFAULT_XLSX_PATH,
    load_dictionary,
    load_xlsx_form,
    validate_export_columns,
)


def test_settings_load_id_and_version():
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)
    assert schema.id_string == "depd_beneficiary_data_v6"
    assert schema.version == "7.0"


def test_survey_has_known_fields():
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)
    names = set(schema.field_names)
    for f in ["facility_type", "facility_name", "district", "rp_end", "w_total"]:
        assert f in names, f"missing survey field {f}"


def test_select_multiples_detected():
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)
    assert "w_age_groups" in schema.select_multiples
    assert "carts_services" in schema.select_multiples


def test_dictionary_loads():
    d = load_dictionary(DEFAULT_DICTIONARY_PATH)
    assert len(d) >= 200
    assert "facility_type" in d
    assert "w_total" in d


def test_validate_no_missing_required_on_real_export_shape():
    """The live export has all dictionary fields; required columns present."""
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)
    dictionary = load_dictionary(DEFAULT_DICTIONARY_PATH)
    # Use all survey field names plus Kobo system columns present in exports.
    cols = list(schema.field_names) + [
        "_id", "_uuid", "_submission_time", "_validation_status",
        "_GIS_latitude", "_GIS_longitude",
    ]
    res = validate_export_columns(
        cols, schema, dictionary,
        required=["facility_type", "facility_name", "district", "rp_end", "_submission_time"],
    )
    assert res["missing_required"] == []
    assert "_submission_time" not in res["unknown"]  # known system column


def test_validate_missing_required_flags_error():
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)
    dictionary = load_dictionary(DEFAULT_DICTIONARY_PATH)
    res = validate_export_columns(
        ["facility_type", "facility_name"], schema, dictionary,
        required=["facility_type", "facility_name", "district", "rp_end", "_submission_time"],
    )
    assert "district" in res["missing_required"]
    assert "rp_end" in res["missing_required"]
    assert "_submission_time" in res["missing_required"]


def test_default_paths_exist():
    assert os.path.exists(DEFAULT_XLSX_PATH), DEFAULT_XLSX_PATH
    assert os.path.exists(DEFAULT_DICTIONARY_PATH), DEFAULT_DICTIONARY_PATH
