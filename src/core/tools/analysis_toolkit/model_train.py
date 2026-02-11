from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, detect_group_column, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, method: str = "logistic") -> dict[str, Any]:
    df = load_table(input_path)
    label_col = detect_group_column(df)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not label_col or not num_cols:
        payload = {"status": "skipped", "reason": "missing label or numeric columns"}
        write_json(out_dir / "model_results.json", payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / "model_results.json")}
    # simple baseline: predict mean of label encoded
    labels = pd.Categorical(df[label_col]).codes
    y = labels.astype(float)
    baseline = float(np.mean(y))
    payload = {
        "model": method,
        "label_col": label_col,
        "baseline": baseline,
        "n_samples": int(len(df)),
    }
    write_json(out_dir / "model_results.json", payload)
    return {"module": "model_train", "status": "ok", "output": str(out_dir / "model_results.json")}
