from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from .common import load_table, normalize_output_dir
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
    ax.scatter(coords[:, 0], coords[:, 1], s=30)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(corr[i, j]) > 0.5:
                ax.plot([coords[i, 0], coords[j, 0]], [coords[i, 1], coords[j, 1]], alpha=0.3)
    ax.set_title("Correlation Network")
    ax.axis("off")
    path = out_dir / "network.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_network", "status": "ok", "output": str(path)}
