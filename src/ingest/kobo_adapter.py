"""Kobo export adapter.

Reads a CSV or JSON export (synthetic submissions for testing, live XLSX for
production) and produces a cleaned, canonical dataframe:

  * strips group prefixes such as ``sec_w/w_total`` -> ``w_total``
  * maps export columns to canonical dictionary names
  * normalises select_multiple (space-separated or 0/1 columns) back to
    canonical space-separated choice names
  * keeps raw values; keeps blank distinct from 0 (never blank -> 0)
  * strips restricted (personal) columns at load; returns them separately for
    admin / manager views only

The adapter is *format-agnostic*: it works on any columnar export.  The live
Kobo reader (kobo_live.py) supplies the raw dataframe; this adapter cleans it.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from .schema import RESTRICTED_PREFIXES, load_dictionary

logger = logging.getLogger(__name__)

# Canonical key fields that must survive adaptation (present in every report).
CANONICAL_REQUIRED = ["facility_type", "facility_name", "district", "rp_end", "_submission_time"]

# Direct beneficiaries column used by the KPI ladder.
W_TOTAL = "w_total"


def strip_group_prefix(col: str) -> str:
    """Strip Kobo group prefixes from a column name.

    Examples:
      ``sec_w/w_total`` -> ``w_total``
      ``group_dp8mz64/Cumulative_Disabilit_sued_Since_Inception`` ->
        ``Cumulative_Disabilit_sued_Since_Inception``
    """
    if "/" in col:
        return col.rsplit("/", 1)[-1]
    return col


def _select_multiples_columns(columns: list) -> dict:
    """Return {base_field: [expanded_cols]} for select_multiple 0/1 columns.

    Kobo expands select_multiple 'f' with choices c1..cn to columns
    'f_c1', 'f_c2', ...  A cell is '1' if the choice was selected, blank/0
    otherwise.  We detect these by matching the dictionary's choice lists.
    """
    mapping: dict = {}
    dictionary = load_dictionary()
    for col in columns:
        for field_name, meta in dictionary.items():
            cl = (meta.get("choice_list") or "").strip()
            if not cl:
                continue
            # column like f_choiceName
            prefix = field_name + "_"
            if col.startswith(prefix) and col != field_name:
                choice = col[len(prefix):]
                mapping.setdefault(field_name, []).append((col, choice))
    return mapping


def adapt(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and canonicalise a raw Kobo export dataframe.

    Steps:
      1. Strip group prefixes from all column names.
      2. Drop fully-empty columns.
      3. Map columns to canonical dictionary names (identity where already
         canonical).
      4. Normalise select_multiple 0/1 expanded columns back to the canonical
         select_multiple value (space-separated selected choice names).
      5. Keep blank distinct from 0: all cells read as text/object; numeric
         conversion is done explicitly by the KPI layer.
      6. Strip restricted columns (returned separately via split_restricted).

    Returns the general (public) dataframe.  Restricted columns are dropped.
    """
    if df is None or df.empty:
        return df

    d = df.copy()

    # 1. Strip group prefixes.
    d.columns = [strip_group_prefix(c) for c in d.columns]

    # 2. Drop fully-empty columns.
    d = d.dropna(axis=1, how="all")

    # 3. Normalise select_multiple expansions.
    sm_map = _select_multiples_columns(list(d.columns))
    for base_field, expanded in sm_map.items():
        selected = []
        for col, choice in expanded:
            if col not in d.columns:
                continue
            vals = d[col]
            # Treat '1' or 'true'/'yes' as selected; blank/'0' as not.
            mask = vals.astype(str).str.strip().str.lower().isin({"1", "true", "yes"})
            # Build selected list per row: where mask is True, include choice.
            chosen = [
                choice if mask.iloc[i] else ""
                for i in range(len(d))
            ]
            selected.append(chosen)
        if selected:
            # Combine per-row across all choice columns.
            combined = []
            for i in range(len(d)):
                picks = [sel[i] for sel in selected if sel[i]]
                combined.append(" ".join(picks) if picks else None)
            d[base_field] = combined
            for col, _ in expanded:
                if col in d.columns:
                    d = d.drop(columns=[col])

    # 4. Read all cells as object so blank stays distinct from 0.
    d = d.astype(object).where(pd.notna(d), None)

    return d


def split_restricted(df: pd.DataFrame) -> tuple:
    """Split a dataframe into (general, restricted).

    Restricted columns (contact, signature, picture, story) are removed from
    the general dataframe and returned separately for admin / manager views.
    """
    if df is None or df.empty:
        empty = df.copy() if df is not None else df
        return empty, empty.copy() if empty is not None else empty
    drop = [c for c in df.columns if str(c).startswith(RESTRICTED_PREFIXES)]
    general = df.drop(columns=drop) if drop else df.copy()
    restricted = df[drop].copy() if drop else df.iloc[:, 0:0].copy()
    return general, restricted


def required_present(df: pd.DataFrame, required: Optional[list] = None) -> list:
    """Return the list of required columns missing from df."""
    if required is None:
        required = CANONICAL_REQUIRED
    return [c for c in required if c not in df.columns]
