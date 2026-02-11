from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from .common import load_table, detect_group_column, normalize_output_dir
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "facet", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    group_col = detect_group_column(df)
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if not group_col or not num_cols:
        return {"module": "viz_facet_grid", "status": "skipped", "message": "missing group/numeric"}
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    groups = df[group_col].dropna().unique().tolist()[:4]
    fig, axes = plt.subplots(1, len(groups), figsize=(4 * len(groups), 3), squeeze=False)
    for idx, g in enumerate(groups):
        subset = df[df[group_col] == g]
        axes[0, idx].hist(subset[num_cols[0]].dropna())
        axes[0, idx].set_title(str(g))
    path = out_dir / "facet_grid.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_facet_grid", "status": "ok", "output": str(path)}
