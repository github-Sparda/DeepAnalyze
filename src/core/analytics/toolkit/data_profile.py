from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    profile = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "numeric_columns": numeric_columns(df),
        "categorical_columns": [c for c in df.columns if c not in numeric_columns(df)],
        "missing_total": int(df.isna().sum().sum()),
    }
    out_dir = normalize_output_dir(output_dir, "profile")
    write_json(out_dir / "data_profile.json", profile)
    return {"module": "data_profile", "status": "ok", "output": str(out_dir / "data_profile.json")}
