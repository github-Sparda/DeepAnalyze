from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import (
    load_table,
    detect_group_column,
    load_analysis_runtime_config,
    numeric_columns,
    write_json,
    write_csv,
    normalize_output_dir,
    select_group_labels,
    evaluate_label_health,
)


def _predict_centroid(sample: np.ndarray, centroids: dict[str, list[float]]) -> str:
    from src.core.common import find_nearest_centroid
    return find_nearest_centroid(sample, centroids)


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


def _cv_sklearn_model_accuracy(df: pd.DataFrame, num_cols: list[str], labels: np.ndarray, folds: int, model_name: str) -> dict[str, Any]:
    if folds < 2:
        raise ValueError("cv_folds must be >= 2")
    unique_labels, counts = np.unique(labels, return_counts=True)
    if len(unique_labels) < 2:
        raise ValueError("need at least two classes for CV")
    min_count = int(counts.min())
    if min_count < 2:
        raise ValueError("not enough samples per class for CV")
    folds = min(folds, min_count)
    try:
        from sklearn.ensemble import RandomForestClassifier  # type: ignore
        from sklearn.linear_model import LogisticRegression  # type: ignore
        from sklearn.model_selection import StratifiedKFold  # type: ignore
        from sklearn.pipeline import make_pipeline  # type: ignore
        from sklearn.preprocessing import StandardScaler  # type: ignore
    except Exception as exc:
        raise ValueError(f"sklearn unavailable for model CV: {exc}") from exc
    if model_name == "logistic":
        estimator_factory = lambda: make_pipeline(  # noqa: E731
            StandardScaler(),
            LogisticRegression(max_iter=1000, solver="liblinear", random_state=0),
        )
    elif model_name == "random_forest":
        estimator_factory = lambda: RandomForestClassifier(n_estimators=300, random_state=0)  # noqa: E731
    else:
        raise ValueError(f"unsupported model for CV: {model_name}")

    X = df[num_cols].fillna(0).to_numpy()
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
    fold_metrics: list[dict[str, Any]] = []
    for fold, (train_idx, test_idx) in enumerate(cv.split(X, labels), start=1):
        estimator = estimator_factory()
        estimator.fit(X[train_idx], labels[train_idx])
        preds = estimator.predict(X[test_idx])
        acc = float(np.mean(labels[test_idx] == np.array(preds))) if len(test_idx) else 0.0
        fold_metrics.append({"fold": fold, "accuracy": acc, "test_size": int(len(test_idx))})
    accuracies = [m["accuracy"] for m in fold_metrics]
    return {
        "folds": folds,
        "fold_metrics": fold_metrics,
        "mean_accuracy": float(np.mean(accuracies)),
        "std_accuracy": float(np.std(accuracies)),
        "model": model_name,
    }


def _result_filename(base_name: str, artifact_prefix: str = "") -> str:
    prefix = str(artifact_prefix or "").strip()
    if not prefix:
        return base_name
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix
    return f"{stem}_{prefix}{suffix}"


def _render_curve_plot(
    xs: list[float],
    ys: list[float],
    path: Path,
    title: str,
    xlabel: str,
    ylabel: str,
    diagonal: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(xs, ys, linewidth=2)
    if diagonal:
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _render_feature_importance_plot(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    top_rows = rows[:15]
    labels = [str(item.get("feature", "")) for item in top_rows]
    values = [float(item.get("importance", 0.0)) for item in top_rows]
    fig, ax = plt.subplots(figsize=(7, max(4, len(top_rows) * 0.35)))
    positions = np.arange(len(labels))
    ax.barh(positions, values)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Importance")
    ax.set_title("Feature Importance")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def run(
    input_path: str | Path,
    output_dir: str | Path,
    method: str = "baseline",
    model_path: str | Path | None = None,
    cv_folds: int = 5,
    artifact_prefix: str = "",
) -> dict[str, Any]:
    df = load_table(input_path)
    runtime_config = load_analysis_runtime_config(Path(input_path).resolve().parent)
    label_col = detect_group_column(df, runtime_config=runtime_config)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    plots_dir = normalize_output_dir(output_dir, "plots")
    eval_name = _result_filename("model_eval.json", artifact_prefix)
    detail_name = _result_filename("model_eval_detail.json", artifact_prefix)
    cv_name = _result_filename("cv_results.json", artifact_prefix)
    failure_name = _result_filename("validation_failures.json", artifact_prefix)
    confusion_name = _result_filename("confusion_matrix.json", artifact_prefix)
    comparison_json_name = _result_filename("model_performance_comparison.json", artifact_prefix)
    comparison_csv_name = _result_filename("model_performance_comparison.csv", artifact_prefix)
    importance_json_name = _result_filename("feature_importance.json", artifact_prefix)
    importance_csv_name = _result_filename("feature_importance.csv", artifact_prefix)
    roc_plot_name = _result_filename("roc_curve.png", artifact_prefix)
    pr_plot_name = _result_filename("pr_curve.png", artifact_prefix)
    importance_plot_name = _result_filename("feature_importance_plot.png", artifact_prefix)
    if not label_col or not num_cols:
        payload = {"status": "skipped", "reason": "missing label or numeric columns"}
        write_json(out_dir / eval_name, payload)
        return {"module": "model_eval", "status": "skipped", "output": str(out_dir / eval_name)}
    group_series, group_info = select_group_labels(df[label_col], runtime_config=runtime_config)
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
        write_json(out_dir / eval_name, payload)
        write_json(out_dir / cv_name, {"status": "skipped", "reason": "label_invalid_for_modeling"})
        return {"module": "model_eval", "status": "skipped", "output": str(out_dir / eval_name)}
    majority_label = pd.Series(labels).mode().iloc[0] if len(labels) else ""
    majority_acc = float(np.mean(labels == majority_label)) if len(labels) else 0.0
    metrics: dict[str, Any] = {"majority_accuracy": majority_acc, "group_info": group_info}
    model_payload: dict[str, Any] = {}
    if model_path and Path(model_path).exists():
        try:
            model_payload = json.loads(Path(model_path).read_text(encoding="utf-8"))
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
    if "preds" in locals():
        label_order = sorted(set(labels))
        matrix: dict[str, dict[str, int]] = {}
        for actual in label_order:
            matrix[str(actual)] = {}
            for predicted in label_order:
                matrix[str(actual)][str(predicted)] = 0
        for actual, predicted in zip(labels, preds):
            matrix[str(actual)][str(predicted)] = int(matrix[str(actual)][str(predicted)] + 1)
        write_json(
            out_dir / confusion_name,
            {"labels": [str(x) for x in label_order], "matrix": matrix},
        )
    model_name = str(model_payload.get("model", "")).strip().lower() if isinstance(model_payload, dict) else ""
    cv_payload: dict[str, Any] = {}
    failure_payload: dict[str, Any] = {}
    try:
        if model_name in {"logistic", "random_forest"}:
            cv_payload = _cv_sklearn_model_accuracy(df[num_cols], num_cols, labels, cv_folds, model_name)
        else:
            cv_payload = _cv_centroid_accuracy(df[num_cols], num_cols, labels, cv_folds)
        write_json(out_dir / cv_name, {"status": "ok", **cv_payload})
    except Exception as exc:
        failure_payload = {"stage": "cross_validation", "error": str(exc)}
        write_json(out_dir / failure_name, failure_payload)
        cv_payload = {"status": "failed", "error": str(exc)}
        write_json(out_dir / cv_name, cv_payload)
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
    classes = [str(x) for x in model_payload.get("classes", [])] if isinstance(model_payload.get("classes"), list) else []
    positive_label = str(model_payload.get("positive_label", "")).strip()
    if model_name in {"logistic", "random_forest"} and method in {"roc_pr", "importance", "baseline"}:
        metrics["model_name"] = model_name
        metrics["train_accuracy"] = float(model_payload.get("train_accuracy", 0.0) or 0.0)
        metrics["test_accuracy"] = float(model_payload.get("test_accuracy", 0.0) or 0.0)
        test_truth = [str(x) for x in model_payload.get("test_truth", [])]
        test_pred = [str(x) for x in model_payload.get("test_pred", [])]
        test_score = [float(x) for x in model_payload.get("test_score", [])]
        if test_truth and test_pred:
            label_order = sorted(set(test_truth + test_pred))
            confusion: dict[str, dict[str, int]] = {label: {pred: 0 for pred in label_order} for label in label_order}
            for actual, predicted in zip(test_truth, test_pred):
                confusion[actual][predicted] = int(confusion[actual][predicted] + 1)
            write_json(out_dir / confusion_name, {"labels": label_order, "matrix": confusion})
        if len(classes) == 2 and positive_label and len(test_truth) == len(test_score):
            try:
                from sklearn.metrics import (
                    auc,  # type: ignore
                    average_precision_score,  # type: ignore
                    precision_recall_curve,  # type: ignore
                    roc_curve,  # type: ignore
                )

                y_true = np.array([1 if str(x) == positive_label else 0 for x in test_truth], dtype=int)
                scores = np.array(test_score, dtype=float)
                fpr, tpr, _ = roc_curve(y_true, scores)
                precision, recall, _ = precision_recall_curve(y_true, scores)
                roc_auc = float(auc(fpr, tpr))
                pr_auc = float(average_precision_score(y_true, scores))
                metrics["roc_auc"] = roc_auc
                metrics["pr_auc"] = pr_auc
                _render_curve_plot(
                    [float(x) for x in fpr],
                    [float(x) for x in tpr],
                    plots_dir / roc_plot_name,
                    "ROC Curve",
                    "False Positive Rate",
                    "True Positive Rate",
                    diagonal=True,
                )
                write_json(
                    plots_dir / f"{roc_plot_name}.json",
                    {
                        "path": str(plots_dir / roc_plot_name),
                        "type": "roc_curve",
                        "model": model_name,
                        "positive_label": positive_label,
                        "auc": roc_auc,
                        "input_model": str(model_path or ""),
                    },
                )
                _render_curve_plot(
                    [float(x) for x in recall],
                    [float(x) for x in precision],
                    plots_dir / pr_plot_name,
                    "Precision-Recall Curve",
                    "Recall",
                    "Precision",
                )
                write_json(
                    plots_dir / f"{pr_plot_name}.json",
                    {
                        "path": str(plots_dir / pr_plot_name),
                        "type": "precision_recall_curve",
                        "model": model_name,
                        "positive_label": positive_label,
                        "average_precision": pr_auc,
                        "input_model": str(model_path or ""),
                    },
                )
            except Exception as exc:
                failure_payload = {**failure_payload, "curve_error": str(exc)}
        importance_rows = model_payload.get("feature_importance", []) if isinstance(model_payload, dict) else []
        if isinstance(importance_rows, list) and importance_rows:
            write_json(out_dir / importance_json_name, importance_rows)
            write_csv(out_dir / importance_csv_name, pd.DataFrame(importance_rows))
            _render_feature_importance_plot(importance_rows, plots_dir / importance_plot_name)
            write_json(
                plots_dir / f"{importance_plot_name}.json",
                {
                    "path": str(plots_dir / importance_plot_name),
                    "type": "feature_importance",
                    "model": model_name,
                    "source": str(model_path or ""),
                    "top_features": [str(item.get("feature", "")) for item in importance_rows[:10]],
                },
            )
            metrics["top_feature"] = str(importance_rows[0].get("feature", "")) if importance_rows else ""

        comparison_rows = [
            {"model": "majority_baseline", "metric": "accuracy", "value": float(majority_acc)},
            {"model": f"{model_name}_holdout", "metric": "accuracy", "value": float(metrics.get("test_accuracy", 0.0) or 0.0)},
            {"model": f"{model_name}_cross_validation", "metric": "mean_accuracy", "value": float(cv_payload.get("mean_accuracy", 0.0) or 0.0)},
            {"model": f"{model_name}_cross_validation", "metric": "std_accuracy", "value": float(cv_payload.get("std_accuracy", 0.0) or 0.0)},
        ]
        if "roc_auc" in metrics:
            comparison_rows.append({"model": model_name, "metric": "roc_auc", "value": float(metrics["roc_auc"])})
        if "pr_auc" in metrics:
            comparison_rows.append({"model": model_name, "metric": "pr_auc", "value": float(metrics["pr_auc"])})
        write_json(out_dir / comparison_json_name, comparison_rows)
        write_csv(out_dir / comparison_csv_name, pd.DataFrame(comparison_rows))
        write_json(
            out_dir / f"{comparison_csv_name}.json",
            {
                "path": str(out_dir / comparison_csv_name),
                "type": "model_performance_comparison",
                "model": model_name,
                "metrics": [str(row.get("metric", "")) for row in comparison_rows],
            },
        )

    write_json(out_dir / eval_name, payload)
    detail_payload = {"metrics": metrics, "cv": cv_payload, "validation_failure": failure_payload, "warning": leakage_warning}
    write_json(out_dir / detail_name, detail_payload)
    return {"module": "model_eval", "status": "ok", "output": str(out_dir / eval_name)}
