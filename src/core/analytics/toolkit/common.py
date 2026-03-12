from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from src.core.common import ensure_dir, save_json, load_json


def load_analysis_runtime_config(base_dir: str | Path | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "group_column_candidates": ["group", "label", "class", "target"],
        "group_selection": {
            "prefer_reference_vs_others": True,
            "reference_labels": ["Normal", "Control", "Healthy"],
            "preferred_case_labels": ["EP", "Case"],
            "max_top_groups": 2,
        },
    }
    if base_dir is None:
        return defaults
    root = Path(base_dir)
    candidates = [
        root / "config" / "analysis_runtime.json",
        root / "analysis_runtime.json",
        Path("config") / "analysis_runtime.json",
    ]
    for path in candidates:
        payload = load_json(path)
        if payload and isinstance(payload, dict):
            merged = dict(defaults)
            for key, value in payload.items():
                if key == "group_selection" and isinstance(value, dict):
                    group_selection = dict(defaults.get("group_selection", {}))
                    group_selection.update(value)
                    merged[key] = group_selection
                else:
                    merged[key] = value
            return merged
    return defaults


# 使用公共模块的函数替代私有实现
write_json = save_json


def write_csv(path: str | Path, df: pd.DataFrame) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p


def load_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p)
    if p.suffix.lower() in {".json"}:
        return pd.read_json(p)
    if p.suffix.lower() in {".tsv"}:
        return pd.read_csv(p, sep="\t")
    return pd.read_csv(p)


def detect_group_column(df: pd.DataFrame, runtime_config: dict[str, Any] | None = None) -> str | None:
    config = runtime_config if isinstance(runtime_config, dict) else {}
    candidates = [
        str(x).strip().lower()
        for x in config.get("group_column_candidates", [])
        if str(x).strip()
    ] or ["group", "label", "class", "target"]
    for col in df.columns:
        if col.lower() in candidates:
            return col
    non_numeric = [c for c in df.columns if not np.issubdtype(df[c].dtype, np.number)]
    return non_numeric[0] if non_numeric else None


def normalize_group_labels(series: pd.Series) -> pd.Series:
    values = series.astype(str).fillna("")
    prefixes = values.str.extract(r"([A-Za-z]+)", expand=False).fillna("")
    normalized = prefixes.where(prefixes.str.len() >= 2, values)
    return normalized


def select_group_labels(
    series: pd.Series,
    runtime_config: dict[str, Any] | None = None,
) -> tuple[pd.Series, dict[str, Any]]:
    config = runtime_config if isinstance(runtime_config, dict) else {}
    group_selection = config.get("group_selection", {}) if isinstance(config.get("group_selection"), dict) else {}
    raw = series.astype(str).fillna("")
    raw_groups = raw.unique().tolist()
    info: dict[str, Any] = {
        "method": "raw",
        "raw_groups": raw_groups[:20],
        "raw_group_count": len(raw_groups),
        "normalized_groups": [],
        "used_groups": [],
        "excluded_groups": [],
    }
    if len(raw_groups) <= 2:
        info["used_groups"] = raw_groups
        return raw, info
    normalized = normalize_group_labels(raw)
    norm_groups = normalized.unique().tolist()
    info["normalized_groups"] = norm_groups
    if len(norm_groups) <= 2:
        info["method"] = "normalized"
        info["used_groups"] = norm_groups
        return normalized, info
    reference_labels = [str(x).strip() for x in group_selection.get("reference_labels", []) if str(x).strip()]
    preferred_case_labels = [str(x).strip() for x in group_selection.get("preferred_case_labels", []) if str(x).strip()]
    if bool(group_selection.get("prefer_reference_vs_others", True)) and reference_labels:
        reference = next((label for label in reference_labels if label in norm_groups), "")
        if reference:
            other_groups = [g for g in norm_groups if g != reference]
            target_label = next(
                (candidate for candidate in preferred_case_labels if any(candidate.upper() in g.upper() for g in other_groups)),
                "Case",
            )
            mapped = normalized.where(normalized == reference, target_label)
            info["method"] = "reference_vs_others"
            info["used_groups"] = [reference, target_label]
            info["reference_label"] = reference
            info["excluded_groups"] = []
            return mapped, info
    counts = normalized.value_counts()
    max_top_groups = int(group_selection.get("max_top_groups", 2) or 2)
    top2 = counts.head(max(2, max_top_groups)).index.tolist()[:2]
    info["method"] = "top2_normalized"
    info["used_groups"] = top2
    info["excluded_groups"] = [g for g in norm_groups if g not in top2]
    filtered = normalized.where(normalized.isin(top2))
    return filtered, info


def evaluate_label_health(
    labels: pd.Series,
    max_class_count: int = 20,
    min_samples_per_class: int = 2,
    cv_folds: int = 5,
) -> dict[str, Any]:
    series = labels.astype(str).fillna("")
    total = int(len(series))
    unique = int(series.nunique()) if total else 0
    unique_ratio = float(unique / total) if total else 0.0
    counts = series.value_counts().to_dict() if total else {}
    min_class_size = int(min(counts.values())) if counts else 0
    max_class_size = int(max(counts.values())) if counts else 0
    feasible_cv_folds = int(min(cv_folds, min_class_size)) if counts else 0
    issues: list[str] = []
    if total == 0:
        issues.append("empty_labels")
    if unique_ratio > 0.8:
        issues.append("label_id_like_unique_ratio_high")
    if len(counts) < 2:
        issues.append("insufficient_class_count")
    if len(counts) > max_class_count:
        issues.append("class_count_exceeds_limit")
    if min_class_size < min_samples_per_class and len(counts) >= 2:
        issues.append("class_size_too_small_for_modeling")
    if len(counts) >= 2 and min_class_size < 2:
        issues.append("split_not_feasible")
    if len(counts) >= 2 and feasible_cv_folds < 2:
        issues.append("cross_validation_not_feasible")
    return {
        "valid": len(issues) == 0,
        "total_samples": total,
        "unique_labels": unique,
        "unique_ratio": unique_ratio,
        "class_counts": counts,
        "min_class_size": min_class_size,
        "max_class_size": max_class_size,
        "max_class_count": max_class_count,
        "min_samples_per_class": min_samples_per_class,
        "requested_cv_folds": cv_folds,
        "feasible_cv_folds": feasible_cv_folds,
        "issues": issues,
    }


def numeric_columns(df: pd.DataFrame) -> list[str]:
    from pandas.api.types import is_numeric_dtype
    return [c for c in df.columns if is_numeric_dtype(df[c].dtype)]


def safe_values(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").dropna().to_numpy()


def iqr_bounds(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (0.0, 0.0)
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)


def default_output(payload_name: str, status: str, message: str) -> dict[str, Any]:
    return {"module": payload_name, "status": status, "message": message}


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_output_dir(base_dir: str | Path, name: str) -> Path:
    return ensure_dir(Path(base_dir) / name)


def guard_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    return [c for c in columns if c in df.columns]
