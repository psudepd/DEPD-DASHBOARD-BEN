"""Folium map renderer for the DEPD Sindh GIS page (Phase 4).

Renders facility pins only at valid coordinates:
  (a) _GIS_latitude / _GIS_longitude present, AND
  (b) point inside Sindh bbox (24.0-28.5 N, 66.5-71.5 E), AND
  (c) point inside the polygon of the submitted district (when boundaries
      are available).
Otherwise no pin; the facility is listed in a "Missing / invalid location"
panel (handled by the map page).

Marker colour comes from data/ownership_by_type.csv (via MapStyler),
shape + icon from docs/gis_icon_map.csv.
"""
from __future__ import annotations

import math
import os

import folium
import pandas as pd
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from src.geo.map_styling import MapStyler

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
OWNERSHIP_PATH = os.path.join(PROJECT_ROOT, "data", "ownership_by_type.csv")
ICON_MAP_PATH = os.path.join(PROJECT_ROOT, "docs", "gis_icon_map.csv")

SINDH_BBOX = (24.0, 66.5, 28.5, 71.5)  # min_lat, min_lon, max_lat, max_lon


def _icon_styles() -> dict:
    """Load colour/shape/icon per facility type from docs/gis_icon_map.csv."""
    icon_df = pd.read_csv(ICON_MAP_PATH)
    styles: dict = {}
    for _, r in icon_df.iterrows():
        ftype = str(r["facility_type"]).strip()
        styles[ftype] = {
            "color": str(r["colour_hex"]).strip(),
            "shape": str(r["marker_shape"]).strip(),
            "icon": str(r["suggested_icon_name"]).strip(),
        }
    return styles


_ICON_STYLES = _icon_styles()


def _icon_style(ftype: str) -> dict:
    return _ICON_STYLES.get(
        ftype, {"color": "#6B7280", "shape": "circle", "icon": "question"}
    )


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if not math.isnan(x) else None


def _gis_lat_lon(row):
    """Return (lat, lon) from _GIS_* columns or by parsing the GIS geopoint
    string ("lat lon alt prec"). Returns (None, None) when unavailable."""
    lat = _num(row.get("_GIS_latitude"))
    lon = _num(row.get("_GIS_longitude"))
    if lat is not None and lon is not None:
        return lat, lon
    gis = row.get("GIS")
    if gis is None:
        return None, None
    try:
        parts = str(gis).split()
        if len(parts) >= 2:
            lat = _num(parts[0])
            lon = _num(parts[1])
            if lat is not None and lon is not None:
                return lat, lon
    except (AttributeError, ValueError):
        pass
    return None, None


def _coords_valid(lat: float, lon: float) -> bool:
    if lat is None or lon is None:
        return False
    min_lat, min_lon, max_lat, max_lon = SINDH_BBOX
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def _point_in_district(lat: float, lon: float, district: str, district_polys: dict) -> bool:
    poly = district_polys.get(district)
    if poly is None or not isinstance(poly, BaseGeometry):
        return True  # no polygon to check against -> accept if coords valid
    return poly.contains(Point(lon, lat))


def _styler():
    return MapStyler(OWNERSHIP_PATH, ICON_MAP_PATH)


FALLBACK_WARNING = (
    '<div style="padding:12px;border:1px solid #b00020;background:#fdecea;color:#660000;">'
    "<b>District boundaries not loaded.</b> "
    "Pins shown for <b>MANUAL verification only</b>. "
    "A point inside Sindh bbox is <b>NOT</b> a guarantee it belongs to the "
    "submitted district. Confirm each pin against the district list before "
    "treating it as valid.</div>"
)


def _fallback_map(df: pd.DataFrame):
    """Fallback folium map when district boundaries are missing.

    OpenStreetMap tiles, no district polygons, pins for every row with
    valid coordinates (inside Sindh bbox). District point-in-polygon check
    is DISABLED because polygons are unavailable; only the bbox check runs.
    """
    m = folium.Map(location=[26.5, 68.5], zoom_start=7, tiles="OpenStreetMap")
    markers = []
    missing_rows = []
    if df is not None and len(df):
        for _, row in df.iterrows():
            ftype = str(row.get("facility_type", "")).strip()
            style = _icon_style(ftype)
            lat, lon = _gis_lat_lon(row)
            district = row.get("district")
            # Fallback mode: bbox check only; district containment disabled.
            valid = lat is not None and lon is not None and _coords_valid(lat, lon)
            if not valid:
                if lat is None or lon is None:
                    reason = "no coordinates"
                else:
                    reason = "outside Sindh bbox"
                missing_rows.append(
                    {
                        "facility_name": row.get("facility_name", ""),
                        "district": district,
                        "lat": lat,
                        "lon": lon,
                        "reason": reason,
                    }
                )
                continue
            popup = (
                f"<b>{row.get('facility_name','')}</b><br>"
                f"Type: {ftype}<br>"
                f"District: {row.get('district','')}<br>"
                f"Direct: {row.get('direct','')}"
            )
            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=str(row.get("facility_name", "")),
                icon=folium.Icon(
                    color=style["color"],
                    icon=style["icon"],
                    prefix="fa",
                ),
            ).add_to(m)
            markers.append(
                {
                    "facility_name": row.get("facility_name", ""),
                    "facility_type": ftype,
                    "district": district,
                    "lat": lat,
                    "lon": lon,
                }
            )
    m._fallback = True
    m._markers = markers
    m._missing_rows = (
        pd.DataFrame(missing_rows, columns=["facility_name", "district", "lat", "lon", "reason"])
        if missing_rows
        else pd.DataFrame(columns=["facility_name", "district", "lat", "lon", "reason"])
    )
    m._warning_html = FALLBACK_WARNING
    return m


def build_folium_map(df: pd.DataFrame, boundaries: dict | None):
    """Build a folium.Map for the Sindh district boundaries.

    When boundaries is None (GeoJSON missing), renders a fallback folium map
    with OpenStreetMap tiles, no district polygons, and pins for every row
    with valid coordinates (bbox check only; district containment disabled,
    because polygons are unavailable).
    """
    if boundaries is None:
        return _fallback_map(df)

    # District polygons keyed by district name for point-in-district checks.
    district_polys: dict = {}
    for feature in boundaries.get("features", []):
        props = feature.get("properties", {}) or {}
        name = (
            props.get("district_name")
            or props.get("name")
            or props.get("DISTRICT")
            or props.get("district")
        )
        geom = feature.get("geometry")
        if name is not None and geom is not None:
            district_polys[str(name).strip()] = shape(geom)

    styler = _styler()

    # Centre on Sindh.
    m = folium.Map(location=[26.5, 68.5], zoom_start=7, tiles="CartoDB positron")

    # Neutral grey division polygons + district outlines.
    for feature in boundaries.get("features", []):
        props = feature.get("properties", {}) or {}
        name = (
            props.get("district_name")
            or props.get("name")
            or props.get("DISTRICT")
            or props.get("district")
        )
        geom = feature.get("geometry")
        if name is None or geom is None:
            continue
        folium.GeoJson(
            feature,
            style_function=lambda f: {
                "fillColor": "#EEF1F4",
                "color": "#E3E8ED",
                "weight": 1,
                "fillOpacity": 0.6,
            },
            tooltip=str(name),
        ).add_to(m)

    # Facility pins (valid coordinates only).
    if df is not None and len(df):
        missing_rows = []
        for _, row in df.iterrows():
            ftype = str(row.get("facility_type", "")).strip()
            style = styler.get_marker_style(ftype)
            lat, lon = _gis_lat_lon(row)
            district = row.get("district")
            valid = (
                lat is not None
                and lon is not None
                and _coords_valid(lat, lon)
                and _point_in_district(lat, lon, district, district_polys)
            )
            if not valid:
                missing_rows.append(row)
                continue
            popup = (
                f"<b>{row.get('facility_name','')}</b><br>"
                f"Type: {ftype}<br>"
                f"District: {row.get('district','')}<br>"
                f"Direct: {row.get('direct','')}"
            )
            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=str(row.get("facility_name", "")),
                icon=folium.Icon(
                    color=style["color"],
                    icon=style["icon"],
                    prefix="fa",
                ),
            ).add_to(m)

        # Missing / invalid location panel (returned as attribute for the page).
        m._missing_rows = pd.DataFrame(missing_rows) if missing_rows else pd.DataFrame()
    else:
        m._missing_rows = pd.DataFrame()

    return m


def missing_boundaries_html() -> str:
    """HTML shown when the boundary GeoJSON is missing."""
    return (
        '<div style="padding:12px;border:1px solid #b00020;background:#fdecea;color:#660000;">'
        "<b>District boundary GeoJSON missing.</b> "
        "Download the Pakistan subnational administrative boundaries from HDX and place it at "
        "<code>data/boundaries/sindh_districts.geojson</code>. "
        "Table view shown instead.</div>"
    )
