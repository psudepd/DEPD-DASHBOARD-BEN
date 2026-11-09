"""Device totals per facility/period from Section R (recipients) or Section P5 (NOWPDP assistive devices).

Never adds P5 and R for the same row.
"""
from __future__ import annotations

import pandas as pd


def _num(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, float) and pd.isna(v):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def device_totals(df) -> pd.DataFrame:
    """Return a DataFrame with one row per facility/period.

    Columns: facility_key, facility_type, wheelchair, crutches_walkers,
    tricycle, prosthesis, orthosis, hearing, vision, other, source,
    double_count_risk.

    Rules:
      * nowpdp: use p5_* columns only, source="P5". If r_given=="yes" and
        any r_* device field > 0, double_count_risk=True (still P5 only).
      * other facility_type with r_given=="yes": use R fields, source="R".
      * other facility_type with r_given!="yes": all quantities 0,
        source="none".
    """
    if isinstance(df, (dict, pd.Series)):
        df = pd.DataFrame([df])

    rows = []
    for _, row in df.iterrows():
        rec = {
            "facility_key": row.get("_id"),
            "facility_type": row.get("facility_type"),
            "wheelchair": None,
            "crutches_walkers": None,
            "tricycle": None,
            "prosthesis": None,
            "orthosis": None,
            "hearing": None,
            "vision": None,
            "other": None,
            "source": None,
            "double_count_risk": False,
        }

        ftype = row.get("facility_type")
        r_given = str(row.get("r_given", "")).strip().lower()

        if ftype == "nowpdp":
            rec["wheelchair"] = _num(row.get("p5_wheelchair"))
            rec["crutches_walkers"] = _num(row.get("p5_crutches"))
            rec["tricycle"] = _num(row.get("p5_tricycle"))
            rec["prosthesis"] = None
            rec["orthosis"] = None
            rec["hearing"] = _num(row.get("p5_hearing"))
            rec["vision"] = _num(row.get("p5_cane"))
            rec["other"] = _num(row.get("p5_other"))
            rec["source"] = "P5"
            if r_given == "yes":
                r_fields = (
                    "r_wheelchair", "r_crutches", "r_walker", "r_limb",
                    "r_orthosis", "r_hearing", "r_spectacles", "r_dev_other",
                )
                if any(_num(row.get(c)) > 0 for c in r_fields):
                    rec["double_count_risk"] = True
        elif r_given == "yes":
            rec["wheelchair"] = _num(row.get("r_wheelchair"))
            rec["crutches_walkers"] = _num(row.get("r_crutches")) + _num(
                row.get("r_walker")
            )
            rec["tricycle"] = None
            rec["prosthesis"] = _num(row.get("r_limb"))
            rec["orthosis"] = _num(row.get("r_orthosis"))
            rec["hearing"] = _num(row.get("r_hearing"))
            rec["vision"] = _num(row.get("r_spectacles"))
            rec["other"] = _num(row.get("r_dev_other"))
            rec["source"] = "R"
        else:
            for key in (
                "wheelchair", "crutches_walkers", "tricycle", "prosthesis",
                "orthosis", "hearing", "vision", "other",
            ):
                rec[key] = 0
            rec["source"] = "none"

        rows.append(rec)

    return pd.DataFrame(rows)
