from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import load_table, write_json, normalize_output_dir
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "volcano", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    if "p_value" in df.columns and "mean_diff" in df.columns:
        x = df["mean_diff"].fillna(0)
        y = -np.log10(df["p_value"].replace(0, np.nan)).fillna(0)
    else:
        x = np.arange(len(df))
        y = np.zeros_like(x, dtype=float)
    fig, ax = plt.subplots()
    ax.scatter(x, y, s=10, alpha=0.7)
    ax.set_xlabel("Effect")
    ax.set_ylabel("-log10(p)")
    ax.set_title("Volcano Plot" if mode == "volcano" else "Manhattan Plot")
    path = out_dir / f"{mode}_plot.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    write_json(Path(out_dir) / f"{mode}_plot.json", {"path": str(path)})
    return {"module": "viz_manhattan_volcano", "status": "ok", "output": str(path)}
