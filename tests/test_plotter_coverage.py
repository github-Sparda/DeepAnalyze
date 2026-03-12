from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.visualization.plotter import (
    Plotter,
    create_plotter,
    render_chord_placeholder,
    render_comparison,
    render_correlation_heatmap,
    render_distribution,
    render_fallback_plot,
    render_group_comparison,
    render_trend,
)


def test_plotter_renders_static_and_interactive_outputs(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "y": [2, 3, 4, 5],
            "cat": ["A", "B", "A", "B"],
        }
    )

    dist = render_distribution(df, "x", tmp_path / "dist.png")
    corr = render_correlation_heatmap(df[["x", "y"]], tmp_path / "corr.png")
    trend = render_trend(df, "x", "y", tmp_path / "trend.png")
    comp = render_comparison(df, "cat", "y", tmp_path / "comp.png")
    group = render_group_comparison(df, "cat", "y", tmp_path / "group.png", mode="violin")
    fallback = render_fallback_plot(df, tmp_path / "fallback.png", note="Fallback")
    chord = render_chord_placeholder(tmp_path / "chord.html", "todo")

    for path in [dist, corr, trend, comp, group, fallback, chord]:
        assert Path(path).exists()

    meta = json.loads((tmp_path / "dist.png.json").read_text(encoding="utf-8"))
    assert meta["type"] == "distribution"

    html = render_distribution(df, "x", tmp_path / "dist.html", interactive=True)
    assert html.suffix == ".html"
    html2 = render_group_comparison(df, "cat", "y", tmp_path / "group.html", mode="bar", interactive=True)
    assert html2.suffix == ".html"


def test_plotter_dispatcher_and_fallback(tmp_path: Path) -> None:
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4], "cat": ["A", "B"]})
    plotter = create_plotter()
    assert isinstance(plotter, Plotter)
    assert plotter.plot(df, chart_type="line", x="x", y="y", output_path=tmp_path / "line.png").exists()
    assert plotter.plot(df, chart_type="bar", category="cat", value="y", output_path=tmp_path / "bar.png").exists()
    assert plotter.plot(df, chart_type="heatmap", output_path=tmp_path / "heat.png").exists()
    assert plotter.plot(df, chart_type="histogram", column="x", output_path=tmp_path / "hist.png").exists()
    assert plotter.plot(df, chart_type="unknown", output_path=tmp_path / "other.png").exists()
