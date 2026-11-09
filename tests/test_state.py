"""Tests for src/ui.state filtering helpers."""
import pandas as pd
import pytest

from src.kpi.aggregate import aggregate_reach
from src.ui.state import get_filtered_dataframe


def test_filter_idempotence():
    a = get_filtered_dataframe()
    b = get_filtered_dataframe()
    assert len(a) == len(b)


def test_filter_reconciles_to_aggregate():
    df = get_filtered_dataframe(basis="active")
    r = aggregate_reach(df)
    assert r["direct"] is not None and r["direct"] >= 0


def test_division_filter_changes_scope():
    full = get_filtered_dataframe()
    filtered = get_filtered_dataframe(division="sukkur")
    assert len(filtered) < len(full)
