from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, write_json, normalize_output_dir


def _detect_time_event(df: pd.DataFrame) -> tuple[str | None, str | None]:
    time_col = None
    event_col = None
    for col in df.columns:
        name = col.lower()
        if time_col is None and ("time" in name or "duration" in name):
            time_col = col
        if event_col is None and ("event" in name or "status" in name):
            event_col = col
    return time_col, event_col


def run(input_path: str | Path, output_dir: str | Path, method: str = "km") -> dict[str, Any]:
    df = load_table(input_path)
    time_col, event_col = _detect_time_event(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not time_col or not event_col:
        payload = {"status": "skipped", "reason": "missing time/event columns"}
        write_json(out_dir / "survival_analysis.json", payload)
        return {"module": "survival_analysis", "status": "skipped", "output": str(out_dir / "survival_analysis.json")}
    times = pd.to_numeric(df[time_col], errors="coerce").dropna().to_numpy()
    events = pd.to_numeric(df[event_col], errors="coerce").fillna(0).to_numpy()
    survival = []
    if times.size > 0:
        order = np.argsort(times)
        n = len(times)
        at_risk = n
        surv = 1.0
        for idx in order:
            t = float(times[idx])
            d = 1 if idx < len(events) and events[idx] else 0
            if d:
                surv *= (at_risk - 1) / at_risk
            survival.append({"time": t, "survival": surv})
            at_risk -= 1
    payload = {"method": method, "time_col": time_col, "event_col": event_col, "survival": survival}
    write_json(out_dir / "survival_analysis.json", payload)
    return {"module": "survival_analysis", "status": "ok", "output": str(out_dir / "survival_analysis.json")}
