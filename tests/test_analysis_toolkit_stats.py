from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.analytics.toolkit import stats_tests


def test_stats_tests_group_normalization(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "Group": [
                "Normal1",
                "Normal2",
                "Normal3",
                "Focal1",
                "Generalized1",
                "Generalized2",
            ],
            "peak1": [0.1, 0.12, 0.11, 0.5, 0.6, 0.62],
            "peak2": [0.05, 0.07, 0.06, 0.4, 0.45, 0.48],
        }
    )
    input_path = tmp_path / "sample.csv"
    df.to_csv(input_path, index=False)

    stats_tests.run(input_path, tmp_path)

    group_info_path = tmp_path / "result" / "stats_group_info.json"
    assert group_info_path.exists()
    group_info = json.loads(group_info_path.read_text(encoding="utf-8"))
    assert group_info["method"] == "reference_vs_others"
    assert group_info["used_groups"] == ["Normal", "Case"]

    results_path = tmp_path / "result" / "stats_results.json"
    assert results_path.exists()
    results = pd.read_json(results_path)
    assert set(results["group_a"].unique().tolist()) == {"Normal"}
    assert set(results["group_b"].unique().tolist()) == {"Case"}
    assert "p_value" in results.columns
