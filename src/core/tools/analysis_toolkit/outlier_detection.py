from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, numeric_columns, iqr_bounds, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    results = []
    for col in numeric_columns(df):
        values = pd.to_numeric(df[col], errors="coerce").dropna().to_numpy()
        if values.size == 0:
            continue
        low, high = iqr_bounds(values)
        outliers = int(((values < low) | (values > high)).sum())
        results.append({"feature": col, "outliers": outliers, "low": low, "high": high})
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "outlier_detection.json", results)
    return {"module": "outlier_detection", "status": "ok", "output": str(out_dir / "outlier_detection.json")}
