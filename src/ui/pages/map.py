"""GIS map page (Phase 4).

Map + four panels:
  (1) Headline: Direct, Estimated family, Estimated total
  (2) Direct by service type: 18 cards
  (3) Data received: reports, facilities, districts x/30, last submission,
      source mix, latest 10 reports
  (4) Filters above the map: service type, ownership class, region, district

When the boundary GeoJSON is missing (the current state), a clear message is
shown and a fallback district table + bar chart render instead of a map.
Click-to-filter wiring is Phase 5: filters above the map drive the panels;
clicking a marker shows a popup only.
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.export.exporters import footer_text
from src.geo.boundaries import load_boundaries
from src.geo.render_folium import build_folium_map, missing_boundaries_html
from src.geo.render_static import render_static_jpg
from src.kpi.aggregate import aggregate_reach
from src.kpi.geography import DIVISION_MAP
from src.ui.components import kpi_card, table_with_downloads
from src.ui.state import DATA_SOURCE, get_filtered_dataframe, load_data

FAMILY_FACTOR = int(os.environ.get("FAMILY_FACTOR", "5"))
DISTRICTS_TOTAL = 30

OWNERSHIP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ownership_by_type.csv",
)


def _ownership_by_type() -> dict:
    df = pd.read_csv(OWNERSHIP_PATH)
    return {
        str(r["facility_type"]).strip(): str(r["ownership_class"]).strip()
        for _, r in df.iterrows()
    }


def _render_map_or_fallback(df: pd.DataFrame):
    boundaries, ok = load_boundaries()
    if not ok:
        st.components.v1.html(missing_boundaries_html(), height=70)
        st.info("Fallback: district table (boundary file not yet supplied).")
        from src.kpi.aggregate import breakdown

        dist = breakdown(df, "district")
        if len(dist):
            st.bar_chart(dist.set_index("group")["direct"])
        else:
            st.info("No district data.")
        return

    fmap = build_folium_map(df, boundaries)
    if fmap is None:
        st.info("Map unavailable.")
        return
    st_folium(fmap, width=700, height=500, key="depd_map")
    missing = getattr(fmap, "_missing_rows", None)
    if missing is not None and len(missing):
        with st.expander("Missing / invalid location facilities", expanded=False):
            st.dataframe(
                missing[["facility_name", "facility_type", "district"]]
                .rename(columns={"facility_name": "Facility", "facility_type": "Type", "district": "District"}),
                use_container_width=True,
                hide_index=True,
            )


def _headline_panel(df: pd.DataFrame):
    r = aggregate_reach(df, family_factor=FAMILY_FACTOR)
    kpi_card("Direct beneficiaries", f"{r['direct']:,.0f}",
             "Facility-reported unique headcounts (resolved per Section 5.3).")
    kpi_card("Estimated family (indirect)", f"{r['family']:,.0f}",
             f"Estimated model: Direct × {FAMILY_FACTOR}. Not a count.")
    kpi_card("Estimated total reach", f"{r['total']:,.0f}",
             "Estimated total reach = Direct + family estimate.")


def _service_cards(df: pd.DataFrame):
    st.markdown("**Direct by service type (18)**")
    from src.kpi.aggregate import breakdown

    bt = breakdown(df, "service")
    types = [
        "rcmhc", "rcph", "gov_se", "inclusive", "deaf_reach", "sipmr", "ipmr",
        "carts", "nowpdp", "hostel", "vtc", "academy", "gia",
        "sindh_persons_with_disabilitie", "dis_cer",
        "legal_support__beneficiaries", "pcrdp", "assistive_ip",
    ]
    by_type = {}
    if len(bt):
        by_type = dict(zip(bt["group"].astype(str), bt["direct"]))
    cols = st.columns(3)
    for i, t in enumerate(types):
        with cols[i % 3]:
            val = by_type.get(t, 0.0)
            status = "No reports" if val == 0 and t not in by_type else ""
            kpi_card(t, f"{val:,.0f}" + ("" if status == "" else " · No reports"))


def _data_received_panel(df: pd.DataFrame):
    st.markdown("**Data received**")
    r = aggregate_reach(df, family_factor=FAMILY_FACTOR)
    kpi_card("Reports received", len(df))
    kpi_card("Distinct facilities", df["facility_name"].nunique() if len(df) else 0)
    d_rep = df[df["district"].notna() & (df["district"].astype(str).str.strip() != "")] if len(df) else df
    kpi_card("Districts reporting", f"{d_rep['district'].nunique()}/{DISTRICTS_TOTAL}")
    st.caption("Last submission time (Asia/Karachi)")
    if len(df) and "_submission_time" in df.columns:
        times = pd.to_datetime(df["_submission_time"], errors="coerce").dropna()
        ts = times.max().strftime("%Y-%m-%d %H:%M") if len(times) else "—"
        st.caption(ts)
    else:
        st.caption("—")
    st.markdown("**Source mix**")
    st.write(r.get("source_mix", {}) or "No data")
    st.markdown("**Latest 10 reports**")
    if len(df):
        latest = (
            df.sort_values("_submission_time", ascending=False)
            [["facility_name", "facility_type", "district", "rp_end", "direct", "source", "flags"]]
            .head(10)
        )
        table_with_downloads(latest, "Latest 10 reports", "map_latest_10")
    else:
        st.info("No reports in selection")


def render(df: pd.DataFrame, basis: str = "active"):
    """Render the GIS map page."""
    st.title("DEPD Geographic Coverage")
    if DATA_SOURCE != "live":
        st.warning(
            "SYNTHETIC TEST DATA — demonstrating the pipeline, not real figures."
        )

    st.caption(f"Basis: {basis}")

    # --- Filters above the map ---
    ownership_by_type = _ownership_by_type()
    all_df = load_data()
    services = ["All"] + sorted(all_df["facility_type"].dropna().unique().tolist())
    ownership_classes = ["All"] + sorted(set(ownership_by_type.values()))
    regions = ["All"] + sorted(DIVISION_MAP.values())
    districts = ["All"] + sorted(DIVISION_MAP.keys())

    f1, f2, f3, f4 = st.columns(4)
    svc = f1.selectbox("Service type", services, key="map_service")
    own = f2.selectbox("Ownership class", ownership_classes, key="map_ownership")
    reg = f3.selectbox("Region (division)", regions, key="map_region")
    dist = f4.selectbox("District", districts, key="map_district")

    fdf = df.copy()
    if svc != "All":
        fdf = fdf[fdf["facility_type"].astype(str) == svc]
    if own != "All":
        allowed = {t for t, c in ownership_by_type.items() if c == own}
        fdf = fdf[fdf["facility_type"].astype(str).isin(allowed)]
    if reg != "All":
        fdf = fdf[fdf["division_mapped"].astype(str) == reg]
    if dist != "All":
        fdf = fdf[fdf["district"].astype(str) == dist]

    chip = " · ".join(
        f"{k}={v}" for k, v in {
            "service": svc, "ownership": own, "region": reg, "district": dist,
        }.items() if v != "All"
    ) or "All Sindh"
    st.caption(f"Filters: {chip} · Basis: {basis}")

    # --- Layout: map left, panels right ---
    map_col, panel_col = st.columns([3, 2])
    with map_col:
        st.markdown("**Sindh district map**")
        _render_map_or_fallback(fdf)
    with panel_col:
        st.markdown("### Headline")
        _headline_panel(fdf)
        st.markdown("---")
        st.markdown("### Direct by service type")
        _service_cards(fdf)
        st.markdown("---")
        st.markdown("### Data received")
        _data_received_panel(fdf)
