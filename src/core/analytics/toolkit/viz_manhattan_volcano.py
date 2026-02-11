from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
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
        sig = df["p_value"].fillna(1.0) < 0.05
    else:
        x = np.arange(len(df))
        y = np.zeros_like(x, dtype=float)
        sig = np.zeros_like(x, dtype=bool)
    fig, ax = plt.subplots()
    colors = np.where(sig, "#D62728", "#9AA1A7")
    ax.scatter(x, y, s=12, alpha=0.7, c=colors)
    ax.set_xlabel("Effect")
    ax.set_ylabel("-log10(p)")
    ax.set_title("Volcano Plot" if mode == "volcano" else "Manhattan Plot")
    legend_items = [
        Line2D([0], [0], marker="o", color="w", label="p < 0.05", markerfacecolor="#D62728", markersize=6),
        Line2D([0], [0], marker="o", color="w", label="p ≥ 0.05", markerfacecolor="#9AA1A7", markersize=6),
    ]
    ax.legend(handles=legend_items, frameon=True, loc="best")
    path = out_dir / f"{mode}_plot.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    group_a = None
    group_b = None
    if "group_a" in df.columns:
        group_a = df["group_a"].iloc[0]
    if "group_b" in df.columns:
        group_b = df["group_b"].iloc[0]
    meta = {
        "path": str(path),
        "mode": mode,
        "x": "mean_diff",
        "y": "-log10(p)",
        "significance_threshold": 0.05,
        "group_a": group_a,
        "group_b": group_b,
    }
    write_json(Path(out_dir) / f"{mode}_plot.json", meta)
    write_json(Path(out_dir) / f"{mode}_plot.png.json", meta)
    return {"module": "viz_manhattan_volcano", "status": "ok", "output": str(path)}
