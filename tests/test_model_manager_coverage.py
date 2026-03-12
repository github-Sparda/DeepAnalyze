from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from sklearn.datasets import load_iris, make_regression
from sklearn.linear_model import LinearRegression, LogisticRegression

from src.core.analytics.model_manager import ModelDeploymentHelper, ModelManager


def test_model_manager_save_load_update_compare_export_and_delete(tmp_path: Path) -> None:
    manager = ModelManager(tmp_path / "models")
    iris = load_iris(as_frame=True)
    X = iris.frame[iris.feature_names]
    y = (iris.target == 0).astype(int)
    model = LogisticRegression(max_iter=200).fit(X, y)

    model_id = manager.save_model(model, "iris-logistic", X_sample=X.head(5), metadata={"owner": "qa"})
    assert model_id in manager.registry

    loaded_model, metadata = manager.load_model(model_id)
    assert isinstance(loaded_model, LogisticRegression)
    assert metadata["model_name"] == "iris-logistic"
    assert metadata["metadata"]["owner"] == "qa"

    perf = manager.evaluate_model(loaded_model, X, y, cv=3)
    assert perf["scoring_metric"] in {"roc_auc", "accuracy"}
    assert "cv_mean" in perf and "roc_auc" in perf

    manager.update_model_performance(model_id, perf)
    comparison = manager.compare_models([model_id, "missing"])
    assert comparison.iloc[0]["model_name"] == "iris-logistic"

    listed = manager.list_models(model_name="iris", model_type="LogisticRegression")
    assert listed.iloc[0]["versions"] == 1

    best = manager.get_best_model(metric="cv_mean", model_type="LogisticRegression")
    assert best is not None and best[0] == model_id

    export_dir = tmp_path / "exported"
    exported = Path(manager.export_model(model_id, export_dir))
    assert (exported / "model.pkl").exists()
    assert (exported / "model_info.json").exists()
    assert "required_packages" in json.loads((exported / "model_info.json").read_text(encoding="utf-8"))
    assert "load_model" in (exported / "load_model.py").read_text(encoding="utf-8")

    assert manager.delete_model(model_id) is True
    assert manager.delete_model("missing") is False


def test_model_manager_errors_and_regression_metrics(tmp_path: Path) -> None:
    manager = ModelManager(tmp_path / "models")
    X_arr, y_arr = make_regression(n_samples=40, n_features=4, random_state=7)
    X = pd.DataFrame(X_arr, columns=list("abcd"))
    y = pd.Series(y_arr)
    model = LinearRegression().fit(X, y)
    model_id = manager.save_model(model, "linreg", X_sample=X.head(2))

    perf = manager.evaluate_model(model, X, y, cv=3)
    assert {"mse", "rmse", "mae", "cv_mean"} <= perf.keys()

    manager.update_model_performance(model_id, perf)
    best = manager.get_best_model(metric="mse")
    assert best is not None and best[0] == model_id

    with pytest.raises(FileNotFoundError):
        manager.load_model("missing")
    with pytest.raises(ValueError):
        manager.load_model(model_id, version=99)


def test_model_deployment_helper_outputs() -> None:
    api_code = ModelDeploymentHelper.create_prediction_api(object(), ["f1", "f2"])
    assert "/predict" in api_code
    assert "feature_names = ['f1', 'f2']" in api_code or 'feature_names = ["f1", "f2"]' in api_code

    card = ModelDeploymentHelper.create_model_card(
        {"model_name": "demo", "model_type": "LogisticRegression", "created_at": "2026-03-13", "model_id": "abc"},
        {"cv_mean": 0.91, "accuracy": 0.88},
    )
    assert "# Model Card: demo" in card
    assert "**accuracy**: 0.8800".lower() in card.lower()
