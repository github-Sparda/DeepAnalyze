from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: str | Path, payload: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


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


def detect_group_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if col.lower() in {"group", "label", "class", "target"}:
            return col
    non_numeric = [c for c in df.columns if not np.issubdtype(df[c].dtype, np.number)]
    return non_numeric[0] if non_numeric else None


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if np.issubdtype(df[c].dtype, np.number)]


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
