from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, detect_group_column, numeric_columns, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    group_col = detect_group_column(df)
    if not group_col:
        return {"module": "subgroup_analysis", "status": "skipped", "message": "no group column"}
    results = []
    for col in numeric_columns(df):
        grouped = df.groupby(group_col)[col].mean().to_dict()
        results.append({"feature": col, "group_means": grouped})
    out_dir = normalize_output_dir(output_dir, "result")
    write_json(out_dir / "subgroup_analysis.json", results)
    return {"module": "subgroup_analysis", "status": "ok", "output": str(out_dir / "subgroup_analysis.json")}
