from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, numeric_columns, write_json, write_csv, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, top_k: int = 10) -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = numeric_columns(df)
    if not num_cols:
        return {"module": "feature_selection", "status": "skipped", "message": "no numeric columns"}
    variances = df[num_cols].var().sort_values(ascending=False)
    selected = variances.head(top_k)
    result = [{"feature": idx, "variance": float(val)} for idx, val in selected.items()]
    out_dir = normalize_output_dir(output_dir, "result")
    write_csv(out_dir / "feature_selection.csv", pd.DataFrame(result))
    write_json(out_dir / "feature_selection.json", result)
    return {"module": "feature_selection", "status": "ok", "output": str(out_dir / "feature_selection.json")}
