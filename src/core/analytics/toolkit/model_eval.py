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


def _build_centroids(df: pd.DataFrame, num_cols: list[str], labels: np.ndarray) -> dict[str, list[float]]:
    centroids: dict[str, list[float]] = {}
    for label in sorted(set(labels)):
        subset = df[labels == label]
        centroids[label] = subset[num_cols].mean().fillna(0).to_list()
    return centroids


def _cv_centroid_accuracy(df: pd.DataFrame, num_cols: list[str], labels: np.ndarray, folds: int) -> dict[str, Any]:
    if folds < 2:
        raise ValueError("cv_folds must be >= 2")
    unique_labels, counts = np.unique(labels, return_counts=True)
    if len(unique_labels) < 2:
        raise ValueError("need at least two classes for CV")
    min_count = int(counts.min())
    if min_count < 2:
        raise ValueError("not enough samples per class for CV")
    folds = min(folds, min_count)
    # stratified fold indices
    indices = np.arange(len(labels))
    fold_bins: list[list[int]] = [[] for _ in range(folds)]
    for label in unique_labels:
        label_idx = indices[labels == label]
        np.random.shuffle(label_idx)
        for i, idx in enumerate(label_idx):
            fold_bins[i % folds].append(int(idx))
    fold_metrics: list[dict[str, Any]] = []
    for fold in range(folds):
        test_idx = np.array(fold_bins[fold], dtype=int)
        train_idx = np.array([i for i in indices if i not in test_idx], dtype=int)
        train_df = df.iloc[train_idx]
        train_labels = labels[train_idx]
        centroids = _build_centroids(train_df, num_cols, train_labels)
        test_df = df.iloc[test_idx]
        preds = [_predict_centroid(row, centroids) for row in test_df[num_cols].fillna(0).to_numpy()]
        acc = float(np.mean(labels[test_idx] == np.array(preds))) if len(preds) else 0.0
        fold_metrics.append({"fold": fold + 1, "accuracy": acc, "test_size": int(len(test_idx))})
    accuracies = [m["accuracy"] for m in fold_metrics]
    return {
        "folds": folds,
        "fold_metrics": fold_metrics,
        "mean_accuracy": float(np.mean(accuracies)),
        "std_accuracy": float(np.std(accuracies)),
    }


def run(
    input_path: str | Path,
    output_dir: str | Path,
    method: str = "baseline",
    model_path: str | Path | None = None,
    cv_folds: int = 5,
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
    labels = df["_group_norm"].astype(str).to_numpy()
    health = evaluate_label_health(pd.Series(labels), cv_folds=cv_folds)
    write_json(out_dir / "label_health_report.json", health)
    if not health.get("valid", False):
        payload = {
            "metric": method,
            "status": "skipped",
            "reason": "label_invalid_for_modeling",
            "metrics": {"group_info": group_info, "label_health": health},
        }
        write_json(out_dir / "model_eval.json", payload)
        write_json(out_dir / "cv_results.json", {"status": "skipped", "reason": "label_invalid_for_modeling"})
        return {"module": "model_eval", "status": "skipped", "output": str(out_dir / "model_eval.json")}
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
            centroids = _build_centroids(df, num_cols, labels)
            preds = [_predict_centroid(row, centroids) for row in data]
            metrics["centroid_accuracy"] = float(np.mean(labels == np.array(preds))) if len(preds) else 0.0
    cv_payload: dict[str, Any] = {}
    failure_payload: dict[str, Any] = {}
    try:
        cv_payload = _cv_centroid_accuracy(df[num_cols], num_cols, labels, cv_folds)
        write_json(out_dir / "cv_results.json", {"status": "ok", **cv_payload})
    except Exception as exc:
        failure_payload = {"stage": "cross_validation", "error": str(exc)}
        write_json(out_dir / "validation_failures.json", failure_payload)
        cv_payload = {"status": "failed", "error": str(exc)}
        write_json(out_dir / "cv_results.json", cv_payload)
    payload = {"metric": method, "metrics": metrics}
    leakage_warning = {}
    train_acc = metrics.get("centroid_accuracy")
    test_acc = cv_payload.get("mean_accuracy") if isinstance(cv_payload, dict) else None
    if isinstance(train_acc, (int, float)) and isinstance(test_acc, (int, float)):
        if float(train_acc) >= 0.98 and float(test_acc) <= 0.1:
            leakage_warning = {
                "reason_code": "possible_leakage_or_label_issue",
                "train_metric": float(train_acc),
                "test_metric": float(test_acc),
                "action": "recheck_label_mapping_and_split_strategy",
            }
    if leakage_warning:
        payload["warning"] = leakage_warning
    write_json(out_dir / "model_eval.json", payload)
    detail_payload = {"metrics": metrics, "cv": cv_payload, "validation_failure": failure_payload, "warning": leakage_warning}
    write_json(out_dir / "model_eval_detail.json", detail_payload)
    return {"module": "model_eval", "status": "ok", "output": str(out_dir / "model_eval.json")}
