"""Programme KPIs for the Phase 5 programme dashboards.

Reads field definitions from docs/field_dictionary.csv. Never sums across
units. Excludes regional_dir (office information only).
"""
from __future__ import annotations

import os

import pandas as pd

from src.kpi.resolver import num

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
FIELD_DICTIONARY_PATH = os.path.join(PROJECT_ROOT, "docs", "field_dictionary.csv")

PROGRAMME_PREFIXES = {
    "nowpdp": ("p_cum", "p1_", "p2_", "p3_", "p4_", "p5_"),
    "carts": ("v1_", "v2_", "v3_", "v4_", "v5_", "q_"),
    "deaf_reach": ("t_",),
    "sipmr": ("l_", "u_"),
    "inclusive": ("n_",),
}

V5_LABEL = "V5 Parent Training (parents are NOT disability beneficiaries)"


def _load_dictionary() -> pd.DataFrame:
    return pd.read_csv(FIELD_DICTIONARY_PATH, dtype=str)


def _matches_prefix(field: str, prefixes) -> bool:
    if field in prefixes:
        return True
    return any(field.startswith(p) for p in prefixes if p.endswith("_"))


def programme_kpis(df: pd.DataFrame, programme: str) -> pd.DataFrame:
    """One row per indicator for a programme cluster.

    Columns: indicator, label, value, unit, rule, source_field, null_state.
    """
    if programme not in PROGRAMME_PREFIXES:
        raise ValueError(f"unknown programme: {programme}")

    prefixes = PROGRAMME_PREFIXES[programme]
    dictionary = _load_dictionary()
    dict_map = {
        str(r["field"]).strip(): {
            "label": str(r["label"]).strip(),
            "unit": str(r["unit"]).strip(),
            "rule": str(r["aggregation_rule"]).strip(),
        }
        for _, r in dictionary.iterrows()
    }

    d = df.copy()
    if "facility_type" in d.columns:
        d = d[d["facility_type"].astype(str) != "regional_dir"].copy()

    rows = []
    for field, info in dict_map.items():
        if not _matches_prefix(field, prefixes):
            continue
        label = info["label"]
        unit = info["unit"]
        rule = info["rule"]

        if field.startswith("v5_"):
            label = V5_LABEL

        if rule == "":
            rows.append(
                {
                    "indicator": field,
                    "label": label,
                    "value": None,
                    "unit": unit,
                    "rule": rule,
                    "source_field": field,
                    "null_state": "Not collected",
                }
            )
            continue

        if field not in d.columns:
            rows.append(
                {
                    "indicator": field,
                    "label": label,
                    "value": None,
                    "unit": unit,
                    "rule": rule,
                    "source_field": field,
                    "null_state": "No data",
                }
            )
            continue

        values = d[field].apply(num).dropna()
        if values.empty:
            rows.append(
                {
                    "indicator": field,
                    "label": label,
                    "value": None,
                    "unit": unit,
                    "rule": rule,
                    "source_field": field,
                    "null_state": "No data",
                }
            )
            continue

        if rule in ("CUM", "SNAP") and "_submission_time" in d.columns and "facility_name" in d.columns:
            d2 = d.copy()
            d2["_st"] = pd.to_datetime(d2["_submission_time"], errors="coerce")
            idx = d2.groupby("facility_name")["_st"].idxmax()
            latest = d2.loc[idx]
            field_vals = latest[field].apply(num).dropna()
            value = float(field_vals.sum()) if len(field_vals) else None
        else:
            # FLOW -> sum across rows (also fallback for any other rule)
            value = float(values.sum())

        if value is None:
            null_state = "No data"
        elif value == 0:
            null_state = None
        else:
            null_state = None

        rows.append(
            {
                "indicator": field,
                "label": label,
                "value": value,
                "unit": unit,
                "rule": rule,
                "source_field": field,
                "null_state": null_state,
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["unit", "indicator"]).reset_index(drop=True)
    return out
