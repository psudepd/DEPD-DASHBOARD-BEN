"""Programme dashboards page (Phase 5A).

Five tabs: NOWPDP, C-ARTS, Deaf Reach, SIPMR, Inclusive Education.
Each tab renders one table per unit group (People / Sessions / Devices /
km per day / Schools) with Download Excel + Download JPG per table.

Programme outputs are not Direct beneficiaries: no family estimate, no
total reach, no F-multiplier here. Those belong to Executive Overview only.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.kpi.programmes import programme_kpis
from src.ui.components import table_with_downloads

PROGRAMMES = [
    ("NOWPDP", "nowpdp"),
    ("C-ARTS", "carts"),
    ("Deaf Reach", "deaf_reach"),
    ("SIPMR", "sipmr"),
    ("Inclusive Education", "inclusive"),
]

UNIT_GROUPS = [
    ("People", ["people"]),
    ("Sessions", ["sessions"]),
    ("Devices", ["devices"]),
    ("km per day", ["km per day"]),
    ("Schools", ["schools"]),
]

CAPTION = (
    "Programme outputs are not Direct beneficiaries. Do not add sessions, "
    "devices, or certificates to Direct."
)


def _render_table(sub: pd.DataFrame, title: str, key: str):
    if sub.empty:
        st.info("No data")
        return
    display = sub.copy()
    display["value"] = display.apply(
        lambda r: "" if pd.isna(r["value"]) else f"{r['value']:,.0f}", axis=1
    )
    display["null_state"] = display["null_state"].fillna("")
    st.markdown(f"**{title}**")
    st.dataframe(
        display[["indicator", "label", "value", "unit", "rule", "null_state"]],
        use_container_width=True,
        hide_index=True,
    )
    table_with_downloads(display, title, key)


def render_programmes(df: pd.DataFrame, filters: dict) -> None:
    """Five tabs: NOWPDP, C-ARTS, Deaf Reach, SIPMR, Inclusive Education."""
    st.title("DEPD Programme Outputs")
    st.caption(CAPTION)

    tabs = st.tabs([name for name, _ in PROGRAMMES])
    for (name, prog), tab in zip(PROGRAMMES, tabs):
        with tab:
            st.subheader(name)
            kpis = programme_kpis(df, prog)
            for group_name, units in UNIT_GROUPS:
                sub = kpis[kpis["unit"].isin(units)]
                if sub.empty:
                    continue
                _render_table(sub, group_name, f"{prog}_{group_name.lower()}")
