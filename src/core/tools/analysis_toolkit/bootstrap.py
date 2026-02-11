from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np

from .common import load_table, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, iterations: int = 200) -> dict[str, Any]:
    df = load_table(input_path)
    results = []
    for col in numeric_columns(df):
        values = df[col].dropna().to_numpy()
        if values.size == 0:
            continue
        means = []
        for _ in range(iterations):
            sample = np.random.choice(values, size=values.size, replace=True)
            means.append(float(np.mean(sample)))
        low, high = np.percentile(means, [2.5, 97.5])
        results.append({"feature": col, "mean": float(np.mean(values)), "ci_low": float(low), "ci_high": float(high)})
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "bootstrap.json", results)
    return {"module": "bootstrap", "status": "ok", "output": str(out_dir / "bootstrap.json")}
