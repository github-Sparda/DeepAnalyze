from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.analytics.toolkit import viz_comparison, viz_longitudinal, viz_chord


def _write_sample_csv(path: Path) -> None:
    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "value": [1.2, 1.5, 2.3, 2.1],
            "time": [1, 2, 1, 2],
        }
    )
    df.to_csv(path, index=False)


def test_toolkit_visuals_delegate_to_core_layer(tmp_path: Path) -> None:
    data_path = tmp_path / "sample.csv"
    _write_sample_csv(data_path)

    comparison = viz_comparison.run(data_path, tmp_path, mode="box")
    assert comparison["status"] == "ok"
    comparison_path = Path(comparison["output"])
    assert comparison_path.exists()

    longitudinal = viz_longitudinal.run(data_path, tmp_path)
    assert longitudinal["status"] == "ok"
    longitudinal_path = Path(longitudinal["output"])
    assert longitudinal_path.exists()

    chord = viz_chord.run(str(data_path), str(tmp_path))
    assert chord["status"] == "ok"
    chord_path = Path(chord["output"])
    assert chord_path.exists()
    assert chord_path.suffix == ".html"
