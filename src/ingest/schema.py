"""XLSForm schema loader for the DEPD beneficiary form.

Loads the survey, choices and settings sheets from data/depd_form_latest.xlsx
and exposes canonical field names, types, labels and choice lists.  Also
validates a live Kobo export against docs/field_dictionary.csv.

The XLSForm is the source of truth for the form schema; the field dictionary is
a documentation snapshot.  Any column in the live export that is not in the
dictionary is ignored with a warning (never breaks the load).
"""
from __future__ import annotations

import csv
import functools
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import openpyxl

logger = logging.getLogger(__name__)

DEFAULT_XLSX_PATH = os.environ.get(
    "DEPD_FORM_XLSX",
    str(Path(__file__).resolve().parents[2] / "data" / "depd_form_latest.xlsx"),
)
DEFAULT_DICTIONARY_PATH = os.environ.get(
    "DEPD_FIELD_DICTIONARY",
    str(Path(__file__).resolve().parents[2] / "docs" / "field_dictionary.csv"),
)

RESTRICTED_PREFIXES = (
    "contact_name",
    "contact_info",
    "officer_designation",
    "signature",
    "s_pic_",
    "s_story",
)


@dataclass
class SurveyField:
    """A single row from the XLSForm survey sheet."""
    type: str
    name: str
    label: str = ""
    hint: str = ""
    relevant: str = ""
    choice_list: str = ""
    aggregation_rule: str = ""
    unit: str = ""


@dataclass
class XlsFormSchema:
    """Parsed XLSForm."""
    id_string: str = ""
    version: str = ""
    survey: list = field(default_factory=list)
    choices: dict = field(default_factory=dict)
    fields_by_name: dict = field(default_factory=dict)
    select_multiples: list = field(default_factory=list)
    select_ones: list = field(default_factory=list)

    @property
    def field_names(self) -> list:
        return [f.name for f in self.survey if f.name]


def _col_letter_to_index(ref: str) -> int:
    """Convert an Excel column reference (e.g. 'AA') to a 1-based index."""
    idx = 0
    for ch in ref:
        idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx


@functools.lru_cache(maxsize=1)
def load_xlsx_form(path: str = DEFAULT_XLSX_PATH) -> XlsFormSchema:
    """Load an XLSForm from an XLSX workbook (survey / choices / settings)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    schema = XlsFormSchema()

    if "settings" in wb.sheetnames:
        ws = wb["settings"]
        rows = list(ws.iter_rows(values_only=True))
        # The settings sheet has no header row: row 1 holds the keys
        # (id_string, version, ...) and row 2 holds their values.
        if len(rows) >= 2:
            keys = [str(c).strip() if c is not None else "" for c in rows[0]]
            vals = [str(c).strip() if c is not None else "" for c in rows[1]]
            settings = dict(zip(keys, vals))
            schema.id_string = settings.get("id_string", "")
            schema.version = settings.get("version", "")
            logger.info("Loaded XLSForm id_string=%s version=%s", schema.id_string, schema.version)

    if "survey" in wb.sheetnames:
        ws = wb["survey"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(c).strip() if c is not None else "" for c in rows[0]]
            for row in rows[1:]:
                if not row or all(c is None for c in row):
                    continue
                values = dict(zip(header, row))
                name = str(values.get("name", "")).strip()
                if not name:
                    continue
                ftype = str(values.get("type", "")).strip()
                label = str(values.get("label", "")).strip()
                hint = str(values.get("hint", "")).strip()
                relevant = str(values.get("relevant", "")).strip()
                choice_list = ""
                if ftype.startswith(("select_one ", "select_multiple ")):
                    choice_list = ftype.split(None, 1)[1].strip()
                sf = SurveyField(
                    type=ftype,
                    name=name,
                    label=label,
                    hint=hint,
                    relevant=relevant,
                    choice_list=choice_list,
                )
                schema.survey.append(sf)
                schema.fields_by_name[name] = sf
                if ftype.startswith("select_multiple "):
                    schema.select_multiples.append(name)
                elif ftype.startswith("select_one "):
                    schema.select_ones.append(name)

    if "choices" in wb.sheetnames:
        ws = wb["choices"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(c).strip() if c is not None else "" for c in rows[0]]
            for row in rows[1:]:
                if not row or all(c is None for c in row):
                    continue
                values = dict(zip(header, row))
                list_name = str(values.get("list_name", "")).strip()
                name = str(values.get("name", "")).strip()
                label = str(values.get("label", "")).strip()
                if not list_name or not name:
                    continue
                schema.choices.setdefault(list_name, []).append(
                    {"name": name, "label": label}
                )

    return schema


@functools.lru_cache(maxsize=1)
def load_dictionary(path: str = DEFAULT_DICTIONARY_PATH) -> dict:
    """Load docs/field_dictionary.csv keyed by field name.

    Returns: field_name -> {section, type, label, choice_list, unit,
    aggregation_rule, relevant_when}.
    """
    dictionary: dict = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("field") or "").strip()
            if not name:
                continue
            dictionary[name] = {
                "section": (row.get("section") or "").strip(),
                "type": (row.get("type") or "").strip(),
                "label": (row.get("label") or "").strip(),
                "choice_list": (row.get("choice_list") or "").strip(),
                "unit": (row.get("unit") or "").strip(),
                "aggregation_rule": (row.get("aggregation_rule") or "").strip(),
                "relevant_when": (row.get("relevant_when") or "").strip(),
            }
    return dictionary


def validate_export_columns(
    export_columns: list,
    schema: XlsFormSchema,
    dictionary: dict,
    required: Optional[list] = None,
) -> dict:
    """Compare live export columns against the schema + dictionary.

    The hard failure is based on `required` (the columns the loader cannot
    work without), not on every dictionary field.  Dictionary fields absent
    from the export are reported separately as informational (they may be
    optional or select_multiple expansions).

    Returns a dict with keys:
      - 'missing_required': hard-required columns absent from the export
      - 'missing_dictionary': dictionary fields absent from the export (info)
      - 'unknown': export columns not in the dictionary (ignored, warned)
      - 'select_multiples_expanded': select_multiple 0/1 expansions detected
    """
    if required is None:
        required = []
    export_set = set(export_columns)
    dict_fields = set(dictionary.keys())

    missing_required = sorted(set(required) - export_set)
    missing_dictionary = sorted(dict_fields - export_set)
    # Kobo system columns (start with '_') are known metadata; never flag them unknown.
    unknown = sorted(c for c in export_set - dict_fields if not c.startswith("_"))

    expanded = []
    for mf_name in schema.select_multiples:
        sf = schema.fields_by_name.get(mf_name)
        if sf is None:
            continue
        for choice in schema.choices.get(sf.choice_list, []):
            col = f"{mf_name}_{choice['name']}"
            if col in export_set and col not in dict_fields:
                expanded.append(col)

    return {
        "missing_required": missing_required,
        "missing_dictionary": missing_dictionary,
        "unknown": [c for c in unknown if c not in set(expanded)],
        "select_multiples_expanded": expanded,
    }


def required_fields_from_dictionary(dictionary: dict) -> list:
    """Fields that must be present in every export (hard-required for KPIs)."""
    return [
        "facility_type",
        "facility_name",
        "district",
        "rp_end",
        "_submission_time",
        "w_total",
    ]

