"""Reconciliation tests for the Breakdowns page (Phase 3C).

For three filter combinations, the Direct grand total must reconcile across
the service, division and district breakdown tables AND against
aggregate_reach() — within ±0.1.
"""
from src.kpi.aggregate import aggregate_reach, breakdown
from src.ui.state import get_filtered_dataframe

FILTERS = [
    {},
    {"division": "sukkur"},
    {"service_type": "gov_se"},
]


def _close(a, b, tol=0.1):
    return abs(a - b) <= tol


def test_breakdown_reconciles_no_filter():
    df = get_filtered_dataframe(basis="active")
    a = float(breakdown(df, "service")["direct"].sum())
    b = float(breakdown(df, "division")["direct"].sum())
    c = float(breakdown(df, "district")["direct"].sum())
    r = float(aggregate_reach(df)["direct"])
    assert _close(a, r), f"service {a} != reach {r}"
    assert _close(b, r), f"division {b} != reach {r}"
    assert _close(c, r), f"district {c} != reach {r}"


def test_breakdown_reconciles_division_filter():
    df = get_filtered_dataframe(basis="active", division="sukkur")
    a = float(breakdown(df, "service")["direct"].sum())
    b = float(breakdown(df, "division")["direct"].sum())
    c = float(breakdown(df, "district")["direct"].sum())
    r = float(aggregate_reach(df)["direct"])
    assert _close(a, r), f"service {a} != reach {r}"
    assert _close(b, r), f"division {b} != reach {r}"
    assert _close(c, r), f"district {c} != reach {r}"


def test_breakdown_reconciles_service_filter():
    df = get_filtered_dataframe(basis="active", service_type="gov_se")
    a = float(breakdown(df, "service")["direct"].sum())
    b = float(breakdown(df, "division")["direct"].sum())
    c = float(breakdown(df, "district")["direct"].sum())
    r = float(aggregate_reach(df)["direct"])
    assert _close(a, r), f"service {a} != reach {r}"
    assert _close(b, r), f"division {b} != reach {r}"
    assert _close(c, r), f"district {c} != reach {r}"


def test_breakdown_reconciles_cumulative_basis():
    df = get_filtered_dataframe(basis="cumulative")
    a = float(breakdown(df, "service")["direct"].sum())
    b = float(breakdown(df, "division")["direct"].sum())
    c = float(breakdown(df, "district")["direct"].sum())
    r = float(aggregate_reach(df)["direct"])
    assert _close(a, r), f"service {a} != reach {r}"
    assert _close(b, r), f"division {b} != reach {r}"
    assert _close(c, r), f"district {c} != reach {r}"
