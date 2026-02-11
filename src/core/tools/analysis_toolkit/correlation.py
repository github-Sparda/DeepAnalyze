from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, numeric_columns, write_json, write_csv, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = numeric_columns(df)
    if not num_cols:
        return {"module": "correlation", "status": "skipped", "message": "no numeric columns"}
    corr = df[num_cols].corr().fillna(0)
    out_dir = normalize_output_dir(output_dir, "result")
    write_csv(out_dir / "correlation.csv", corr.reset_index())
    write_json(out_dir / "correlation.json", corr.to_dict())
    return {"module": "correlation", "status": "ok", "output": str(out_dir / "correlation.json")}
