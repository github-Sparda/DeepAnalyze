from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .common import load_table, write_json, normalize_output_dir


def _bh_fdr(pvals: list[float]) -> list[float]:
    n = len(pvals)
    if n == 0:
        return []
    sorted_idx = np.argsort(pvals)
    sorted_p = np.array(pvals)[sorted_idx]
    q = np.empty(n, dtype=float)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        val = sorted_p[i] * n / rank
        prev = min(prev, val)
        q[i] = prev
    out = np.empty(n, dtype=float)
    out[sorted_idx] = q
    return out.tolist()


def run(input_path: str | Path, output_dir: str | Path, pval_field: str = "p_value") -> dict[str, Any]:
    df = load_table(input_path)
    if pval_field not in df.columns:
        return {"module": "multiple_testing", "status": "skipped", "message": "p_value column missing"}
    pvals = df[pval_field].fillna(1.0).to_list()
    qvals = _bh_fdr([float(p) for p in pvals])
    df["q_value"] = qvals
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "multiple_testing.json", df.to_dict(orient="records"))
    return {"module": "multiple_testing", "status": "ok", "output": str(out_dir / "multiple_testing.json")}
