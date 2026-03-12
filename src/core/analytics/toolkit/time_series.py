from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .common import load_table, write_json, normalize_output_dir
from src.core.common import detect_time_column as _detect_time_column


def run(input_path: str | Path, output_dir: str | Path, method: str = "decompose") -> dict[str, Any]:
    df = load_table(input_path)
    time_col = _detect_time_column(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not time_col:
        payload = {"status": "skipped", "reason": "no time column"}
        write_json(out_dir / "time_series.json", payload)
        return {"module": "time_series", "status": "skipped", "output": str(out_dir / "time_series.json")}
    df = df.sort_values(time_col)
    payload = {"method": method, "time_col": time_col, "rows": int(len(df))}
    write_json(out_dir / "time_series.json", payload)
    return {"module": "time_series", "status": "ok", "output": str(out_dir / "time_series.json")}
