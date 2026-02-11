from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, numeric_columns, write_csv, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, method: str = "zscore") -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = numeric_columns(df)
    if not num_cols:
        return {"module": "normalization", "status": "skipped", "message": "no numeric columns"}
    norm_df = df.copy()
    if method == "minmax":
        for col in num_cols:
            col_min = norm_df[col].min()
            col_max = norm_df[col].max()
            if col_max != col_min:
                norm_df[col] = (norm_df[col] - col_min) / (col_max - col_min)
    else:
        for col in num_cols:
            mean = norm_df[col].mean()
            std = norm_df[col].std()
            if std and std != 0:
                norm_df[col] = (norm_df[col] - mean) / std
    out_dir = normalize_output_dir(output_dir, "result")
    write_csv(out_dir / "normalized.csv", norm_df)
    return {"module": "normalization", "status": "ok", "output": str(out_dir / "normalized.csv")}
