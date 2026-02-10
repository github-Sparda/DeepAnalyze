#!/usr/bin/env python3
"""
Smoke test for AnalysisPipeline using a real dataset.
This executes the pipeline and validates that core artifacts are produced.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.analysis_pipeline import AnalysisPipeline


def main() -> int:
    data_file = project_root / "data" / "examples" / "simpson_paradox_analysis" / "data" / "Simpson.csv"
    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        return 1

    pipeline = AnalysisPipeline()
    results = pipeline.run_complete_analysis(str(data_file))

    report_path = Path(results.get("final_report", ""))
    if not report_path.exists():
        print("Report missing.")
        return 1

    artifacts = results.get("artifacts", [])
    if not artifacts:
        print("No artifacts produced.")
        return 1

    missing = [a for a in artifacts if not Path(a).exists()]
    if missing:
        print("Missing artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    print("AnalysisPipeline smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
