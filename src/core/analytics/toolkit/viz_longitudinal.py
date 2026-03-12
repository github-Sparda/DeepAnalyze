from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import load_table, normalize_output_dir
from src.core.visualization.plotter import render_trend
from src.core.common import detect_time_column as _detect_time_column


def run(
    input_path: str | Path,
    output_dir: str | Path,
    mode: str = "line",
    theme: dict[str, Any] | None = None,
) -> dict[str, Any]:
    df = load_table(input_path)
    time_col = _detect_time_column(df)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not time_col or not numeric_cols:
        return {"module": "viz_longitudinal", "status": "skipped", "message": "missing time/numeric"}
    out_dir = normalize_output_dir(output_dir, "plots")
    path = out_dir / "longitudinal.png"
    render_trend(
        df,
        x=time_col,
        y=numeric_cols[0],
        output_path=path,
        style=(theme or {}).get("style", "academic"),
        interactive=False,
    )
    return {"module": "viz_longitudinal", "status": "ok", "output": str(path)}
