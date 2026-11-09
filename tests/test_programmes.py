"""Tests for src/kpi/programmes.programme_kpis (Phase 5A)."""
import pandas as pd
import pytest

from src.kpi.programmes import programme_kpis

FIXTURE = "data/synthetic_submissions.csv"


def _load_df():
    return pd.read_csv(FIXTURE, dtype=object)


def test_nowpdp_fields_present():
    df = _load_df()
    out = programme_kpis(df, "nowpdp")
    p_cum = out[out["indicator"] == "p_cum"]
    assert len(p_cum) == 1
    assert p_cum.iloc[0]["unit"] == "people"
    assert p_cum.iloc[0]["rule"] == "CUM"
    p5 = out[out["indicator"] == "p5_wheelchair"]
    assert len(p5) == 1
    assert p5.iloc[0]["unit"] == "devices"
    assert p5.iloc[0]["rule"] == "FLOW"


def test_carts_v5_label_parents():
    df = _load_df()
    out = programme_kpis(df, "carts")
    v5 = out[out["indicator"] == "v5_cum"]
    assert len(v5) == 1
    assert "Parent" in v5.iloc[0]["label"]


def test_sipmr_people_vs_sessions():
    df = _load_df()
    out = programme_kpis(df, "sipmr")
    pts = out[out["indicator"] == "u_physio_pts"]
    ses = out[out["indicator"] == "u_physio_ses"]
    assert len(pts) == 1 and pts.iloc[0]["unit"] == "people"
    assert len(ses) == 1 and ses.iloc[0]["unit"] == "sessions"


def test_missing_field_is_no_data():
    df = pd.DataFrame(
        {
            "facility_type": ["deaf_reach", "deaf_reach"],
            "_submission_time": ["2026-07-01", "2026-08-01"],
            "t_psl": ["", ""],
            "t_teachers": ["", ""],
        }
    )
    out = programme_kpis(df, "deaf_reach")
    row = out[out["indicator"] == "t_psl"]
    assert len(row) == 1
    assert row.iloc[0]["value"] is None
    assert row.iloc[0]["null_state"] == "No data"


def test_zero_is_not_blank():
    df = pd.DataFrame(
        {
            "facility_type": ["deaf_reach", "deaf_reach"],
            "_submission_time": ["2026-07-01", "2026-08-01"],
            "t_teachers": [0, 0],
        }
    )
    out = programme_kpis(df, "deaf_reach")
    row = out[out["indicator"] == "t_teachers"]
    assert len(row) == 1
    assert row.iloc[0]["value"] == 0
    assert row.iloc[0]["null_state"] is None
