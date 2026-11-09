"""Sindh district boundary loading and validation (Phase 4).

Loads data/boundaries/sindh_districts.geojson if present. Never invents
polygons. Validates district names against data/choices.csv (districts list)
and raises a clear error naming any mismatch.
"""
from __future__ import annotations

import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
BOUNDARY_PATH = os.path.join(PROJECT_ROOT, "data", "boundaries", "sindh_districts.geojson")
CHOICES_PATH = os.path.join(PROJECT_ROOT, "data", "choices.csv")


class MissingBoundariesError(FileNotFoundError):
    """Raised when boundary GeoJSON is present but invalid."""


def _choices_districts() -> set:
    df = pd.read_csv(CHOICES_PATH)
    dist = df[df["list_name"] == "districts"]
    return {str(n).strip() for n in dist["name"].dropna()}


def load_boundaries(path: str = BOUNDARY_PATH):
    """Load the Sindh district boundary GeoJSON.

    Returns (geojson_dict, ok_flag):
      - (None, False) when the file does not exist (caller renders fallback).
      - (geojson, True) when loaded and district names validate against
        data/choices.csv.

    Raises MissingBoundariesError if the file exists but its district names
    do not match the choices.csv districts list (mismatch named).
    """
    if not os.path.exists(path):
        return None, False
    with open(path, encoding="utf-8") as fh:
        gj = json.load(fh)

    gj_districts = set()
    for feature in gj.get("features", []):
        props = feature.get("properties", {}) or {}
        name = (
            props.get("district_name")
            or props.get("name")
            or props.get("DISTRICT")
            or props.get("district")
        )
        if name is not None:
            gj_districts.add(str(name).strip())

    expected = _choices_districts()
    missing = expected - gj_districts
    extra = gj_districts - expected
    mismatched = sorted(missing | extra)
    if mismatched:
        raise MissingBoundariesError(
            "District names in sindh_districts.geojson do not match the "
            "data/choices.csv districts list. Mismatched districts: "
            + ", ".join(mismatched)
        )
    return gj, True


def boundaries_available() -> bool:
    gj, ok = load_boundaries()
    return ok
