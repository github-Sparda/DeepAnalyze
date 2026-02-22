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
    evaluate_label_health,
)


def _compute_centroids(df: pd.DataFrame, label_col: str, num_cols: list[str]) -> dict[str, list[float]]:
    centroids: dict[str, list[float]] = {}
    for label, group in df.groupby(label_col):
        centroid = group[num_cols].mean().fillna(0).to_list()
        centroids[str(label)] = [float(x) for x in centroid]
    return centroids


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


def run(input_path: str | Path, output_dir: str | Path, method: str = "centroid") -> dict[str, Any]:
    df = load_table(input_path)
    label_col = detect_group_column(df)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not label_col or not num_cols:
        payload = {"status": "skipped", "reason": "missing label or numeric columns"}
        write_json(out_dir / "model_results.json", payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / "model_results.json")}
    group_series, group_info = select_group_labels(df[label_col])
    df = df.copy()
    df["_group_norm"] = group_series
    df = df[df["_group_norm"].notna()]
    mapping = (
        pd.DataFrame({"raw_label": df[label_col].astype(str), "analysis_label": df["_group_norm"].astype(str)})
        .drop_duplicates()
        .sort_values(["analysis_label", "raw_label"])
    )
    write_json(
        out_dir / "analysis_label_mapping.json",
        {
            "source_label_col": label_col,
            "analysis_label_col": "_group_norm",
            "group_info": group_info,
            "mappings": mapping.to_dict(orient="records"),
        },
    )
    labels = df["_group_norm"].astype(str)
    health = evaluate_label_health(labels)
    write_json(out_dir / "label_health_report.json", health)
    if not health.get("valid", False):
        payload = {
            "status": "skipped",
            "reason": "label_invalid_for_modeling",
            "label_health": health,
        }
        write_json(out_dir / "model_results.json", payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / "model_results.json")}
    data = df[num_cols].fillna(0).to_numpy()
    rng = np.random.default_rng(0)
    indices = np.arange(len(df))
    rng.shuffle(indices)
    split = int(len(indices) * 0.8) if len(indices) > 1 else len(indices)
    train_idx = indices[:split]
    test_idx = indices[split:] if split < len(indices) else indices[:split]
    train_df = df.iloc[train_idx]
    test_df = df.iloc[test_idx] if len(test_idx) else train_df
    centroids = _compute_centroids(train_df, "_group_norm", num_cols)
    train_pred = [
        _predict_centroid(train_df[num_cols].iloc[i].fillna(0).to_numpy(), centroids)
        for i in range(len(train_df))
    ]
    test_pred = [
        _predict_centroid(test_df[num_cols].iloc[i].fillna(0).to_numpy(), centroids)
        for i in range(len(test_df))
    ]
    train_acc = float(np.mean(train_df["_group_norm"].astype(str).to_numpy() == np.array(train_pred))) if len(train_df) else 0.0
    test_acc = float(np.mean(test_df["_group_norm"].astype(str).to_numpy() == np.array(test_pred))) if len(test_df) else 0.0
    payload = {
        "model": method,
        "label_col": label_col,
        "group_info": group_info,
        "train_accuracy": train_acc,
        "test_accuracy": test_acc,
        "centroids": centroids,
        "n_samples": int(len(df)),
    }
    write_json(out_dir / "model_results.json", payload)
    return {"module": "model_train", "status": "ok", "output": str(out_dir / "model_results.json")}
