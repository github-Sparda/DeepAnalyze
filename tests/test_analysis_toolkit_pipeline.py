from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.tools.analysis_toolkit.runner import run_pipeline


def test_analysis_toolkit_pipeline_minimal(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "Group": ["Normal1", "Normal2", "Generalized1", "Generalized2"],
            "peak1": [0.1, 0.12, 0.9, 0.95],
            "peak2": [0.05, 0.06, 0.8, 0.85],
        }
    )
    input_path = tmp_path / "sample.csv"
    df.to_csv(input_path, index=False)

    run_pipeline(input_path, tmp_path, steps=["data_profile", "stats_tests", "feature_selection"])

    assert (tmp_path / "profile" / "data_profile.json").exists()
    assert (tmp_path / "result" / "stats_results.json").exists()
    assert (tmp_path / "result" / "feature_selection.json").exists()
