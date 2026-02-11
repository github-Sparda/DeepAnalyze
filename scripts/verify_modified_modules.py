from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.core.reporting.assembler import ReportAssembler
from src.core.tools.analysis_toolkit import (
    stats_tests,
    feature_selection,
    model_train,
    model_eval,
)
from src.core.tools.analysis_toolkit.runner import run_step


def _make_sample_csv(path: Path) -> None:
    df = pd.DataFrame(
        {
            "Group": ["Normal1", "Normal2", "Generalized1", "Generalized2", "Focal1", "Focal2"],
            "peak1": [0.1, 0.12, 0.9, 0.95, 0.5, 0.55],
            "peak2": [0.05, 0.06, 0.8, 0.85, 0.4, 0.45],
        }
    )
    df.to_csv(path, index=False)


def _assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing {label}: {path}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        input_path = base / "sample.csv"
        _make_sample_csv(input_path)

        # stats tests + group normalization
        stats_tests.run(input_path, base)
        _assert_exists(base / "result" / "stats_results.json", "stats results")
        _assert_exists(base / "result" / "stats_group_info.json", "stats group info")
        group_info = json.loads((base / "result" / "stats_group_info.json").read_text(encoding="utf-8"))
        if group_info.get("method") != "normal_vs_case":
            raise SystemExit(f"Unexpected group normalization method: {group_info.get('method')}")

        # correlation + dimensionality for viz
        run_step("correlation", input_path, base)
        run_step("dimensionality", input_path, base, method="pca")

        # feature selection (p_value path)
        feature_selection.run(input_path, base, method="p_value")
        _assert_exists(base / "result" / "feature_selection.json", "feature selection")
        _assert_exists(base / "result" / "feature_selection_rationale.json", "feature selection rationale")

        # multiple testing + summary/table exports
        run_step("multiple_testing", base / "result" / "stats_results.json", base, pval_field="p_value")
        stats_df = pd.read_json(base / "result" / "stats_results.json")
        if (base / "result" / "multiple_testing.json").exists():
            mt_df = pd.read_json(base / "result" / "multiple_testing.json")
            if "q_value" in mt_df.columns:
                stats_df = stats_df.merge(mt_df[["feature", "q_value"]], on="feature", how="left")
        stats_df.to_json(base / "result" / "stats_summary.json", orient="records", force_ascii=False)
        top_df = stats_df.sort_values("p_value").head(10)
        top_df.to_json(base / "result" / "top_features.json", orient="records", force_ascii=False)

        # modeling baseline
        model_train.run(input_path, base, method="centroid")
        _assert_exists(base / "result" / "model_results.json", "model results")
        model_eval.run(input_path, base, model_path=base / "result" / "model_results.json")
        _assert_exists(base / "result" / "model_eval.json", "model eval")

        # visualization outputs
        run_step("viz_manhattan_volcano", base / "result" / "stats_results.json", base, mode="volcano")
        run_step("viz_top_features", base / "result" / "stats_results.json", base)
        run_step("viz_heatmap_cluster", base / "result" / "correlation.csv", base, mode="heatmap")
        run_step("viz_embedding", base / "result" / "dimensionality.json", base, name="embedding_pca")
        _assert_exists(base / "plots" / "volcano_plot.png", "volcano plot")

        # report assembly: embed visuals and table previews
        manifest = {
            "visualizations": [
                {"name": "volcano", "relative_path": "plots/volcano_plot.png"},
                {"name": "heatmap", "relative_path": "plots/heatmap.png"},
                {"name": "embedding", "relative_path": "plots/embedding_pca.png"},
            ],
            "tables": [
                {"name": "top_features.json", "relative_path": "result/top_features.json"},
                {"name": "stats_summary.json", "relative_path": "result/stats_summary.json"},
                {"name": "model_eval.json", "relative_path": "result/model_eval.json"},
            ],
        }
        report_payload = {
            "title": "Verification",
            "summary": "Summary",
            "sections": [
                {"title": "差异分析", "body": "diff"},
                {"title": "相关性分析", "body": "corr"},
                {"title": "聚类与降维", "body": "embed"},
            ],
        }
        assembler = ReportAssembler(language="zh")
        html = assembler.assemble(
            outline="",
            analysis_md="analysis",
            document_manifest=manifest,
            report_payload=report_payload,
            execution_warning="",
        )
        if "../plots/volcano_plot.png" not in html:
            raise SystemExit("Report did not embed volcano plot.")
        if "table-preview" not in html:
            raise SystemExit("Report did not embed table preview blocks.")

    print("OK - modified modules verified")


if __name__ == "__main__":
    main()
