from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

from .common import load_table, numeric_columns, normalize_output_dir, write_json
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "scatter", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    cols = numeric_columns(df)
    if len(cols) < 2:
        return {"module": "viz_multivariate", "status": "skipped", "message": "not enough numeric columns"}
    corr = df[cols].corr().fillna(0).to_numpy()
    np.fill_diagonal(corr, 0)
    max_idx = divmod(np.abs(corr).argmax(), corr.shape[1])
    x_col = cols[max_idx[0]]
    y_col = cols[max_idx[1]]
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots()
    sns.scatterplot(x=df[x_col], y=df[y_col], ax=ax, s=10)
    ax.set_title(f"Scatter: {x_col} vs {y_col}")
    path = out_dir / "scatter.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    write_json(
        Path(out_dir) / "scatter.png.json",
        {
            "path": str(path),
            "type": "scatter",
            "x": x_col,
            "y": y_col,
            "abs_correlation": float(abs(corr[max_idx])),
        },
    )
    return {"module": "viz_multivariate", "status": "ok", "output": str(path)}
