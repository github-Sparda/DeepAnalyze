from __future__ import annotations

import pytest
from pathlib import Path

pd = pytest.importorskip("pandas")

from deepanalyze.orchestration.visualization_planner import VisualizationPlanner


def test_visualization_planner_generates_instructions(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "category": ["a", "b", "a", "c"],
            "value": [1, 4, 5, 2],
            "score": [10, 8, 5, 6],
        }
    )
    dataset_path = tmp_path / "sample.csv"
    df.to_csv(dataset_path, index=False)
    datasets = [{"file": "sample.csv", "path": str(dataset_path)}]
    planner = VisualizationPlanner(tmp_path, max_items=5)
    instructions = planner.plan(datasets)

    assert instructions
    assert any(inst["type"] == "distribution" for inst in instructions)
    assert any(inst["type"] == "correlation" for inst in instructions)
    assert any(inst["type"] == "comparison" for inst in instructions)
    assert any(inst["type"] == "table" for inst in instructions)
