"""Live reader for the Kobo export-settings XLSX URL (reference implementation).

Configuration comes ONLY from environment variables or Streamlit secrets:
  KOBO_EXPORT_URL   full export-settings data.xlsx URL
  KOBO_API_TOKEN    Kobo API token (omit only if the export allows anonymous access)
Never log the token. Never hard-code either value.

Extended (Phase 1): schema validation against docs/field_dictionary.csv,
15-minute caching with a stale marker, and a visible "Last refreshed" timestamp.
"""
from __future__ import annotations

import io
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from . import kobo_adapter
from .schema import (
    DEFAULT_DICTIONARY_PATH,
    DEFAULT_XLSX_PATH,
    load_dictionary,
    load_xlsx_form,
    validate_export_columns,
)

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ['facility_type', 'facility_name', 'district', 'rp_end', '_submission_time', 'w_total']
# Personal / restricted fields: removed from the general dataframe at load.
RESTRICTED_PREFIXES = ('contact_name', 'contact_info', 'officer_designation', 'signature', 's_pic_', 's_story')

# Cache defaults (overridable via env / secrets).
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', '900'))  # 15 minutes
CACHE_DIR = os.environ.get(
    'DEPD_CACHE_DIR', '/app/.cache' if os.path.exists('/app/.cache') else '.cache',
)

# Timezone for display.
try:
    import zoneinfo

    TZ = zoneinfo.ZoneInfo('Asia/Karachi')
except Exception:  # pragma: no cover - fallback if zoneinfo tzdata missing
    TZ = None


def _now_karachi() -> datetime:
    if TZ is not None:
        return datetime.now(TZ)
    return datetime.now(timezone.utc)


class KoboSchemaError(RuntimeError):
    pass


def _config(url=None, token=None):
    url = url or os.environ.get('KOBO_EXPORT_URL')
    token = token or os.environ.get('KOBO_API_TOKEN')
    if not url:
        raise RuntimeError('KOBO_EXPORT_URL is not set')
    return url, token


def fetch_bytes(url=None, token=None, timeout=120.0, retries=3, transport=None) -> bytes:
    url, token = _config(url, token)
    headers = {'Authorization': f'Token {token}'} if token else {}
    last = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, transport=transport) as c:
                r = c.get(url, headers=headers)
            if r.status_code == 200 and r.content[:2] == b'PK':   # xlsx is a zip
                return r.content
            last = f'HTTP {r.status_code}'
        except httpx.HTTPError as e:                                # never include headers
            last = type(e).__name__
        time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f'Kobo export download failed ({last})')


def parse_export(content: bytes) -> pd.DataFrame:
    # dtype=object keeps blank distinct from 0; convert numbers explicitly later.
    df = pd.read_excel(io.BytesIO(content), dtype=object)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KoboSchemaError(f'Export settings changed? Missing columns: {missing}')
    return df


def strip_restricted(df: pd.DataFrame):
    drop = [c for c in df.columns if str(c).startswith(RESTRICTED_PREFIXES)]
    return df.drop(columns=drop), df[drop].copy()   # (general, admin-only)


def _cache_path() -> Path:
    p = Path(CACHE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p / 'last_good_export.xlsx'


def _load_cached() -> pd.DataFrame | None:
    """Return the last good cached export as a dataframe, or None if absent."""
    cp = _cache_path()
    if not cp.exists():
        return None
    try:
        return pd.read_excel(cp, dtype=object)
    except Exception:
        return None


def _save_cache(df: pd.DataFrame) -> None:
    """Persist the last good export to the cache file."""
    cp = _cache_path()
    try:
        df.to_excel(cp, index=False)
    except Exception as e:  # cache write must never kill the app
        logger.warning('Could not write cache: %s', e)


def _status_path() -> Path:
    p = Path(CACHE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p / 'loader_status.json'


def save_status(status: dict) -> None:
    """Persist loader status (last_refreshed etc.) for the UI to read."""
    try:
        _status_path().write_text(json.dumps(status, default=str), encoding='utf-8')
    except Exception as e:  # status write must never kill the app
        logger.warning('Could not write loader status: %s', e)


def load_status() -> dict:
    """Return the persisted loader status, or a default empty status."""
    try:
        return json.loads(_status_path().read_text(encoding='utf-8'))
    except Exception:
        return {
            'fresh': False,
            'stale': False,
            'last_refreshed': None,
            'schema_ok': False,
            'missing_required': [],
            'unknown': [],
            'warning': None,
        }


def schema_ok(df: pd.DataFrame) -> tuple:
    """Validate a dataframe's columns against the field dictionary.

    Returns (ok, missing_required, unknown).
    ok is False only when a hard-required column is missing.
    """
    dictionary = load_dictionary(DEFAULT_DICTIONARY_PATH)
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)
    result = validate_export_columns(
        list(df.columns), schema, dictionary, required=REQUIRED_COLUMNS
    )
    missing_required = result['missing_required']
    ok = len(missing_required) == 0
    return ok, missing_required, result['unknown']


def _load_live_full(
    url=None,
    token=None,
    use_cache: bool = True,
    **kw,
):
    """Internal: load with full status. Returns (general_df, restricted_df, status)."""
    status = {
        'fresh': False,
        'stale': False,
        'last_refreshed': None,
        'schema_ok': False,
        'missing_required': [],
        'unknown': [],
        'warning': None,
    }

    dictionary = load_dictionary(DEFAULT_DICTIONARY_PATH)
    schema = load_xlsx_form(DEFAULT_XLSX_PATH)

    df = None
    try:
        content = fetch_bytes(url, token, **kw)
        df = parse_export(content)
        status['fresh'] = True
        status['last_refreshed'] = _now_karachi().isoformat()
        # Persist the good copy.
        _save_cache(df)
        save_status(status)
    except Exception as exc:  # Kobo unreachable -> fall back to cache
        status['warning'] = f'Kobo unreachable ({exc}); using last good cached copy (stale)'
        status['stale'] = True
        df = _load_cached()
        if df is None:
            raise
        status['last_refreshed'] = status.get('last_refreshed') or 'cached (unknown)'
        save_status(status)

    # Schema validation on every load.
    ok, missing, unknown = schema_ok(df)
    status['schema_ok'] = ok
    status['missing_required'] = missing
    status['unknown'] = unknown
    if unknown:
        status['warning'] = (
            (status['warning'] + '; ' if status['warning'] else '')
            + f'{len(unknown)} unknown column(s) ignored; listed in Data Quality'
        )
        logger.warning('Unknown export columns ignored: %s', unknown[:50])

    if not ok:
        raise KoboSchemaError(
            f'Export settings changed? Missing required columns: {missing}'
        )

    # Adapt: canonical mapping, select_multiple normalisation, blank != 0.
    general_raw, restricted = kobo_adapter.split_restricted(df)
    general = kobo_adapter.adapt(general_raw)

    # Re-check required columns after adaptation.
    missing_after = [c for c in REQUIRED_COLUMNS if c not in general.columns]
    if missing_after:
        raise KoboSchemaError(f'Export settings changed? Missing columns after adaptation: {missing_after}')

    save_status(status)
    return general, restricted, status


def load_live(url=None, token=None, **kw):
    """Load the live Kobo export (backward-compatible: returns 2 values).

    Returns (general_df, restricted_df).  For the full status dict use
    load_live_full().
    """
    general, restricted, _status = _load_live_full(url=url, token=token, **kw)
    return general, restricted


def load_live_full(url=None, token=None, **kw):
    """Load the live Kobo export with full status.

    Returns (general_df, restricted_df, status).
    """
    return _load_live_full(url=url, token=token, **kw)


def last_refreshed() -> str:
    """Return a human-readable 'Last refreshed' string (Asia/Karachi), or None."""
    st = load_status()
    return st.get('last_refreshed')


