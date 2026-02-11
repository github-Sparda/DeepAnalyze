from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from .common import load_table, numeric_columns, normalize_output_dir
from .viz_theme import apply_theme


def run_basic(input_path: str | Path, output_dir: str | Path, theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    outputs = []
    num_cols = numeric_columns(df)
    for col in num_cols[:4]:
        fig, ax = plt.subplots()
        sns.histplot(df[col].dropna(), ax=ax, kde=True)
        ax.set_title(f"Distribution of {col}")
        path = out_dir / f"hist_{col}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        outputs.append(str(path))
    return {"module": "plot_utils", "status": "ok", "plots": outputs}
