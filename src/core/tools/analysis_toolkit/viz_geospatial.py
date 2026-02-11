from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from .common import load_table, normalize_output_dir
from .viz_theme import apply_theme


def _detect_latlon(df):
    lat = None
    lon = None
    for col in df.columns:
        name = col.lower()
        if lat is None and (name == "lat" or name == "latitude"):
            lat = col
        if lon is None and (name == "lon" or name == "longitude"):
            lon = col
    return lat, lon


def run(input_path: str | Path, output_dir: str | Path, mode: str = "heatmap", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    lat, lon = _detect_latlon(df)
    if not lat or not lon:
        return {"module": "viz_geospatial", "status": "skipped", "message": "missing lat/lon"}
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots()
    ax.scatter(df[lon], df[lat], s=10, alpha=0.6)
    ax.set_title("Geospatial Scatter")
    path = out_dir / "geospatial.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_geospatial", "status": "ok", "output": str(path)}
