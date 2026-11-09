"""Reference exporters: every table -> Excel and JPG; map -> JPG of the complete Sindh extent.

Rules (see docs/00_specification.md Section 8):
- Table exports use the SAME filtered dataframe that is on screen (no extra columns, no restricted fields).
- Every export carries: title, active filters, reporting period, Active/Cumulative basis, source, last-refreshed time (Asia/Karachi).
- Map export ALWAYS uses the full Sindh extent (the total bounds of the approved boundary file plus a margin),
  never the current zoom or pan, and shows the filtered markers, legend and the same footer.
"""
from __future__ import annotations
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def footer_text(filters: dict, period: str, basis: str, refreshed: str) -> str:
    f = '; '.join(f'{k}: {v}' for k, v in filters.items()) or 'All Sindh'
    return f'Filters: {f} | Period: {period} | Basis: {basis} | Source: DEPD Kobo reports | Refreshed: {refreshed} (Asia/Karachi)'


def df_to_xlsx_bytes(df: pd.DataFrame, title: str, footer: str, sheet: str = 'Data') -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as xw:
        df.to_excel(xw, sheet_name=sheet[:31], index=False, startrow=2)
        ws = xw.sheets[sheet[:31]]
        bold = xw.book.add_format({'bold': True, 'font_size': 13})
        ws.write(0, 0, title, bold)
        ws.write(1, 0, footer)
        for i, c in enumerate(df.columns):
            width = min(max(len(str(c)), int(df[c].astype(str).str.len().max() or 0)) + 2, 50)
            ws.set_column(i, i, width)
        ws.freeze_panes(3, 0)
    return buf.getvalue()


def df_to_jpg_bytes(df: pd.DataFrame, title: str, footer: str, max_rows: int = 60, dpi: int = 200) -> bytes:
    d = df.head(max_rows)
    h = max(2.5, 0.32 * (len(d) + 4))
    fig, ax = plt.subplots(figsize=(max(8, 1.3 * len(d.columns)), h))
    ax.axis('off')
    ax.set_title(title, loc='left', fontsize=12, fontweight='bold', color='#18345A')
    tbl = ax.table(cellText=d.astype(str).values, colLabels=list(d.columns), loc='upper left', cellLoc='left')
    tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.auto_set_column_width(list(range(len(d.columns))))
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor('#18345A'); cell.get_text().set_color('white')
    note = footer + (f' | Showing first {max_rows} of {len(df)} rows; download Excel for all rows' if len(df) > max_rows else '')
    fig.text(0.01, 0.01, note, fontsize=6, color='#66758C')
    buf = io.BytesIO(); fig.savefig(buf, format='jpg', dpi=dpi, bbox_inches='tight', pil_kwargs={'quality': 92}); plt.close(fig)
    return buf.getvalue()


def sindh_extent(total_bounds, margin: float = 0.05):
    """total_bounds = (minx, miny, maxx, maxy) of the approved Sindh boundary file. Returns padded extent."""
    minx, miny, maxx, maxy = total_bounds
    dx, dy = (maxx - minx) * margin, (maxy - miny) * margin
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)
