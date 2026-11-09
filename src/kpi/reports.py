"""Summary reports for the DEPD KPI dashboard.

Produces summary_report (one row per division/district/service_type group)
and summary_sheet (one row per submission, excluding regional_dir).
"""
from __future__ import annotations

import os

import pandas as pd

from src.kpi.aggregate import _first_non_blank
from src.kpi.geography import add_division_columns
from src.kpi.resolver import resolve_active

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
OWNERSHIP_PATH = os.path.join(PROJECT_ROOT, "data", "ownership_by_type.csv")
GIS_ICON_MAP_PATH = os.path.join(PROJECT_ROOT, "docs", "gis_icon_map.csv")


def _load_ownership() -> pd.DataFrame:
    return pd.read_csv(OWNERSHIP_PATH)


def _load_icon_map():
    if os.path.exists(GIS_ICON_MAP_PATH):
        return pd.read_csv(GIS_ICON_MAP_PATH)
    return None


def _ownership_class(ft: str, ownership: pd.DataFrame) -> str:
    m = ownership[ownership["facility_type"] == ft]
    if len(m) > 0:
        v = m.iloc[0]["ownership_class"]
        if pd.notna(v):
            return str(v).strip()
    return "other"


def _service_category(ft: str, ownership: pd.DataFrame, icon_map) -> str:
    m = ownership[ownership["facility_type"] == ft]
    if len(m) > 0 and "class_status" in m.columns:
        v = m.iloc[0]["class_status"]
        if pd.notna(v) and str(v).strip() != "":
            return str(v).strip()
    if icon_map is not None and "facility_type" in icon_map.columns and "icon_group" in icon_map.columns:
        im = icon_map[icon_map["facility_type"] == ft]
        if len(im) > 0:
            v = im.iloc[0]["icon_group"]
            if pd.notna(v) and str(v).strip() != "":
                return str(v).strip()
    return ft


_REPORT_COLS = ["division", "district", "service_type", "reports", "direct", "new", "waiting", "indirect_x5", "total_reach"]
_SHEET_COLS = ["service_type", "service_category", "ownership_class", "division", "district", "organisation", "reporting_period", "direct", "indirect_x5", "total_reach", "source", "flags"]


def summary_report(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=_REPORT_COLS)
    d = add_division_columns(df.copy())
    d = d[d["facility_type"].astype(str) != "regional_dir"].copy()
    if len(d) == 0:
        return pd.DataFrame(columns=_REPORT_COLS)

    d["_direct"] = pd.to_numeric(
        d.get("direct", pd.Series([0.0] * len(d), index=d.index)), errors="coerce"
    ).fillna(0.0)
    d["_new"] = d.apply(lambda r: _first_non_blank(r, ("w_new", "c_new", "n_new")), axis=1)
    d["_waiting"] = d.apply(lambda r: _first_non_blank(r, ("w_waiting", "c_waiting", "n_waiting")), axis=1)

    g = d.groupby(["division_mapped", "district", "facility_type"], dropna=False)
    out = g.agg(
        reports=("_direct", "size"),
        direct=("_direct", "sum"),
        new=("_new", "sum"),
        waiting=("_waiting", "sum"),
    ).reset_index()

    out = out[out["reports"] > 0].copy()
    out["indirect_x5"] = out["direct"] * 5
    out["total_reach"] = out["direct"] * 6
    out = out.rename(columns={"division_mapped": "division", "facility_type": "service_type"})
    out = out[_REPORT_COLS]
    out = out.sort_values(["division", "district", "service_type"], ascending=True).reset_index(drop=True)
    return out


def summary_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=_SHEET_COLS)
    d = add_division_columns(df.copy())
    d = d[d["facility_type"].astype(str) != "regional_dir"].copy()
    if len(d) == 0:
        return pd.DataFrame(columns=_SHEET_COLS)

    ownership = _load_ownership()
    icon_map = _load_icon_map()

    d["service_type"] = d["facility_type"].astype(str)
    d["ownership_class"] = d["facility_type"].map(lambda ft: _ownership_class(ft, ownership))
    d["service_category"] = d["facility_type"].map(lambda ft: _service_category(ft, ownership, icon_map))
    d["division"] = d["division_mapped"].astype(str)
    d["district"] = d["district"].astype(str)

    if "facility_name" in d.columns:
        org = d["facility_name"].astype(str)
    else:
        org = d["facility_type"].astype(str)
    if "r_org" in d.columns:
        mask = (d["facility_type"] == "assistive_ip") & d["r_org"].notna() & (d["r_org"].astype(str).str.strip() != "")
        org = org.where(~mask, d["r_org"].astype(str))
    d["organisation"] = org

    if "rp_end" in d.columns:
        d["reporting_period"] = pd.to_datetime(d["rp_end"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        d["reporting_period"] = ""

    d["_direct"] = pd.to_numeric(
        d.get("direct", pd.Series([0.0] * len(d), index=d.index)), errors="coerce"
    ).fillna(0.0)
    d["direct"] = d["_direct"]
    d["indirect_x5"] = d["_direct"] * 5
    d["total_reach"] = d["_direct"] * 6

    if "source" in d.columns:
        d["source"] = d["source"].fillna("").astype(str)
    else:
        resolved = d.apply(lambda r: resolve_active(r.to_dict()), axis=1)
        d["source"] = [str(r.get("source", "")) for r in resolved]

    if "flags" in d.columns:
        d["flags"] = d["flags"].fillna("").astype(str)
    else:
        resolved = d.apply(lambda r: resolve_active(r.to_dict()), axis=1)
        d["flags"] = [str(r.get("flags", "")) for r in resolved]

    out = d[_SHEET_COLS]
    out = out.sort_values(["service_type", "division", "district"], ascending=True).reset_index(drop=True)
    return out
