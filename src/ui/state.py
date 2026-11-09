"""UI state: load and filter the synthetic submissions dataframe.

Phase 3A stub — load_data() reads the local synthetic fixture.  Phase 3B adds
an env-based DATA_SOURCE switch (synthetic default; "live" uses kobo_live).
"""
from __future__ import annotations

import os

import pandas as pd

from src.kpi.aggregate import select_latest_per_facility
from src.kpi.geography import add_division_columns
from src.kpi.resolver import resolve_dataframe

DATA_SOURCE = os.environ.get("DEPD_DATA_SOURCE", "synthetic")


def load_data() -> pd.DataFrame:
    """Load submissions for now.

    DATA_SOURCE=synthetic (default) reads data/synthetic_submissions.csv.
    DATA_SOURCE=live reads from kobo_live.load_live().
    """
    if DATA_SOURCE == "live":
        from src.ingest.kobo_live import load_live

        return load_live()
    return pd.read_csv("data/synthetic_submissions.csv", dtype=object)


def get_filtered_dataframe(
    division=None,
    district=None,
    service_type=None,
    period=None,
    basis="active",
) -> pd.DataFrame:
    """Return the single filtered dataframe used by every page."""
    df = load_data()
    df = select_latest_per_facility(df)
    df = add_division_columns(df)
    df = resolve_dataframe(df, basis=basis)
    if division is not None:
        df = df[df["division_mapped"] == division]
    if district is not None:
        df = df[df["district"] == district]
    if service_type is not None:
        df = df[df["facility_type"] == service_type]
    if period is not None:
        df = df[df["rp_end"] == period]
    return df.reset_index(drop=True)
