"""Breakdowns page (Phase 3C).

Three reconciliation tables — by service type (as filed), by division
(from district mapping, never submitted division), and by district — each
following the Active/Cumulative toggle. All three reconcile to the same
grand total as aggregate_reach().

Also holds the "suggested corrections" banner/toggle for the service table
(default "as filed"; the toggle is disabled until Phase 5 supplies the
reviewed override table).
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.kpi.aggregate import aggregate_reach, breakdown
from src.kpi.geography import DIVISION_MAP, normalise
from src.ui.components import table_with_downloads

OWNERSHIP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ownership_by_type.csv",
)
DISTRICT_DIVISION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "district_division.csv",
)

FAMILY_FACTOR = int(os.environ.get("FAMILY_FACTOR", "5"))

# Canonical lists (never invented): 18 services, 6 divisions, 30 districts.
SERVICE_TYPES = [
    "rcmhc", "rcph", "gov_se", "inclusive", "deaf_reach", "sipmr", "ipmr",
    "carts", "nowpdp", "hostel", "vtc", "academy", "gia",
    "sindh_persons_with_disabilitie", "dis_cer",
    "legal_support__beneficiaries", "pcrdp", "assistive_ip",
]
DIVISIONS_6 = sorted({str(v).strip() for v in DIVISION_MAP.values()})
DISTRICTS_30 = sorted(DIVISION_MAP.keys())


def _ownership_df():
    return pd.read_csv(OWNERSHIP_PATH)


def _district_division_df():
    return pd.read_csv(DISTRICT_DIVISION_PATH)


def _male_female_other(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """Male/female/other sums from W-only rows, grouped by key_col."""
    if df.empty or "source" not in df.columns:
        return pd.DataFrame(columns=[key_col, "male", "female", "transgender", "other"])
    w = df[df["source"].astype(str) == "W"].copy()
    if w.empty:
        return pd.DataFrame(columns=[key_col, "male", "female", "transgender", "other"])
    w["_male"] = pd.to_numeric(w.get("w_male", 0), errors="coerce").fillna(0.0)
    w["_female"] = pd.to_numeric(w.get("w_female", 0), errors="coerce").fillna(0.0)
    w["_trans"] = pd.to_numeric(w.get("w_trans", 0), errors="coerce").fillna(0.0)
    w["_other"] = pd.to_numeric(w.get("w_other", 0), errors="coerce").fillna(0.0)
    g = w.groupby(key_col)[["_male", "_female", "_trans", "_other"]].sum().reset_index()
    g.columns = [key_col, "male", "female", "transgender", "other"]
    return g


def _source_mix_flag(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """Per-group source-mix flag string: W:x · section:y · zero:z · review:w."""
    if df.empty or "source" not in df.columns or "flags" not in df.columns:
        return pd.DataFrame(columns=[key_col, "source_mix_flag"])
    rows = []
    for key, sub in df.groupby(key_col):
        sm = {}
        for s in sub["source"].fillna("").astype(str):
            sm[s] = sm.get(s, 0) + 1
        flags = sub["flags"].fillna("").astype(str)
        review = int(flags.str.contains("W_vs_section_mismatch", na=False).sum())
        parts = []
        if sm.get("W", 0):
            parts.append(f"W:{sm['W']}")
        sec = sum(v for k, v in sm.items() if str(k).startswith("section:"))
        if sec:
            parts.append(f"section:{sec}")
        if sm.get("zero_report", 0):
            parts.append(f"zero:{sm['zero_report']}")
        if review:
            parts.append(f"review:{review}")
        rows.append({key_col: key, "source_mix_flag": " · ".join(parts) if parts else "—"})
    return pd.DataFrame(rows)


def _full_index(base: pd.DataFrame, key_col: str, all_keys: list, label_col: str | None = None) -> pd.DataFrame:
    """Reindex base onto all_keys so empty categories show as rows."""
    if base.empty:
        out = pd.DataFrame({key_col: all_keys})
    else:
        out = base.set_index(key_col).reindex(all_keys).reset_index()
    if label_col and label_col in base.columns and label_col not in out.columns:
        out[label_col] = out[key_col]
    out[key_col] = out[key_col].astype(str)
    for c in ("reports", "facilities", "direct", "family_x5", "total_reach", "new", "waiting", "cumulative"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
        else:
            out[c] = 0.0
    if "source_mix_flag" in out.columns:
        out["source_mix_flag"] = out["source_mix_flag"].fillna("—")
    if "male" in out.columns:
        for c in ("male", "female", "transgender", "other"):
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    return out


def _augment_breakdown(df: pd.DataFrame, by: str, all_keys: list, key_col: str, label_col: str | None = None):
    """Run breakdown() then add male/female/other and source-mix-flag columns."""
    base = breakdown(df, by)
    if base.empty:
        base = pd.DataFrame(columns=["group", "reports", "facilities", "direct", "family_x5",
                                     "total_reach", "new", "waiting", "cumulative", "source_mix"])
    base = base.rename(columns={"group": key_col})
    mfo = _male_female_other(df, key_col)
    smf = _source_mix_flag(df, key_col)
    out = base.merge(mfo, on=key_col, how="outer").merge(smf, on=key_col, how="outer")
    return _full_index(out, key_col, all_keys, label_col)


def _suggested_corrections_count(df: pd.DataFrame) -> int:
    """Name contains 'deaf reach' but facility_type == gov_se."""
    if df.empty or "facility_name" not in df.columns:
        return 0
    names = df["facility_name"].fillna("").astype(str)
    mask = names.str.contains("deaf reach", case=False, na=False) & (df["facility_type"].astype(str) == "gov_se")
    return int(mask.sum())


def render_service_table(df: pd.DataFrame):
    st.markdown("### By service type (as filed)")
    corr_n = _suggested_corrections_count(df)
    if corr_n:
        st.info(
            f"Suggested corrections: {corr_n} report(s) whose name contains 'deaf reach' "
            f"but are filed as gov_se. Shown for review only; applied through a "
            f"reviewed override in Phase 5."
        )
    st.toggle("With suggested corrections", value=False, disabled=True, key="breakdown_svc_corrections",
              help="Phase 5 will supply the reviewed override table.")
    out = _augment_breakdown(df, "service", SERVICE_TYPES, "Service type")
    out = out[out["Service type"] != "regional_dir"]
    out["indirect_x5"] = out["direct"] * FAMILY_FACTOR
    out["total_reach"] = out["direct"] * (1 + FAMILY_FACTOR)
    out["Status"] = out.apply(
        lambda r: "No reports yet" if r["reports"] == 0 else "Updated", axis=1
    )
    display = out[[
        "Service type", "Status", "reports", "facilities", "direct", "indirect_x5",
        "total_reach", "new", "waiting", "cumulative", "male", "female", "transgender",
        "other", "source_mix_flag",
    ]]
    display.columns = [
        "Service type", "Status", "Reports", "Facilities", "Direct",
        "Indirect x5 (Est.)", "Total reach (Est.)", "New", "Waiting", "Cumulative",
        "Male", "Female", "Transgender", "Other", "Source mix flag",
    ]
    st.dataframe(display, use_container_width=True, hide_index=True)
    table_with_downloads(display, "Breakdown by service type", "breakdown_service")


def render_division_table(df: pd.DataFrame):
    st.markdown("### By division (from district mapping)")
    out = _augment_breakdown(df, "division", DIVISIONS_6, "Division", label_col="Division")
    out["indirect_x5"] = out["direct"] * FAMILY_FACTOR
    out["total_reach"] = out["direct"] * (1 + FAMILY_FACTOR)
    out["Status"] = out.apply(
        lambda r: "No reports" if r["reports"] == 0 else "Updated", axis=1
    )
    display = out[[
        "Division", "Status", "reports", "facilities", "direct", "indirect_x5",
        "total_reach", "new", "waiting", "cumulative", "male", "female", "transgender",
        "other", "source_mix_flag",
    ]]
    display.columns = [
        "Division", "Status", "Reports", "Facilities", "Direct",
        "Indirect x5 (Est.)", "Total reach (Est.)", "New", "Waiting", "Cumulative",
        "Male", "Female", "Transgender", "Other", "Source mix flag",
    ]
    st.dataframe(display, use_container_width=True, hide_index=True)
    table_with_downloads(display, "Breakdown by division", "breakdown_division")


def render_district_table(df: pd.DataFrame):
    st.markdown("### By district")
    dd = _district_division_df()
    div_by_district = {
        str(r["district_code"]).strip(): str(r["division_code"]).strip()
        for _, r in dd.iterrows()
    }
    labels = [f"{d} ({div_by_district.get(d, 'unknown')})" for d in DISTRICTS_30]
    out = _augment_breakdown(df, "district", DISTRICTS_30, "District")
    out["indirect_x5"] = out["direct"] * FAMILY_FACTOR
    out["total_reach"] = out["direct"] * (1 + FAMILY_FACTOR)
    out["Division"] = out["District"].map(div_by_district).fillna("unknown")
    out["Status"] = out.apply(
        lambda r: "No report" if r["reports"] == 0 else "Updated", axis=1
    )
    display = out[[
        "District", "Division", "Status", "reports", "facilities", "direct",
        "indirect_x5", "total_reach", "new", "waiting", "cumulative",
        "male", "female", "transgender", "other", "source_mix_flag",
    ]]
    display.columns = [
        "District", "Division", "Status", "Reports", "Facilities", "Direct",
        "Indirect x5 (Est.)", "Total reach (Est.)", "New", "Waiting", "Cumulative",
        "Male", "Female", "Transgender", "Other", "Source mix flag",
    ]
    st.dataframe(display, use_container_width=True, hide_index=True)
    table_with_downloads(display, "Breakdown by district", "breakdown_district")


def render(df: pd.DataFrame, basis: str = "active"):
    """Render the Breakdowns page."""
    st.title("DEPD Breakdowns")
    st.caption(f"Basis: {basis}  ·  All three tables reconcile to the same Direct grand total.")

    render_service_table(df)
    render_division_table(df)
    render_district_table(df)

    # Reconciliation hint
    total = aggregate_reach(df, family_factor=FAMILY_FACTOR)["direct"]
    st.caption(
        f"Grand total (Direct): {total:,.0f} — service, division and district tables all reconcile "
        f"to this figure."
    )
