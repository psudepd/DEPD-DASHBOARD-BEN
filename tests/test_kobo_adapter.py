"""Tests for the Kobo export adapter (src/ingest/kobo_adapter.py)."""
import pandas as pd

from src.ingest.kobo_adapter import adapt, split_restricted, strip_group_prefix, required_present


def test_strip_group_prefix():
    assert strip_group_prefix("sec_w/w_total") == "w_total"
    assert strip_group_prefix("group_dp8mz64/Cumulative_Disabilit_sued_Since_Inception") == (
        "Cumulative_Disabilit_sued_Since_Inception"
    )
    assert strip_group_prefix("w_total") == "w_total"


def test_blank_stays_distinct_from_zero():
    df = pd.DataFrame({
        "facility_type": ["rcmhc"],
        "facility_name": ["T"],
        "district": ["D"],
        "rp_end": ["2026-11-01"],
        "_submission_time": ["2026-11-02"],
        "w_total": [""],
        "c_active": ["0"],
    })
    out = adapt(df)
    assert out.loc[0, "w_total"] is None or out.loc[0, "w_total"] == ""
    assert out.loc[0, "c_active"] == "0"


def test_restricted_columns_stripped():
    df = pd.DataFrame({
        "facility_type": ["rcmhc"],
        "facility_name": ["T"],
        "district": ["D"],
        "rp_end": ["2026-11-01"],
        "_submission_time": ["2026-11-02"],
        "contact_name": ["John"],
        "s_pic_1": ["pic.jpg"],
    })
    general, restricted = split_restricted(df)
    assert "contact_name" not in general.columns
    assert "s_pic_1" not in general.columns
    assert "contact_name" in restricted.columns


def test_required_present():
    df = pd.DataFrame({
        "facility_type": ["rcmhc"],
        "facility_name": ["T"],
        "district": ["D"],
        "rp_end": ["2026-11-01"],
        "_submission_time": ["2026-11-02"],
    })
    assert required_present(df) == []
    assert required_present(df[["facility_type"]]) == [
        "facility_name", "district", "rp_end", "_submission_time",
    ]


def test_adapt_returns_dataframe():
    df = pd.DataFrame({
        "facility_type": ["rcmhc"],
        "facility_name": ["T"],
        "district": ["D"],
        "rp_end": ["2026-11-01"],
        "_submission_time": ["2026-11-02"],
        "w_total": ["50"],
    })
    out = adapt(df)
    assert isinstance(out, pd.DataFrame)
    assert len(out) == 1
