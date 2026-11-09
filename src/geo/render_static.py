"""Static (server-rendered) Sindh map JPG renderer (Phase 4).

geopandas and matplotlib are imported INSIDE the function (not at module
top) as the ~1 GB RAM workaround for Streamlit Cloud. Renders a JPG of the
full Sindh extent regardless of zoom/pan/selection.
"""
from __future__ import annotations

import io

from src.export.exporters import sindh_extent
from src.geo.boundaries import MissingBoundariesError


def render_static_jpg(boundaries: dict, width_px: int = 1200) -> bytes:
    """Render a JPG of the complete Sindh extent.

    Returns JPEG bytes. Raises MissingBoundariesError if boundaries is None.
    """
    if boundaries is None:
        raise MissingBoundariesError(
            "boundaries is None — cannot render static map without a boundary GeoJSON"
        )

    # Heavy imports inside the function (Streamlit Cloud RAM workaround).
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    gdf = gpd.GeoDataFrame.from_features(boundaries)
    minx, miny, maxx, maxy = gdf.total_bounds
    extent = sindh_extent((minx, miny, maxx, maxy))

    fig_h = max(6.0, width_px / 100.0 * (extent[3] - extent[1]) / max((extent[2] - extent[0]), 1e-9))
    fig, ax = plt.subplots(figsize=(width_px / 100.0, fig_h), dpi=100)
    gdf.plot(ax=ax, color="#EEF1F4", edgecolor="#E3E8ED", linewidth=0.6)
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    fig.tight_layout(pad=0.1)

    buf = io.BytesIO()
    fig.savefig(buf, format="jpg", dpi=150, bbox_inches="tight", pil_kwargs={"quality": 90})
    plt.close(fig)
    return buf.getvalue()
