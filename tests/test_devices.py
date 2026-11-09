"""Tests for src/kpi.devices.device_totals against data/synthetic_submissions.csv.

Rows are located by _id (1001..1024), not by positional index.
"""
import os

import pandas as pd
import pytest

from src.kpi.devices import device_totals

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, os.pardir, "data", "synthetic_submissions.csv")


def _load_df():
    return pd.read_csv(FIXTURE)


def _row(df, _id):
    sub = df[df["_id"] == _id]
    assert len(sub) == 1, f"expected exactly one row with _id={_id}, got {len(sub)}"
    return sub


def test_row_1016_nowpdp_r_and_p5_use_p5_only_flag_risk():
    """nowpdp with both R and P5 filled: use P5 only, flag double-count risk."""
    df = _load_df()
    out = device_totals(_row(df, 1016)).iloc[0]
    assert out["source"] == "P5"
    assert out["double_count_risk"] == True
    assert out["wheelchair"] == 30.0, out["wheelchair"]
    assert out["crutches_walkers"] == 20.0, out["crutches_walkers"]
    assert out["tricycle"] == 8.0, out["tricycle"]
    assert out["prosthesis"] is None or pd.isna(out["prosthesis"])
    assert out["orthosis"] is None or pd.isna(out["orthosis"])
    assert out["hearing"] == 5.0, out["hearing"]
    assert out["vision"] == 9.0, out["vision"]
    assert out["other"] == 2.0, out["other"]


def test_row_1006_sipmr_r_devices():
    """sipmr with R devices: source R, crutches_walkers = r_crutches + r_walker."""
    df = _load_df()
    out = device_totals(_row(df, 1006)).iloc[0]
    assert out["source"] == "R"
    assert out["wheelchair"] == 40.0, out["wheelchair"]
    assert out["crutches_walkers"] == 35.0, out["crutches_walkers"]
    assert out["prosthesis"] == 6.0, out["prosthesis"]
    assert out["orthosis"] == 12.0, out["orthosis"]
    assert out["hearing"] == 0.0, out["hearing"]
    assert out["vision"] == 0.0, out["vision"]
    assert out["other"] == 0.0, out["other"]
    assert out["tricycle"] is None or pd.isna(out["tricycle"])


def test_row_1009_nowpdp_p5_only_no_risk():
    """nowpdp with P5 only (r_given=no): source P5, no double-count risk."""
    df = _load_df()
    out = device_totals(_row(df, 1009)).iloc[0]
    assert out["source"] == "P5"
    assert out["double_count_risk"] == False
    assert out["wheelchair"] == 30.0, out["wheelchair"]
    assert out["crutches_walkers"] == 20.0, out["crutches_walkers"]
