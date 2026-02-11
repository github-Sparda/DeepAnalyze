from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.core.analytics.toolkit.runner import run_step


def _load_config(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(output_dir: Path) -> Path:
    manifest = {
        "profile": [],
        "result": [],
        "plots": [],
    }
    for key in manifest.keys():
        folder = output_dir / key
        if not folder.exists():
            continue
        manifest[key] = [str(p.relative_to(output_dir)) for p in sorted(folder.iterdir()) if p.is_file()]
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run analysis_toolkit example pipeline")
    parser.add_argument(
        "--config",
        default="scripts/analysis_toolkit_example_config.json",
        help="Path to example config JSON",
    )
    args = parser.parse_args()

    config = _load_config(Path(args.config))
    input_path = Path(config.get("input_path", ""))
    output_dir = Path(config.get("output_dir", "outputs/analysis_toolkit_examples"))
    steps = config.get("steps") or []
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    for step in steps:
        if step == "viz_heatmap_cluster":
            correlation_csv = output_dir / "result" / "correlation.csv"
            run_step(step, correlation_csv, output_dir, mode="heatmap")
            continue
        if step == "viz_manhattan_volcano":
            stats_json = output_dir / "result" / "stats_results.json"
            run_step(step, stats_json, output_dir, mode="volcano")
            continue
        run_step(step, input_path, output_dir)

    manifest_path = _write_manifest(output_dir)
    print(f"OK - analysis_toolkit example completed. Output: {output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
