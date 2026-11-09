"""Tests for src/kpi.geography division mapping helpers."""
import os

import pandas as pd

from src.kpi.geography import (
    DIVISION_MAP,
    add_division_columns,
    district_to_division,
    division_of_row,
    normalise,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, os.pardir, "data", "synthetic_submissions.csv")


def test_normalise():
    assert normalise("Karachi Central") == "karachi_central"
    assert normalise("Sukkur") == "sukkur"
    assert normalise(" Shaheed-Benazirabad ") == "shaheed_benazirabad"
    assert normalise(None) == ""


def test_district_to_division_known():
    assert district_to_division("sukkur") == "sukkur"
    assert district_to_division("karachi_central") == "karachi"
    assert district_to_division("hyderabad") == "hyderabad"


def test_district_to_division_unknown_is_none():
    assert district_to_division("not_a_district") is None


def test_division_map_loaded_from_csv():
    assert DIVISION_MAP["sukkur"] == "sukkur"
    assert DIVISION_MAP["karachi_central"] == "karachi"


def test_row_1020_division_mismatch_uses_district_mapping():
    """division=karachi but district=sukkur -> mapped sukkur, mismatch True."""
    df = pd.read_csv(FIXTURE)
    row = df[df["_id"] == 1020].iloc[0]
    assert division_of_row(row) == "sukkur"
    enriched = add_division_columns(df[[_ for _ in df.columns]])
    match = enriched[enriched["_id"] == 1020].iloc[0]
    assert match["division_mapped"] == "sukkur"
    assert match["division_mismatch"] == True


def test_row_1001_division_matches_district():
    """division=karachi, district=karachi_central -> mapped karachi, no mismatch."""
    df = pd.read_csv(FIXTURE)
    row = df[df["_id"] == 1001].iloc[0]
    assert division_of_row(row) == "karachi"
    enriched = add_division_columns(df[[_ for _ in df.columns]])
    match = enriched[enriched["_id"] == 1001].iloc[0]
    assert match["division_mapped"] == "karachi"
    assert match["division_mismatch"] == False
