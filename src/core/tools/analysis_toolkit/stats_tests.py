from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import numpy as np
import pandas as pd

from .common import load_table, detect_group_column, numeric_columns, safe_values, write_json, write_csv, normalize_output_dir


def _normal_p_value(z: float) -> float:
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def _t_test(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, float, float]:
    if a.size == 0 or b.size == 0:
        return 0.0, 1.0, 0.0
    mean_diff = float(np.mean(a) - np.mean(b))
    var_a = np.var(a, ddof=1) if a.size > 1 else 0.0
    var_b = np.var(b, ddof=1) if b.size > 1 else 0.0
    se = math.sqrt(var_a / max(a.size, 1) + var_b / max(b.size, 1))
    if se == 0:
        return mean_diff, 1.0, 0.0, se, 0.0
    t_stat = mean_diff / se
    p_val = _normal_p_value(t_stat)
    pooled = math.sqrt(((a.size - 1) * var_a + (b.size - 1) * var_b) / max(a.size + b.size - 2, 1))
    effect = mean_diff / pooled if pooled else 0.0
    return mean_diff, p_val, effect, se, t_stat


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    df = load_table(input_path)
    group_col = detect_group_column(df)
    numeric_cols = numeric_columns(df)
    results = []
    if group_col and numeric_cols:
        groups = df[group_col].dropna().unique().tolist()
        if len(groups) >= 2:
            g1, g2 = groups[:2]
            df1 = df[df[group_col] == g1]
            df2 = df[df[group_col] == g2]
            for col in numeric_cols:
                a = safe_values(df1[col])
                b = safe_values(df2[col])
                mean_diff, p_val, effect, se, t_stat = _t_test(a, b)
                mean_a = float(np.mean(a)) if a.size else 0.0
                mean_b = float(np.mean(b)) if b.size else 0.0
                eps = 1e-9
                fold_change = (mean_b + eps) / (mean_a + eps)
                ci_low = mean_diff - 1.96 * se
                ci_high = mean_diff + 1.96 * se
                results.append(
                    {
                        "feature": col,
                        "group_a": str(g1),
                        "group_b": str(g2),
                        "mean_a": mean_a,
                        "mean_b": mean_b,
                        "mean_diff": mean_diff,
                        "fold_change": fold_change,
                        "log2_fold_change": math.log2(fold_change) if fold_change > 0 else 0.0,
                        "p_value": p_val,
                        "ci_low": ci_low,
                        "ci_high": ci_high,
                        "effect_size": effect,
                        "t_stat": t_stat,
                        "n_a": int(a.size),
                        "n_b": int(b.size),
                    }
                )
    out_dir = normalize_output_dir(output_dir, "result")
    df_out = pd.DataFrame(results)
    write_csv(out_dir / "stats_results.csv", df_out)
    write_json(out_dir / "stats_results.json", results)
    return {"module": "stats_tests", "status": "ok", "output": str(out_dir / "stats_results.json")}
