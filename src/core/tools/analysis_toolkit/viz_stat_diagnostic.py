from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from .common import load_table, normalize_output_dir
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, mode: str = "qq", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if not num_cols:
        return {"module": "viz_stat_diagnostic", "status": "skipped", "message": "no numeric"}
    data = df[num_cols[0]].dropna().to_numpy()
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots()
    if mode == "qq":
        sorted_data = np.sort(data)
        quantiles = np.linspace(0, 1, len(sorted_data))
        ax.plot(quantiles, sorted_data, marker=".")
        ax.set_title("QQ Plot")
    else:
        ax.plot(data)
        ax.set_title("Diagnostic Plot")
    path = out_dir / f"diagnostic_{mode}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_stat_diagnostic", "status": "ok", "output": str(path)}
