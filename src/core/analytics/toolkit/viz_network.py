from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from .common import load_table, normalize_output_dir, write_json
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "network", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    data = df.select_dtypes(include="number")
    if data.empty:
        return {"module": "viz_network", "status": "skipped", "message": "no numeric data"}
    corr = data.corr().fillna(0).to_numpy()
    n = corr.shape[0]
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    coords = np.c_[np.cos(angles), np.sin(angles)]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(coords[:, 0], coords[:, 1], s=30, color="#4C78A8")
    for i in range(n):
        for j in range(i + 1, n):
            if abs(corr[i, j]) > 0.5:
                color = "#4C78A8" if corr[i, j] >= 0 else "#E45756"
                ax.plot([coords[i, 0], coords[j, 0]], [coords[i, 1], coords[j, 1]], alpha=0.35, color=color)
    ax.set_title("Correlation Network")
    ax.axis("off")
    legend_items = [
        Line2D([0], [0], color="#4C78A8", lw=2, label="Positive corr (>0.5)"),
        Line2D([0], [0], color="#E45756", lw=2, label="Negative corr (<-0.5)"),
    ]
    ax.legend(handles=legend_items, frameon=True, loc="best")
    path = out_dir / "network.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    write_json(
        Path(out_dir) / "network.png.json",
        {
            "path": str(path),
            "threshold": 0.5,
            "type": "correlation_network",
            "node_count": int(n),
        },
    )
    return {"module": "viz_network", "status": "ok", "output": str(path)}
