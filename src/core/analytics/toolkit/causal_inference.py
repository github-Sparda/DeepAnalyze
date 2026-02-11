from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, write_json, normalize_output_dir


def _detect_treatment(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if "treat" in col.lower():
            return col
    return None


def run(input_path: str | Path, output_dir: str | Path, method: str = "psm") -> dict[str, Any]:
    df = load_table(input_path)
    treat_col = _detect_treatment(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not treat_col:
        payload = {"status": "skipped", "reason": "missing treatment column"}
        write_json(out_dir / "causal_inference.json", payload)
        return {"module": "causal_inference", "status": "skipped", "output": str(out_dir / "causal_inference.json")}
    # simple ATE via mean diff on first numeric column
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    outcome_col = numeric_cols[0] if numeric_cols else treat_col
    treated = df[df[treat_col] == 1][outcome_col].mean()
    control = df[df[treat_col] == 0][outcome_col].mean()
    ate = float(treated - control) if pd.notna(treated) and pd.notna(control) else None
    payload = {"method": method, "treatment_col": treat_col, "outcome_col": outcome_col, "ate": ate}
    write_json(out_dir / "causal_inference.json", payload)
    return {"module": "causal_inference", "status": "ok", "output": str(out_dir / "causal_inference.json")}
