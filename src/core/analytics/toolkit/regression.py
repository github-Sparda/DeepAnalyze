from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, numeric_columns, detect_group_column, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = numeric_columns(df)
    if len(num_cols) < 2:
        return {"module": "regression", "status": "skipped", "message": "not enough numeric columns"}
    target = num_cols[-1]
    features = num_cols[:-1]
    X = df[features].fillna(0).to_numpy()
    y = df[target].fillna(0).to_numpy()
    # add intercept
    X = np.column_stack([np.ones(X.shape[0]), X])
    try:
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    except Exception:
        coef = np.zeros(X.shape[1])
    result = {
        "target": target,
        "features": ["intercept"] + features,
        "coefficients": [float(c) for c in coef],
    }
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "regression.json", result)
    return {"module": "regression", "status": "ok", "output": str(out_dir / "regression.json")}
