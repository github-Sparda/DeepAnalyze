from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np

from .common import load_table, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, simulations: int = 200) -> dict[str, Any]:
    df = load_table(input_path)
    results = []
    for col in numeric_columns(df):
        values = df[col].dropna().to_numpy()
        if values.size == 0:
            continue
        mu = float(np.mean(values))
        sigma = float(np.std(values))
        sims = np.random.normal(mu, sigma, size=simulations)
        results.append({"feature": col, "mean": mu, "std": sigma, "sim_mean": float(np.mean(sims))})
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "monte_carlo.json", results)
    return {"module": "monte_carlo", "status": "ok", "output": str(out_dir / "monte_carlo.json")}
