import io, pandas as pd
from openpyxl import load_workbook
from PIL import Image
from src.export import exporters as e

DF = pd.DataFrame({'Service type': ['rcph', 'carts'], 'Organisation': ['A', 'B'], 'Direct': [10, 20]})

def test_xlsx_has_title_filters_and_data():
    b = e.df_to_xlsx_bytes(DF, 'Summary sheet', e.footer_text({'Region': 'Sukkur'}, '2026-11', 'Active', '17:00'))
    ws = load_workbook(io.BytesIO(b)).active
    assert ws['A1'].value == 'Summary sheet' and 'Region: Sukkur' in ws['A2'].value
    assert ws['A3'].value == 'Service type' and ws['C5'].value == 20

def test_jpg_is_valid_image():
    im = Image.open(io.BytesIO(e.df_to_jpg_bytes(DF, 'Summary sheet', 'footer')))
    assert im.format == 'JPEG' and im.size[0] > 200

def test_sindh_extent_is_padded_and_ignores_zoom():
    x0, y0, x1, y1 = e.sindh_extent((0, 0, 10, 10), 0.1)
    assert (x0, y0, x1, y1) == (-1, -1, 11, 11)
