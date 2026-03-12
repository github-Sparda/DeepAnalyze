from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import load_iris, make_regression
from sklearn.linear_model import LogisticRegression

from src.core.analytics.ml_pipeline import FeatureEngineer, MLPipeline


def test_ml_pipeline_classification_fit_predict_and_report(monkeypatch) -> None:
    iris = load_iris(as_frame=True)
    X = iris.frame[iris.feature_names].copy()
    X["petal_band"] = np.where(X["petal length (cm)"] > 3, "high", "low")
    y = (iris.target == 0).astype(int)

    pipeline = MLPipeline(task_type="auto", random_state=11)
    result = pipeline.fit(X, y, test_size=0.25, optimize=False)

    assert result["task_type"] == "classification"
    assert result["best_model"] in result["model_scores"]
    preds = pipeline.predict(X.head(5))
    assert len(preds) == 5

    importance = pipeline.get_feature_importance()
    assert importance is not None and not importance.empty
    report = pipeline.generate_model_report()
    assert report["best_model"] == result["best_model"]
    assert report["feature_importance"]

    pipeline.best_model = LogisticRegression()
    pipeline.preprocessor = type("SimplePreprocessor", (), {"get_feature_names_out": lambda self: np.array(["f1", "f2"])})()
    pipeline.feature_names = ["f1", "f2"]
    pipeline.is_fitted = True
    pipeline.best_model.coef_ = np.array([[0.5, -0.2]])
    importance = pipeline.get_feature_importance()
    assert list(importance["feature"]) == ["f1", "f2"]


def test_ml_pipeline_regression_and_hyperparameter_optimization(monkeypatch) -> None:
    X_arr, y_arr = make_regression(n_samples=120, n_features=5, random_state=5)
    X = pd.DataFrame(X_arr, columns=[f"x{i}" for i in range(5)])
    y = pd.Series(y_arr)

    pipeline = MLPipeline(task_type="auto", random_state=5)

    class DummySearch:
        def __init__(self, model, params, cv, scoring, n_jobs):
            self.best_estimator_ = model

        def fit(self, X, y):
            return self

    monkeypatch.setattr("src.core.analytics.ml_pipeline.GridSearchCV", DummySearch)
    result = pipeline.fit(X, y, optimize=True)
    assert result["task_type"] == "regression"
    assert pipeline.best_model is not None

    names = pipeline._get_feature_names_after_preprocessing()
    assert len(names) >= 1
    assert pipeline.generate_model_report()["best_score"] == pytest.approx(float(pipeline.best_score))


def test_ml_pipeline_prediction_and_feature_engineer_helpers() -> None:
    pipeline = MLPipeline(task_type="classification")
    with pytest.raises(ValueError):
        pipeline.predict(pd.DataFrame({"x": [1, 2]}))

    y = pd.Series(["a", "b", "a", "b"])
    assert pipeline.detect_task_type(y) == "classification"

    engineer = FeatureEngineer()
    df = pd.DataFrame(
        {
            "a": [1.0, 2.0, np.nan, 4.0],
            "b": [3.0, 4.0, 5.0, 6.0],
            "c": [7.0, 8.0, 9.0, 10.0],
            "target": [0, 1, 0, 1],
        }
    )
    engineered = engineer.engineer_features(df, "target")
    assert "a_x_b" in engineered.columns
    assert engineered["a"].isna().sum() == 0

    selected_num = engineer.select_features(engineered.drop(columns=["target"]), engineered["target"], k=3)
    assert len(selected_num) == 3

    selected_cat = engineer.select_features(
        pd.DataFrame({"x1": [1, 2, 3, 4], "x2": [2, 2, 3, 5], "x3": [9, 8, 7, 6]}),
        pd.Series(["A", "A", "B", "B"]),
        k=2,
    )
    assert len(selected_cat) == 2
