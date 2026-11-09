"""Tests for the extended live loader (src/ingest/kobo_live.py)."""
import io
import tempfile

import httpx
import pandas as pd
import pytest

import src.ingest.kobo_live as k


def _xlsx(cols):
    b = io.BytesIO()
    pd.DataFrame([{c: 1 for c in cols}]).to_excel(b, index=False)
    return b.getvalue()


def _t(content, status=200):
    return httpx.MockTransport(lambda req: httpx.Response(status, content=content))


def _isolated_cache(monkeypatch, tmp_path):
    """Point the loader at a fresh temp cache dir so tests don't interfere."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(k, "CACHE_DIR", str(cache_dir))


def test_load_live_returns_two_values_backward_compatible(tmp_path, monkeypatch):
    _isolated_cache(monkeypatch, tmp_path)
    cols = k.REQUIRED_COLUMNS + ["w_total"]
    g, r = k.load_live("https://x/e.xlsx", "T", transport=_t(_xlsx(cols)))
    assert isinstance(g, pd.DataFrame)
    assert isinstance(r, pd.DataFrame)


def test_load_live_full_returns_status(tmp_path, monkeypatch):
    _isolated_cache(monkeypatch, tmp_path)
    cols = k.REQUIRED_COLUMNS + ["w_total"]
    g, r, status = k.load_live_full("https://x/e.xlsx", "T", transport=_t(_xlsx(cols)))
    assert isinstance(status, dict)
    for key in ["fresh", "stale", "schema_ok", "last_refreshed", "missing_required", "unknown", "warning"]:
        assert key in status
    assert status["fresh"] is True
    assert status["schema_ok"] is True


def test_schema_error_on_missing_required(tmp_path, monkeypatch):
    _isolated_cache(monkeypatch, tmp_path)
    with pytest.raises(k.KoboSchemaError):
        k.load_live_full("https://x/e.xlsx", "T", transport=_t(_xlsx(["facility_type"])))


def test_unknown_columns_warned(tmp_path, monkeypatch):
    _isolated_cache(monkeypatch, tmp_path)
    cols = k.REQUIRED_COLUMNS + ["w_total", "weird_new_column_xyz"]
    g, r, status = k.load_live_full("https://x/e.xlsx", "T", transport=_t(_xlsx(cols)))
    assert "weird_new_column_xyz" in status["unknown"]
    assert status["warning"] is not None


def test_stale_fallback_when_kobo_unreachable(tmp_path, monkeypatch):
    _isolated_cache(monkeypatch, tmp_path)
    # First, a successful load to populate the cache.
    good = k.REQUIRED_COLUMNS + ["w_total"]
    k.load_live_full("https://x/e.xlsx", "T", transport=_t(_xlsx(good)))
    # Now make Kobo unreachable; should fall back to stale cache.
    monkeypatch.setattr(k.time, "sleep", lambda s: None)
    g, r, status = k.load_live_full("https://x/e.xlsx", "T", transport=_t(b"no", 403))
    assert status["stale"] is True
    assert isinstance(g, pd.DataFrame)


def test_failure_does_not_leak_token(monkeypatch):
    monkeypatch.setattr(k.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError) as e:
        k.fetch_bytes("https://x/e.xlsx", "SECRET", retries=1, transport=_t(b"no", 403))
    assert "SECRET" not in str(e.value)
