"""Geo / GIS tests (Phase 4).

- test_missing_boundaries_returns_none
- test_out_of_sindh_gis_not_pinned (synthetic row 1019: London coords)
- test_missing_gis_not_pinned (synthetic row 1018: blank GIS)
- test_valid_gis_is_pinned (synthetic row 1001: Karachi coords)
- test_static_raises_when_boundaries_missing
"""
import os

import pandas as pd
import pytest

from src.geo.boundaries import load_boundaries, MissingBoundariesError
from src.geo.render_folium import _coords_valid, _gis_lat_lon, build_folium_map
from src.geo.render_static import render_static_jpg

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, os.pardir, "data", "synthetic_submissions.csv")


def _row(rid):
    df = pd.read_csv(FIXTURE)
    r = df[df["_id"] == rid]
    assert len(r) == 1, f"expected one row with _id={rid}, got {len(r)}"
    return r.iloc[0]


def test_missing_boundaries_returns_none():
    gj, ok = load_boundaries()
    assert gj is None
    assert ok is False


def test_out_of_sindh_gis_not_pinned():
    """Row 1019: GIS = London (51.5, -0.12) — outside Sindh bbox → not pinned."""
    row = _row(1019)
    lat, lon = _gis_lat_lon(row)
    assert lat == 51.5 and lon == -0.12
    assert _coords_valid(lat, lon) is False


def test_missing_gis_not_pinned():
    """Row 1018: GIS blank → not pinned."""
    row = _row(1018)
    lat, lon = _gis_lat_lon(row)
    assert lat is None and lon is None
    assert _coords_valid(lat, lon) is False


def test_valid_gis_is_pinned():
    """Row 1001: GIS = Karachi (24.93, 67.07) — inside Sindh bbox → pinned."""
    row = _row(1001)
    lat, lon = _gis_lat_lon(row)
    assert abs(lat - 24.93) < 1e-9 and abs(lon - 67.07) < 1e-9
    assert _coords_valid(lat, lon) is True


def test_fallback_map_returned_when_boundaries_missing():
    df = pd.read_csv(FIXTURE)
    m = build_folium_map(df, None)
    assert m is not None
    assert getattr(m, "_fallback", False) is True


def test_fallback_renders_pins_when_boundaries_missing():
    """Row 1001 (Karachi) has a marker; row 1019 (London) does not."""
    df = pd.read_csv(FIXTURE)
    m = build_folium_map(df, None)
    names = {mk["facility_name"] for mk in m._markers}
    lats = {mk["lat"] for mk in m._markers}
    assert "TEST RCMHC Karachi Central" in names
    assert 24.93 in lats
    assert "TEST RCPH Larkana" not in names
    assert 51.5 not in lats


def test_fallback_lists_invalid_locations():
    """Invalid table contains row 1019 (outside bbox) and row 1018 (blank coords)."""
    df = pd.read_csv(FIXTURE)
    m = build_folium_map(df, None)
    tbl = m._missing_rows
    names_reasons = {
        str(r["facility_name"]): str(r["reason"]) for _, r in tbl.iterrows()
    }
    assert names_reasons.get("TEST RCPH Larkana") == "outside Sindh bbox"
    assert names_reasons.get("TEST Hostel Mirpurkhas Annex") == "no coordinates"
    assert list(tbl.columns) == ["facility_name", "district", "lat", "lon", "reason"]


def test_static_raises_when_boundaries_missing():
    with pytest.raises(MissingBoundariesError):
        render_static_jpg(None)
