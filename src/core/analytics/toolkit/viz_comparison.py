from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

from .common import load_table, detect_group_column, numeric_columns, normalize_output_dir
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "box", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    group_col = detect_group_column(df)
    num_cols = numeric_columns(df)
    if not group_col or not num_cols:
        return {"module": "viz_comparison", "status": "skipped", "message": "missing group or numeric"}
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    col = num_cols[0]
    fig, ax = plt.subplots()
    if mode == "violin":
        sns.violinplot(x=group_col, y=col, data=df, ax=ax)
    elif mode == "bar":
        sns.barplot(x=group_col, y=col, data=df, ax=ax)
    else:
        sns.boxplot(x=group_col, y=col, data=df, ax=ax)
    ax.set_title(f"{mode} of {col} by {group_col}")
    path = out_dir / f"{mode}_{col}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_comparison", "status": "ok", "output": str(path)}
