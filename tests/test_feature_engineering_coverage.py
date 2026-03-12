from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.analytics.feature_engineering import AutomatedFeatureEngineer, TimeSeriesFeatureEngineer


def _sample_feature_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "num1": [1.0, 2.0, np.nan, 4.0, 5.0],
            "num2": [10.0, 20.0, 30.0, 40.0, np.nan],
            "binary": ["yes", "no", "yes", "no", "yes"],
            "category": ["a", "b", "a", "c", np.nan],
            "text": ["lorem ipsum" * 10, "dolor" * 20, "sit" * 20, "amet" * 20, "x" * 80],
            "drop_me": [np.nan, np.nan, np.nan, 1.0, np.nan],
            "dt": pd.date_range("2026-01-01", periods=5, freq="D"),
            "target": [0, 1, 0, 1, 0],
        }
    )


def test_automated_feature_engineer_full_pipeline() -> None:
    df = _sample_feature_df()
    engineer = AutomatedFeatureEngineer(random_state=3)

    analysis = engineer.analyze_data_types(df)
    assert "num1" in analysis["numerical"]
    assert "category" in analysis["categorical"]
    assert "dt" in analysis["datetime"]
    assert "binary" in analysis["boolean"]
    assert "text" in analysis["text"]

    cleaned = engineer.handle_missing_values(df)
    assert "drop_me" not in cleaned.columns
    assert cleaned["num1"].isna().sum() == 0

    encoded = engineer.encode_categorical_features(cleaned[["binary", "category"]], ["binary", "category"])
    assert "binary" in encoded.columns
    assert any(col.startswith("category_") for col in encoded.columns)

    freq_df = pd.DataFrame({"city": [f"c{i}" for i in range(12)]})
    freq_encoded = engineer.encode_categorical_features(freq_df, ["city"])
    assert "city_freq" in freq_encoded.columns and "city" not in freq_encoded.columns

    numerical = cleaned[["num1", "num2"]].fillna(0)
    with_interactions = engineer.create_interaction_features(numerical, ["num1", "num2"], max_interactions=3)
    assert {"num1_x_num2", "num1_plus_num2"} <= set(with_interactions.columns)

    poly = engineer.create_polynomial_features(numerical, ["num1", "num2"], degree=3)
    assert {"num1_squared", "num1_cubed", "num1_sqrt"} <= set(poly.columns)

    scaled = engineer.scale_numerical_features(numerical, ["num1", "num2"], method="minmax")
    assert scaled["num1"].between(0, 1).all()

    pca_input = pd.DataFrame(np.random.RandomState(1).randn(8, 4), columns=list("abcd"))
    pca_df = engineer.apply_pca(pca_input, n_components=0.9)
    assert all(col.startswith("PC") for col in pca_df.columns)

    X = pd.DataFrame(np.random.RandomState(2).randn(30, 6), columns=[f"f{i}" for i in range(6)])
    y = pd.Series([0, 1] * 15)
    selected = engineer.select_k_best_features(X, y, k=3, task_type="classification")
    assert selected.shape[1] == 3

    engineered = engineer.engineer_dataframe(df.drop(columns=["text"]), target_column="target", feature_strategy="comprehensive")
    assert "target" not in engineered.columns
    assert engineer.feature_names_out

    report = engineer.get_feature_engineering_report()
    assert report["scalings_applied"] is True
    assert report["encodings_applied"] >= 1


def test_time_series_feature_engineer_generates_time_lag_and_rolling_features() -> None:
    ts = TimeSeriesFeatureEngineer()
    df = pd.DataFrame(
        {
            "when": pd.date_range("2026-01-01", periods=6, freq="D"),
            "value": [1, 2, 3, 4, 5, 6],
        }
    )

    time_df = ts.create_time_features(df, "when")
    assert {"when_year", "when_month_sin", "when_day_cos"} <= set(time_df.columns)

    lag_df = ts.create_lag_features(df, "value", lags=[1, 2])
    assert {"value_lag_1", "value_lag_2"} <= set(lag_df.columns)

    roll_df = ts.create_rolling_features(df, "value", windows=[2])
    assert {"value_rolling_mean_2", "value_rolling_std_2", "value_rolling_max_2"} <= set(roll_df.columns)
