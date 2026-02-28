from __future__ import annotations

import json
from pathlib import Path

from src.core.analytics.toolkit.runner import run_step


def test_run_step_maps_method_to_mode_for_visual_modules(tmp_path: Path) -> None:
    rows = [
        {"feature": "f1", "p_value": 0.01, "mean_diff": 1.2},
        {"feature": "f2", "p_value": 0.2, "mean_diff": -0.3},
    ]
    input_path = tmp_path / "stats_results.json"
    input_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    result = run_step("viz_manhattan_volcano", input_path, tmp_path, method="manhattan")
    assert result["status"] == "ok"
    assert (tmp_path / "plots" / "manhattan_plot.png").exists()


def test_run_step_maps_method_to_mode_for_heatmap_cluster(tmp_path: Path) -> None:
    input_path = tmp_path / "correlation.csv"
    input_path.write_text("index,a,b\na,1,0.5\nb,0.5,1\n", encoding="utf-8")

    result = run_step("viz_heatmap_cluster", input_path, tmp_path, method="heatmap_cluster")
    assert result["status"] == "ok"
    assert (tmp_path / "plots" / "heatmap_cluster.png").exists()
