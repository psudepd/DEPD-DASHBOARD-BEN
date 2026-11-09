"""Tests for src/kpi/aggregate.py against tests/expected_sample_107_rows.csv.

The fixture already carries a numeric "direct" column, so aggregate_reach and
breakdown must use it as-is and never re-resolve those rows.
"""
import json
import os

import pandas as pd
import pytest

from src.kpi.aggregate import (
    aggregate_reach,
    apply_sanity_ceiling,
    breakdown,
    select_latest_per_facility,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "expected_sample_107_rows.csv")
EXPECTED = os.path.join(HERE, "expected_sample_107.json")
SUMMARY = os.path.join(HERE, "expected_sample_summary.json")

_FAMILY_FACTOR = 5


def _load_expected():
    with open(EXPECTED, encoding="utf-8") as fh:
        return json.load(fh)


def _load_df():
    return pd.read_csv(FIXTURE)


def test_total_matches_expected_107():
    df = _load_df()
    r = aggregate_reach(df)
    assert abs(r["direct"] - 7728.0) < 0.1, r
    assert abs(r["family"] - 38640.0) < 0.1, r
    assert abs(r["total"] - 46368.0) < 0.1, r


def test_breakdown_by_service():
    df = _load_df()
    b = breakdown(df, "service")
    expected = _load_expected()["by_facility_type_as_filed"]
    for ft, vals in expected.items():
        if ft in b.index:
            assert abs(b.loc[ft, "direct"] - vals["direct"]) < 0.1, (
                f"{ft}: expected {vals['direct']} got {b.loc[ft, 'direct']}"
            )


def test_breakdown_by_division():
    df = _load_df()
    b = breakdown(df, "division")
    expected = _load_expected()["by_division"]
    for div, vals in expected.items():
        assert abs(b.loc[div, "direct"] - vals["direct"]) < 0.1, (
            f"{div}: expected {vals['direct']} got {b.loc[div, 'direct']}"
        )
    assert "Karachi" in b.index and b.loc["Karachi", "reports"] > 0
    assert "Mirpurkhas" in b.index and b.loc["Mirpurkhas", "reports"] > 0


def test_regional_dir_excluded():
    df = _load_df()
    b = breakdown(df, "service")
    assert "regional_dir" not in b.index or b.loc["regional_dir", "direct"] == 0


def test_select_latest_per_facility_keeps_different_ids():
    df = pd.DataFrame(
        [
            {"facility_name": "X Clinic", "rp_end": "2026-11-01", "_id": "a",
             "_submission_time": "2026-11-01", "direct": 1.0},
            {"facility_name": "X Clinic", "rp_end": "2026-11-01", "_id": "b",
             "_submission_time": "2026-11-02", "direct": 2.0},
        ]
    )
    out = select_latest_per_facility(df)
    assert len(out) == 2, out


def test_apply_sanity_ceiling_flags():
    df = pd.DataFrame(
        [
            {"c_cumulative": 50.0},
            {"c_cumulative": 2_000_000.0},
        ]
    )
    out = apply_sanity_ceiling(df)
    assert out["implausible_value"].tolist() == [False, True]
