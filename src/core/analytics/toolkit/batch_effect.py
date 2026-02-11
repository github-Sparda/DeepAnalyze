from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, write_json, normalize_output_dir, numeric_columns


def _detect_batch(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if "batch" in col.lower():
            return col
    return None


def run(input_path: str | Path, output_dir: str | Path, method: str = "detect") -> dict[str, Any]:
    df = load_table(input_path)
    batch_col = _detect_batch(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not batch_col:
        payload = {"status": "skipped", "reason": "missing batch column"}
        write_json(out_dir / "batch_effect.json", payload)
        return {"module": "batch_effect", "status": "skipped", "output": str(out_dir / "batch_effect.json")}
    means = {}
    for col in numeric_columns(df):
        means[col] = df.groupby(batch_col)[col].mean().to_dict()
    payload = {"method": method, "batch_col": batch_col, "means": means}
    write_json(out_dir / "batch_effect.json", payload)
    return {"module": "batch_effect", "status": "ok", "output": str(out_dir / "batch_effect.json")}
