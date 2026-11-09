import io, httpx, pandas as pd, pytest
from src.ingest import kobo_live as k

def _xlsx(cols):
    b = io.BytesIO(); pd.DataFrame([{c: 1 for c in cols}]).to_excel(b, index=False); return b.getvalue()

def _t(content, status=200):
    return httpx.MockTransport(lambda req: httpx.Response(status, content=content))

def test_load_and_strip():
    cols = k.REQUIRED_COLUMNS + ['contact_name', 's_pic_1']
    g, r = k.load_live('https://x/export.xlsx', 'T', transport=_t(_xlsx(cols)))
    assert 'contact_name' not in g.columns and 'contact_name' in r.columns

def test_schema_error():
    with pytest.raises(k.KoboSchemaError):
        k.parse_export(_xlsx(['facility_type']))

def test_failure_does_not_leak_token(monkeypatch):
    monkeypatch.setattr(k.time, 'sleep', lambda s: None)
    with pytest.raises(RuntimeError) as e:
        k.fetch_bytes('https://x/e.xlsx', 'SECRET', retries=2, transport=_t(b'no', 403))
    assert 'SECRET' not in str(e.value)
