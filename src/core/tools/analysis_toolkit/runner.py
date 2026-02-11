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
)
from .common import ensure_dir, write_json

DEFAULT_STEPS = [
    "data_profile",
    "data_quality",
    "stats_tests",
    "correlation",
    "feature_selection",
]


def run_pipeline(input_path: str | Path, output_dir: str | Path, steps: list[str] | None = None) -> dict[str, Any]:
    output_dir = ensure_dir(output_dir)
    steps = steps or DEFAULT_STEPS
    results: dict[str, Any] = {"input": str(input_path), "steps": []}
    for step in steps:
        if step == "data_profile":
            results["steps"].append(data_profile.run(input_path, output_dir))
        elif step == "data_quality":
            results["steps"].append(data_quality.run(input_path, output_dir))
        elif step == "stats_tests":
            results["steps"].append(stats_tests.run(input_path, output_dir))
        elif step == "correlation":
            results["steps"].append(correlation.run(input_path, output_dir))
        elif step == "feature_selection":
            results["steps"].append(feature_selection.run(input_path, output_dir))
        elif step == "normalization":
            results["steps"].append(normalization.run(input_path, output_dir))
        else:
            results["steps"].append({"module": step, "status": "skipped"})
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
