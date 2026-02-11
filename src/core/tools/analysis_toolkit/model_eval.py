from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import (
    load_table,
    detect_group_column,
    numeric_columns,
    write_json,
    normalize_output_dir,
    select_group_labels,
)


def _predict_centroid(sample: np.ndarray, centroids: dict[str, list[float]]) -> str:
    best_label = ""
    best_dist = None
    for label, centroid in centroids.items():
        vec = np.array(centroid)
        dist = float(np.linalg.norm(sample - vec))
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_label = label
    return best_label


def run(
    input_path: str | Path,
    output_dir: str | Path,
    method: str = "baseline",
    model_path: str | Path | None = None,
) -> dict[str, Any]:
    df = load_table(input_path)
    label_col = detect_group_column(df)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not label_col or not num_cols:
        payload = {"status": "skipped", "reason": "missing label or numeric columns"}
        write_json(out_dir / "model_eval.json", payload)
        return {"module": "model_eval", "status": "skipped", "output": str(out_dir / "model_eval.json")}
    group_series, group_info = select_group_labels(df[label_col])
    df = df.copy()
    df["_group_norm"] = group_series
    df = df[df["_group_norm"].notna()]
    labels = df["_group_norm"].astype(str).to_numpy()
    majority_label = pd.Series(labels).mode().iloc[0] if len(labels) else ""
    majority_acc = float(np.mean(labels == majority_label)) if len(labels) else 0.0
    metrics: dict[str, Any] = {"majority_accuracy": majority_acc, "group_info": group_info}
    if model_path and Path(model_path).exists():
        try:
            model_payload = pd.read_json(model_path).to_dict()
        except Exception:
            model_payload = {}
        centroids = model_payload.get("centroids") if isinstance(model_payload, dict) else None
        if isinstance(centroids, dict):
            data = df[num_cols].fillna(0).to_numpy()
            preds = [_predict_centroid(row, centroids) for row in data]
            metrics["centroid_accuracy"] = float(np.mean(labels == np.array(preds))) if len(preds) else 0.0
    else:
        data = df[num_cols].fillna(0).to_numpy()
        unique_labels = sorted(set(labels))
        if unique_labels:
            centroids = {
                label: df[df[label_col].astype(str) == label][num_cols].mean().fillna(0).to_list()
                for label in unique_labels
            }
            preds = [_predict_centroid(row, centroids) for row in data]
            metrics["centroid_accuracy"] = float(np.mean(labels == np.array(preds))) if len(preds) else 0.0
    payload = {"metric": method, "metrics": metrics}
    write_json(out_dir / "model_eval.json", payload)
    return {"module": "model_eval", "status": "ok", "output": str(out_dir / "model_eval.json")}
