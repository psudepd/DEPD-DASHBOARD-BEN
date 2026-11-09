"""UI components: KPI cards and downloadable tables."""
from __future__ import annotations

import streamlit as st

from src.export.exporters import df_to_jpg_bytes, df_to_xlsx_bytes, footer_text


def kpi_card(label: str, value, tooltip: str = None):
    """Renders one KPI card via st.metric."""
    if tooltip:
        label = f"{label} ⓘ"
    st.metric(label=label, value=value)
    if tooltip:
        st.caption(tooltip)


def table_with_downloads(df, title: str, key: str):
    """Renders a dataframe and two download buttons (Excel, JPG)."""
    st.markdown(f"**{title}**")
    st.dataframe(df, use_container_width=True)
    footer = footer_text({"scope": key}, "current", "active", "just now")
    st.download_button(
        "Download Excel",
        data=df_to_xlsx_bytes(df, title, footer),
        file_name=f"{key}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{key}_xlsx",
    )
    st.download_button(
        "Download JPG",
        data=df_to_jpg_bytes(df, title, footer),
        file_name=f"{key}.jpg",
        mime="image/jpeg",
        key=f"{key}_jpg",
    )
