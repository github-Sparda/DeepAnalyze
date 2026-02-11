from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .common import load_table, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    results = []
    for col in numeric_columns(df):
        values = df[col].dropna().to_numpy()
        if values.size == 0:
            continue
        results.append(
            {
                "feature": col,
                "median": float(np.median(values)),
                "mad": float(np.median(np.abs(values - np.median(values)))),
                "p25": float(np.percentile(values, 25)),
                "p75": float(np.percentile(values, 75)),
            }
        )
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "robust_stats.json", results)
    return {"module": "robust_stats", "status": "ok", "output": str(out_dir / "robust_stats.json")}
