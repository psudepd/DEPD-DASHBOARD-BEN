"""Executive Overview page (Phase 3B).

Reach summary block, source mix, Active/Cumulative toggle, additional KPI
cards, time-trend chart, gender donut (W-only), division bar chart, mini
coverage placeholder table, latest-submission status line and a Data received
panel with downloads.

Honours the DEPD_DATA_SOURCE env switch in src/ui.state (synthetic default).
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.export.exporters import footer_text
from src.kpi.aggregate import aggregate_reach
from src.kpi.geography import DIVISION_MAP
from src.ui.components import kpi_card, table_with_downloads
from src.ui.state import DATA_SOURCE

FAMILY_FACTOR = int(os.environ.get("FAMILY_FACTOR", "5"))
DISTRICTS_TOTAL = 30
DIVISIONS_TOTAL = 6


def _section_count(source_mix: dict) -> int:
    return sum(v for k, v in source_mix.items() if str(k).startswith("section:"))


def _review_count(df: pd.DataFrame) -> int:
    if "flags" not in df.columns:
        return 0
    flags = df["flags"].fillna("").astype(str)
    return int(flags.str.contains("W_vs_section_mismatch", na=False).sum())


def _new_waiting(df: pd.DataFrame):
    new_cols = ("w_new", "c_new", "n_new")
    waiting_cols = ("w_waiting", "c_waiting", "n_waiting")
    new_total = 0.0
    waiting_total = 0.0
    for _, row in df.iterrows():
        for c in new_cols:
            if c in row.index:
                try:
                    v = float(row[c])
                except (TypeError, ValueError):
                    continue
                if pd.notna(v):
                    new_total += v
                    break
        for c in waiting_cols:
            if c in row.index:
                try:
                    v = float(row[c])
                except (TypeError, ValueError):
                    continue
                if pd.notna(v):
                    waiting_total += v
                    break
    return new_total, waiting_total


def _gender_donut(df: pd.DataFrame):
    """Male/female/transgender/other only from rows where source == "W"."""
    if df.empty or "source" not in df.columns:
        st.info("Gender not reported")
        return
    w_rows = df[df["source"].astype(str) == "W"]
    if w_rows.empty:
        st.info("Gender not reported")
        return
    male = pd.to_numeric(w_rows.get("w_male", pd.Series([0] * len(w_rows))), errors="coerce").fillna(0).sum()
    female = pd.to_numeric(w_rows.get("w_female", pd.Series([0] * len(w_rows))), errors="coerce").fillna(0).sum()
    trans = pd.to_numeric(w_rows.get("w_trans", pd.Series([0] * len(w_rows))), errors="coerce").fillna(0).sum()
    other = pd.to_numeric(w_rows.get("w_other", pd.Series([0] * len(w_rows))), errors="coerce").fillna(0).sum()
    total = male + female + trans + other
    if total <= 0:
        st.info("Gender not reported")
        return
    fig = go.Figure(data=[go.Pie(
        labels=["Male", "Female", "Transgender", "Other"],
        values=[male, female, trans, other],
        hole=0.45,
        marker_colors=["#18345A", "#008C95", "#2E7D32", "#66758C"],
        textinfo="label+percent",
    )])
    fig.update_layout(
        title="Gender (Section W only)",
        margin=dict(t=40, b=10, l=10, r=10),
        showlegend=False,
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Male {male:,.0f} · Female {female:,.0f} · Transgender {trans:,.0f} · Other {other:,.0f} (Section W rows only)")


def _time_trend(df: pd.DataFrame):
    """Direct by rp_end period. Missing periods stay gaps, not zero."""
    if df.empty or "rp_end" not in df.columns or "direct" not in df.columns:
        st.info("No time-trend data")
        return
    d = df.copy()
    d["rp_end"] = pd.to_datetime(d["rp_end"], errors="coerce")
    d = d.dropna(subset=["rp_end"])
    d["_direct"] = pd.to_numeric(d["direct"], errors="coerce").fillna(0.0)
    if d.empty:
        st.info("No time-trend data")
        return
    trend = d.groupby(d["rp_end"].dt.to_period("M"))["_direct"].sum().reset_index()
    trend["rp_end"] = trend["rp_end"].dt.to_timestamp()
    fig = px.line(trend, x="rp_end", y="_direct", markers=True)
    fig.update_layout(
        title="Direct beneficiaries by reporting period",
        xaxis_title="Period (rp_end)",
        yaxis_title="Direct beneficiaries",
        margin=dict(t=40, b=40, l=40, r=10),
        height=300,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF1F4")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Missing periods are shown as gaps, not zero.")


def _division_bar(df: pd.DataFrame):
    """Direct by division_mapped."""
    if df.empty or "division_mapped" not in df.columns or "direct" not in df.columns:
        st.info("No division data")
        return
    d = df.copy()
    d["_direct"] = pd.to_numeric(d["direct"], errors="coerce").fillna(0.0)
    div = d.groupby("division_mapped")["_direct"].sum().reset_index()
    div = div.sort_values("_direct", ascending=False)
    fig = px.bar(div, x="division_mapped", y="_direct", color_discrete_sequence=["#008C95"])
    fig.update_layout(
        title="Direct beneficiaries by division",
        xaxis_title="Division (from district mapping)",
        yaxis_title="Direct beneficiaries",
        margin=dict(t=40, b=40, l=40, r=10),
        height=300,
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig, use_container_width=True)


def _coverage_table(df: pd.DataFrame):
    """Mini coverage placeholder: district table."""
    if df.empty:
        st.info("No district data")
        return
    d = df.copy()
    d["_direct"] = pd.to_numeric(d["direct"], errors="coerce").fillna(0.0)
    cov = d.groupby(["district", "division_mapped"]).agg(
        reports=("_direct", "size"),
        direct=("_direct", "sum"),
    ).reset_index()
    cov = cov.sort_values(["division_mapped", "district"])
    cov.columns = ["District", "Division", "Reports", "Direct"]
    st.dataframe(cov, use_container_width=True, hide_index=True)
    st.caption(
        "District boundary file not yet supplied — table view only. "
        "Districts with no reports do not appear here."
    )


def _latest_status(df: pd.DataFrame):
    if df.empty:
        st.caption("Last submission: — · 0 reports in selection")
        return
    ts = "—"
    if "_submission_time" in df.columns:
        times = pd.to_datetime(df["_submission_time"], errors="coerce").dropna()
        if len(times):
            ts = times.max().strftime("%Y-%m-%d %H:%M")
    st.caption(f"Last submission: {ts} · {len(df)} reports in selection")


def render(df: pd.DataFrame, basis: str = "active"):
    """Render the Executive Overview page for the given filtered dataframe."""
    st.title("DEPD Executive Analytics")

    if DATA_SOURCE != "live":
        st.warning(
            "SYNTHETIC TEST DATA — demonstrating the pipeline, not real figures. "
            "Set DEPD_DATA_SOURCE=live to read from KoboToolbox."
        )

    st.caption(f"Filters active · Basis: {basis}")

    r = aggregate_reach(df, family_factor=FAMILY_FACTOR)
    source_mix = r.get("source_mix", {})
    review_n = _review_count(df)
    new_total, waiting_total = _new_waiting(df)

    # --- Reach summary block ---
    st.subheader("Reach summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        kpi_card(
            "Direct beneficiaries",
            f"{r['direct']:,.0f}",
            "Facility-reported unique headcounts; resolved per Section 5.3 "
            "(w_total first, then section figure); not deduplicated across facilities.",
        )
        st.caption(
            f"{source_mix.get('W', 0)} from Section W · "
            f"{_section_count(source_mix)} from section data · "
            f"{source_mix.get('zero_report', 0)} zero reports · "
            f"{review_n} need review"
        )
    with col2:
        kpi_card(
            "Estimated family (indirect)",
            f"{r['family']:,.0f}",
            f"Estimated model: Direct × {FAMILY_FACTOR}. Not a count — labelled Estimated.",
        )
    with col3:
        kpi_card(
            "Estimated total reach",
            f"{r['total']:,.0f}",
            "Estimated total reach = Direct + family estimate (Direct × (1 + F)).",
        )

    # --- Additional KPI cards ---
    st.subheader("Coverage & activity")
    col4, col5, col6, col7, col8, col9 = st.columns(6)
    with col4:
        kpi_card("Reports", len(df))
    with col5:
        kpi_card("Facilities", df["facility_name"].nunique() if len(df) else 0)
    with col6:
        d_rep = df[df["district"].notna() & (df["district"].astype(str).str.strip() != "")] if len(df) else df
        kpi_card("Districts reporting", f"{d_rep['district'].nunique()}/{DISTRICTS_TOTAL}")
    with col7:
        d_div = df[df["division_mapped"].notna() & (df["division_mapped"].astype(str).str.strip() != "")] if len(df) else df
        kpi_card("Divisions reporting", f"{d_div['division_mapped'].nunique()}/{DIVISIONS_TOTAL}")
    with col8:
        kpi_card("New beneficiaries", f"{new_total:,.0f}")
    with col9:
        kpi_card("Waiting list", f"{waiting_total:,.0f}")

    # --- Charts row ---
    st.subheader("Trends & comparison")
    cA, cB = st.columns(2)
    with cA:
        _time_trend(df)
    with cB:
        _division_bar(df)

    cC, cD = st.columns(2)
    with cC:
        _gender_donut(df)
    with cD:
        st.markdown("**Mini coverage (district table)**")
        _coverage_table(df)

    # --- Latest submission status ---
    _latest_status(df)

    # --- Data received panel ---
    st.subheader("Data received")
    cE, cF, cG = st.columns(3)
    with cE:
        kpi_card("Reports received", len(df))
        kpi_card("Distinct facilities", df["facility_name"].nunique() if len(df) else 0)
    with cF:
        kpi_card("Districts reporting", f"{d_rep['district'].nunique()}/{DISTRICTS_TOTAL}")
        st.caption("Last submission time (Asia/Karachi)")
        _latest_status(df)
    with cG:
        st.markdown("**Source mix**")
        st.write(source_mix if source_mix else "No data")

    st.markdown("**Latest 10 reports**")
    if len(df):
        latest = (
            df.sort_values("_submission_time", ascending=False)
            [["facility_name", "facility_type", "district", "rp_end", "direct", "source", "flags"]]
            .head(10)
        )
        table_with_downloads(latest, "Latest 10 reports", "exec_latest_10")
    else:
        st.info("No reports in selection")
