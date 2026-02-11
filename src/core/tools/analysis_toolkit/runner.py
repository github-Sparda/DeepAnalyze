from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import (
    data_profile,
    data_quality,
    stats_tests,
    correlation,
    feature_selection,
    normalization,
    plot_utils,
    outlier_detection,
    bootstrap,
    monte_carlo,
    regression,
    robust_stats,
    subgroup_analysis,
    multiple_testing,
    viz_gallery,
    viz_manhattan_volcano,
    viz_heatmap_cluster,
    viz_network,
    viz_comparison,
    survival_analysis,
    model_train,
    model_eval,
    batch_effect,
    dimensionality,
    clustering,
    viz_multivariate,
    viz_longitudinal,
    viz_stat_diagnostic,
    viz_facet_grid,
    viz_geospatial,
    viz_reporting,
    viz_interactive,
    viz_sankey,
    viz_chord,
    viz_top_features,
    viz_embedding,
)
from .common import ensure_dir, write_json

DEFAULT_STEPS = [
    "data_profile",
    "data_quality",
    "stats_tests",
    "correlation",
    "feature_selection",
]

MODULES = {
    "data_profile": data_profile,
    "data_quality": data_quality,
    "stats_tests": stats_tests,
    "correlation": correlation,
    "feature_selection": feature_selection,
    "normalization": normalization,
    "plot_utils": plot_utils,
    "outlier_detection": outlier_detection,
    "bootstrap": bootstrap,
    "monte_carlo": monte_carlo,
    "regression": regression,
    "robust_stats": robust_stats,
    "subgroup_analysis": subgroup_analysis,
    "multiple_testing": multiple_testing,
    "viz_gallery": viz_gallery,
    "viz_manhattan_volcano": viz_manhattan_volcano,
    "viz_heatmap_cluster": viz_heatmap_cluster,
    "viz_network": viz_network,
    "viz_comparison": viz_comparison,
    "survival_analysis": survival_analysis,
    "model_train": model_train,
    "model_eval": model_eval,
    "batch_effect": batch_effect,
    "dimensionality": dimensionality,
    "clustering": clustering,
    "viz_multivariate": viz_multivariate,
    "viz_longitudinal": viz_longitudinal,
    "viz_stat_diagnostic": viz_stat_diagnostic,
    "viz_facet_grid": viz_facet_grid,
    "viz_geospatial": viz_geospatial,
    "viz_reporting": viz_reporting,
    "viz_interactive": viz_interactive,
    "viz_sankey": viz_sankey,
    "viz_chord": viz_chord,
    "viz_top_features": viz_top_features,
    "viz_embedding": viz_embedding,
}


def run_step(module_name: str, input_path: str | Path, output_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
    module = MODULES.get(module_name)
    if module is None:
        return {"module": module_name, "status": "skipped", "message": "unknown module"}
    try:
        import inspect

        sig = inspect.signature(module.run)
        accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return module.run(input_path, output_dir, **accepted)
    except Exception:
        return module.run(input_path, output_dir)


def run_pipeline(input_path: str | Path, output_dir: str | Path, steps: list[str] | None = None) -> dict[str, Any]:
    output_dir = ensure_dir(output_dir)
    steps = steps or DEFAULT_STEPS
    results: dict[str, Any] = {"input": str(input_path), "steps": []}
    for step in steps:
        results["steps"].append(run_step(step, input_path, output_dir))
    write_json(Path(output_dir) / "summary.json", results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run analysis toolkit pipeline")
    parser.add_argument("--input", required=True, help="Input CSV/XLSX file")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--steps", nargs="*", default=None, help="Steps to run")
    args = parser.parse_args()
    run_pipeline(args.input, args.output_dir, args.steps)


if __name__ == "__main__":
    main()
