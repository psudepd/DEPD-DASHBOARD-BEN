"""Division mapping helpers: prefer district->division mapping over submitted division."""
from __future__ import annotations

import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
DISTRICT_DIVISION_PATH = os.path.join(PROJECT_ROOT, "data", "district_division.csv")


def normalise(x):
    """Lowercase, strip, replace spaces and hyphens with '_'."""
    if x is None:
        return ""
    s = str(x).strip().lower()
    s = s.replace(" ", "_").replace("-", "_")
    return s


_DIVISION_MAP: dict = {}


def _load_division_map() -> dict:
    df = pd.read_csv(DISTRICT_DIVISION_PATH)
    m: dict = {}
    for _, row in df.iterrows():
        m[normalise(row["district_code"])] = str(row["division_code"]).strip()
    return m


DIVISION_MAP = _load_division_map()


def district_to_division(district_code):
    """Return the division_code for a district_code, or None if unmapped."""
    return DIVISION_MAP.get(normalise(district_code))


def division_of_row(row):
    """Prefer the district mapping over the submitted division column.

    Returns the mapped division_code, or None if unmapped.  Never falls back
    to the submitted division.
    """
    return district_to_division(row.get("district"))


def add_division_columns(df):
    """Return df with two new columns:
       division_mapped   = from district (via district_to_division)
       division_mismatch = True if submitted division is present and differs
                           from division_mapped (case-insensitive, underscored)
    """
    df = df.copy()
    df["division_mapped"] = df["district"].apply(district_to_division)
    submitted = df.get("division")
    if submitted is not None:
        sub = submitted.fillna("").astype(str).str.lower().str.replace(" ", "_")
        mapped = df["division_mapped"].fillna("").astype(str)
        df["division_mismatch"] = sub != mapped
    else:
        df["division_mismatch"] = False
    return df
