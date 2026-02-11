from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .common import load_table, numeric_columns, iqr_bounds, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    missing_rate = df.isna().mean().to_dict()
    duplicates = int(df.duplicated().sum())
    outlier_counts = {}
    for col in numeric_columns(df):
        values = df[col].dropna().to_numpy()
        if values.size == 0:
            continue
        low, high = iqr_bounds(values)
        outlier_counts[col] = int(((values < low) | (values > high)).sum())
    quality = {
        "missing_rate": missing_rate,
        "duplicates": duplicates,
        "outliers": outlier_counts,
    }
    out_dir = normalize_output_dir(output_dir, "profile")
    write_json(out_dir / "data_quality.json", quality)
    return {"module": "data_quality", "status": "ok", "output": str(out_dir / "data_quality.json")}
