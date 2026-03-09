from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import load_table, normalize_output_dir
from .viz_theme import apply_theme
from .common import write_json


def run(input_path: str | Path, output_dir: str | Path, mode: str = "heatmap", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    if "correlation" in input_path.__str__():
        try:
            df = pd.read_csv(input_path)
            if "index" in df.columns:
                df = df.set_index("index")
        except Exception:
            pass
    data = df.select_dtypes(include="number")
    if data.empty:
        return {"module": "viz_heatmap_cluster", "status": "skipped", "message": "no numeric data"}
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(data.corr(), cmap="RdYlBu", vmin=-1, vmax=1)
    fig.colorbar(im, ax=ax)
    filename_mode = "clustermap" if mode == "clustermap" else mode
    ax.set_title("Heatmap" if mode == "heatmap" else "Clustered Heatmap")
    path = out_dir / f"{filename_mode}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    write_json(
        Path(out_dir) / f"{filename_mode}.png.json",
        {"path": str(path), "mode": mode, "type": "correlation_heatmap", "color_scale": "RdYlBu"},
    )
    return {"module": "viz_heatmap_cluster", "status": "ok", "output": str(path)}
