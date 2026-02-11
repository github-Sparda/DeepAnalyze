from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, detect_group_column, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, method: str = "roc_pr") -> dict[str, Any]:
    df = load_table(input_path)
    label_col = detect_group_column(df)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not label_col or not num_cols:
        payload = {"status": "skipped", "reason": "missing label or numeric columns"}
        write_json(out_dir / "model_eval.json", payload)
        return {"module": "model_eval", "status": "skipped", "output": str(out_dir / "model_eval.json")}
    # placeholder evaluation: variance of numeric features
    metrics = {"feature_variance": {col: float(df[col].var()) for col in num_cols[:5]}}
    payload = {"metric": method, "metrics": metrics}
    write_json(out_dir / "model_eval.json", payload)
    return {"module": "model_eval", "status": "ok", "output": str(out_dir / "model_eval.json")}
