from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import (
    load_table,
    detect_group_column,
    load_analysis_runtime_config,
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
    from src.core.common import find_nearest_centroid
    return find_nearest_centroid(sample, centroids)


def _result_filename(base_name: str, artifact_prefix: str = "") -> str:
    prefix = str(artifact_prefix or "").strip()
    if not prefix:
        return base_name
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix
    return f"{stem}_{prefix}{suffix}"


def _prepare_model_frame(input_path: str | Path) -> tuple[pd.DataFrame, str | None, list[str], dict[str, Any], dict[str, Any]]:
    df = load_table(input_path)
    runtime_config = load_analysis_runtime_config(Path(input_path).resolve().parent)
    label_col = detect_group_column(df, runtime_config=runtime_config)
    num_cols = numeric_columns(df)
    if not label_col or not num_cols:
        return df, label_col, num_cols, runtime_config, {}
    group_series, group_info = select_group_labels(df[label_col], runtime_config=runtime_config)
    df = df.copy()
    df["_group_norm"] = group_series
    df = df[df["_group_norm"].notna()]
    return df, label_col, num_cols, runtime_config, group_info


def run(
    input_path: str | Path,
    output_dir: str | Path,
    method: str = "centroid",
    artifact_prefix: str = "",
) -> dict[str, Any]:
    df, label_col, num_cols, _runtime_config, group_info = _prepare_model_frame(input_path)
    out_dir = normalize_output_dir(output_dir, "result")
    model_result_name = _result_filename("model_results.json", artifact_prefix)
    mapping_name = _result_filename("analysis_label_mapping.json", artifact_prefix)
    health_name = _result_filename("label_health_report.json", artifact_prefix)
    if not label_col or not num_cols:
        payload = {"status": "skipped", "reason": "missing label or numeric columns", "method": method}
        write_json(out_dir / model_result_name, payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / model_result_name)}
    mapping = (
        pd.DataFrame({"raw_label": df[label_col].astype(str), "analysis_label": df["_group_norm"].astype(str)})
        .drop_duplicates()
        .sort_values(["analysis_label", "raw_label"])
    )
    write_json(
        out_dir / mapping_name,
        {
            "source_label_col": label_col,
            "analysis_label_col": "_group_norm",
            "group_info": group_info,
            "mappings": mapping.to_dict(orient="records"),
        },
    )
    labels = df["_group_norm"].astype(str)
    health = evaluate_label_health(labels)
    write_json(out_dir / health_name, health)
    if not health.get("valid", False):
        payload = {
            "status": "skipped",
            "reason": "label_invalid_for_modeling",
            "label_health": health,
            "method": method,
        }
        write_json(out_dir / model_result_name, payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / model_result_name)}
    data = df[num_cols].fillna(0).to_numpy()
    rng = np.random.default_rng(0)
    indices = np.arange(len(df))
    rng.shuffle(indices)
    split = int(len(indices) * 0.8) if len(indices) > 1 else len(indices)
    train_idx = indices[:split]
    test_idx = indices[split:] if split < len(indices) else indices[:split]
    train_df = df.iloc[train_idx]
    test_df = df.iloc[test_idx] if len(test_idx) else train_df
    X_train = train_df[num_cols].fillna(0).to_numpy()
    X_test = test_df[num_cols].fillna(0).to_numpy()
    y_train = train_df["_group_norm"].astype(str).to_numpy()
    y_test = test_df["_group_norm"].astype(str).to_numpy()

    if method == "centroid":
        centroids = _compute_centroids(train_df, "_group_norm", num_cols)
        train_pred = [
            _predict_centroid(train_df[num_cols].iloc[i].fillna(0).to_numpy(), centroids)
            for i in range(len(train_df))
        ]
        test_pred = [
            _predict_centroid(test_df[num_cols].iloc[i].fillna(0).to_numpy(), centroids)
            for i in range(len(test_df))
        ]
        train_acc = float(np.mean(y_train == np.array(train_pred))) if len(train_df) else 0.0
        test_acc = float(np.mean(y_test == np.array(test_pred))) if len(test_df) else 0.0
        payload = {
            "model": method,
            "label_col": label_col,
            "random_seed": 0,
            "numeric_features": num_cols,
            "train_size": int(len(train_df)),
            "test_size": int(len(test_df)),
            "group_info": group_info,
            "train_accuracy": train_acc,
            "test_accuracy": test_acc,
            "centroids": centroids,
            "n_samples": int(len(df)),
        }
        write_json(out_dir / model_result_name, payload)
        return {"module": "model_train", "status": "ok", "output": str(out_dir / model_result_name)}

    try:
        from sklearn.ensemble import RandomForestClassifier  # type: ignore
        from sklearn.linear_model import LogisticRegression  # type: ignore
        from sklearn.pipeline import make_pipeline  # type: ignore
        from sklearn.preprocessing import StandardScaler  # type: ignore
    except Exception as exc:
        payload = {
            "status": "skipped",
            "reason": "sklearn_unavailable",
            "method": method,
            "error": str(exc),
        }
        write_json(out_dir / model_result_name, payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / model_result_name)}

    if method == "logistic":
        estimator = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, solver="liblinear", random_state=0),
        )
    elif method == "random_forest":
        estimator = RandomForestClassifier(n_estimators=300, random_state=0)
    else:
        payload = {"status": "skipped", "reason": "unsupported_method", "method": method}
        write_json(out_dir / model_result_name, payload)
        return {"module": "model_train", "status": "skipped", "output": str(out_dir / model_result_name)}

    estimator.fit(X_train, y_train)
    train_pred = estimator.predict(X_train)
    test_pred = estimator.predict(X_test)
    classes = [str(x) for x in getattr(estimator, "classes_", [])]
    positive_label = classes[-1] if classes else ""
    train_score = None
    test_score = None
    if len(classes) == 2 and hasattr(estimator, "predict_proba"):
        proba_train = estimator.predict_proba(X_train)
        proba_test = estimator.predict_proba(X_test)
        pos_index = classes.index(positive_label)
        train_score = [float(x) for x in proba_train[:, pos_index]]
        test_score = [float(x) for x in proba_test[:, pos_index]]
    elif hasattr(estimator, "decision_function"):
        train_score = [float(x) for x in estimator.decision_function(X_train)]
        test_score = [float(x) for x in estimator.decision_function(X_test)]

    feature_importance: list[dict[str, Any]] = []
    final_estimator = estimator.steps[-1][1] if hasattr(estimator, "steps") else estimator
    if hasattr(final_estimator, "coef_"):
        coef = np.ravel(final_estimator.coef_[0] if np.ndim(final_estimator.coef_) > 1 else final_estimator.coef_)
        feature_importance = [
            {"feature": feature, "importance": float(abs(value)), "signed_importance": float(value)}
            for feature, value in zip(num_cols, coef)
        ]
    elif hasattr(final_estimator, "feature_importances_"):
        feature_importance = [
            {"feature": feature, "importance": float(value)}
            for feature, value in zip(num_cols, np.ravel(final_estimator.feature_importances_))
        ]
    feature_importance = sorted(feature_importance, key=lambda item: float(item.get("importance", 0.0)), reverse=True)

    payload = {
        "model": method,
        "label_col": label_col,
        "random_seed": 0,
        "numeric_features": num_cols,
        "train_size": int(len(train_df)),
        "test_size": int(len(test_df)),
        "group_info": group_info,
        "train_accuracy": float(np.mean(y_train == train_pred)) if len(y_train) else 0.0,
        "test_accuracy": float(np.mean(y_test == test_pred)) if len(y_test) else 0.0,
        "classes": classes,
        "positive_label": positive_label,
        "n_samples": int(len(df)),
        "train_truth": [str(x) for x in y_train],
        "test_truth": [str(x) for x in y_test],
        "train_pred": [str(x) for x in train_pred],
        "test_pred": [str(x) for x in test_pred],
        "train_score": train_score or [],
        "test_score": test_score or [],
        "feature_importance": feature_importance,
    }
    write_json(out_dir / model_result_name, payload)
    return {"module": "model_train", "status": "ok", "output": str(out_dir / model_result_name)}
