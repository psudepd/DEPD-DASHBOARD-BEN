import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

"""DEPD Executive Analytics dashboard — local entry point."""
import streamlit as st

from src.ui.components import kpi_card, table_with_downloads
from src.ui.state import get_filtered_dataframe, load_data
from src.kpi.aggregate import aggregate_reach, breakdown
from src.ui.pages.executive import render as render_executive
from src.ui.pages.breakdowns import render as render_breakdowns
from src.ui.pages.map import render as render_map
from src.ui.state import get_filtered_dataframe, load_data

st.set_page_config(page_title="DEPD Dashboard", layout="wide")

st.title("DEPD Executive Analytics")
st.caption("SYNTHETIC TEST DATA — demonstrating the pipeline, not real figures")

# Sidebar navigation (stub — only the Executive page is implemented for now)
page = st.sidebar.radio("Page", ["Executive Overview", "Breakdowns", "Map"])

# Role stub (Phase 6 will replace with real auth)
role = st.sidebar.selectbox("Role", ["viewer", "admin"])

# Filter bar
all_df = load_data()
divisions = ["All"] + sorted(all_df["division"].dropna().unique().tolist())
districts = ["All"] + sorted(all_df["district"].dropna().unique().tolist())
services = ["All"] + sorted(all_df["facility_type"].dropna().unique().tolist())

c1, c2, c3, c4 = st.columns(4)
division = c1.selectbox("Division", divisions)
district = c2.selectbox("District", districts)
service = c3.selectbox("Service type", services)
basis = c4.radio("Basis", ["active", "cumulative"], horizontal=True)

filters = {}
if division != "All":
    filters["division"] = division
if district != "All":
    filters["district"] = district
if service != "All":
    filters["service_type"] = service

df = get_filtered_dataframe(basis=basis, **filters)

# Show active filter chips
chip_text = " · ".join(f"{k}={v}" for k, v in filters.items()) or "All Sindh"
st.caption(f"Filters: {chip_text} · Basis: {basis}")

# Page: Executive Overview
if page == "Executive Overview":
    render_executive(df, basis)

# Page: Breakdowns
elif page == "Breakdowns":
    render_breakdowns(df, basis)

# Page: Map
elif page == "Map":
    render_map(df, basis)
