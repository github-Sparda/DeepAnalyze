from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

from .common import load_table, numeric_columns, normalize_output_dir
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "scatter", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    cols = numeric_columns(df)[:2]
    if len(cols) < 2:
        return {"module": "viz_multivariate", "status": "skipped", "message": "not enough numeric columns"}
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots()
    sns.scatterplot(x=df[cols[0]], y=df[cols[1]], ax=ax, s=10)
    ax.set_title(f"Scatter: {cols[0]} vs {cols[1]}")
    path = out_dir / "scatter.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_multivariate", "status": "ok", "output": str(path)}
