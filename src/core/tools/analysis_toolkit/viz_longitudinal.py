from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from .common import load_table, normalize_output_dir
from .viz_theme import apply_theme


def _detect_time_column(df):
    for col in df.columns:
        if "time" in col.lower() or "date" in col.lower():
            return col
    return None


def run(input_path: str | Path, output_dir: str | Path, mode: str = "line", theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    time_col = _detect_time_column(df)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not time_col or not numeric_cols:
        return {"module": "viz_longitudinal", "status": "skipped", "message": "missing time/numeric"}
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots()
    ax.plot(df[time_col], df[numeric_cols[0]])
    ax.set_title("Longitudinal Trend")
    path = out_dir / "longitudinal.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_longitudinal", "status": "ok", "output": str(path)}
