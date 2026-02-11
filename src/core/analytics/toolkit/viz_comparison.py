from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import load_table, detect_group_column, numeric_columns, normalize_output_dir
from src.core.visualization.plotter import render_group_comparison


def run(
    input_path: str | Path,
    output_dir: str | Path,
    mode: str = "box",
    theme: dict[str, Any] | None = None,
) -> dict[str, Any]:
    df = load_table(input_path)
    group_col = detect_group_column(df)
    num_cols = numeric_columns(df)
    if not group_col or not num_cols:
        return {"module": "viz_comparison", "status": "skipped", "message": "missing group or numeric"}
    out_dir = normalize_output_dir(output_dir, "plots")
    col = num_cols[0]
    path = out_dir / f"{mode}_{col}.png"
    render_group_comparison(
        df,
        category=group_col,
        value=col,
        output_path=path,
        mode=mode,
        style=(theme or {}).get("style", "academic"),
        interactive=False,
    )
    return {"module": "viz_comparison", "status": "ok", "output": str(path)}
