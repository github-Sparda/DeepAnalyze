from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.orchestration import graph as orchestration_graph


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_hypothesis_matrix_and_coverage_report(tmp_path: Path) -> None:
    session_dir = tmp_path
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    stats_df = pd.DataFrame(
        {
            "feature": ["peak1", "peak2"],
            "p_value": [0.01, 0.2],
            "mean_diff": [0.1, -0.05],
        }
    )
    stats_df.to_json(result_dir / "stats_results.json", orient="records")

    quality_payload = {
        "datasets": [
            {
                "stats": {
                    "Group": {"mean": None},
                    "peak1": {"mean": 0.1},
                    "peak2": {"mean": 0.2},
                    "peak3": {"mean": 0.3},
                }
            }
        ]
    }
    _write_json(result_dir / "data_quality.json", quality_payload)

    hypothesis_payload = {
        "hypotheses": [
            {
                "hypothesis": "H1",
                "expected_artifacts": ["stats_results.json"],
                "missing": [],
                "steps": {"stats_tests": {"status": "ok"}},
            },
            {
                "hypothesis": "H2",
                "expected_artifacts": ["feature_selection.json"],
                "missing": ["feature_selection.json"],
                "steps": {},
            },
        ]
    }

    matrix = orchestration_graph._build_hypothesis_matrix(hypothesis_payload)
    assert matrix["hypotheses"][0]["status"] == "ok"
    assert matrix["hypotheses"][1]["status"] in {"partial", "failed"}

    coverage = orchestration_graph._build_coverage_report(session_dir)
    assert "peak1" in coverage["analyzed_features"]
    assert "peak3" in coverage["missing_features"]


def test_visual_binding(tmp_path: Path) -> None:
    session_dir = tmp_path
    (session_dir / "plots").mkdir(parents=True, exist_ok=True)
    (session_dir / "plots" / "volcano_plot.png").write_text("x")

    binding = orchestration_graph._build_visual_binding(session_dir)
    assert any(b["artifact"].endswith("volcano_plot.png") for b in binding["bindings"])


def test_validation_failure_report(tmp_path: Path) -> None:
    session_dir = tmp_path
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    _write_json(result_dir / "validation_failures.json", {"stage": "cv", "error": "boom"})
    plots_dir = session_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    (plots_dir / "dummy.png").write_text("x")

    from src.core.reporting.assembler import ReportAssembler

    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [
                {"name": "dummy", "path": str(plots_dir / "dummy.png"), "relative_path": "plots/dummy.png"}
            ],
            "tables": [],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "验证失败" in html or "失败" in html


def test_multipath_payload_and_contract(tmp_path: Path) -> None:
    session_dir = tmp_path
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "stats_results.json").write_text("[]", encoding="utf-8")
    (result_dir / "multiple_testing.json").write_text("[]", encoding="utf-8")

    plan_json = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "H1: 差异检验",
                "hypothesis": "组间差异",
                "validation_plan_steps": ["A", "B"],
                "expected_artifacts": ["stats_results.json"],
                "validation_paths": [
                    {
                        "path_id": "path_a",
                        "method_family": "parametric_test",
                        "steps": ["A"],
                        "expected_artifacts": ["stats_results.json"],
                    },
                    {
                        "path_id": "path_b",
                        "method_family": "nonparametric_or_fdr",
                        "steps": ["B"],
                        "expected_artifacts": ["multiple_testing.json"],
                    },
                ],
            }
        ]
    }
    evidence_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "evidence_sources": ["result/stats_results.json", "result/multiple_testing.json"],
                "quant_metrics": {"significant_p_lt_0_05": 2},
                "status": "supported",
            }
        ]
    }
    contrast_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "path_a": {"path_id": "path_a", "status": "ok", "metrics": {"significant_p_lt_0_05": 2}},
                "path_b": {"path_id": "path_b", "status": "ok", "metrics": {"q_lt_0_05": 2}},
                "consistency": "consistent",
                "status": "validated",
                "conflict_reason": "",
            }
        ]
    }
    multipath = orchestration_graph._evaluate_hypothesis_validation_paths(
        session_dir, plan_json, evidence_payload, contrast_payload
    )
    assert multipath["stats"]["total_hypotheses"] == 1
    assert multipath["hypotheses"][0]["status"] in {"validated", "partial"}

    contract = orchestration_graph._build_hypothesis_validation_contract(
        plan_json, contrast_payload, multipath
    )
    assert contract["hypotheses"][0]["has_dual_paths"] is True
    assert contract["hypotheses"][0]["dual_paths_executed"] is True


def test_multipath_status_partial_when_primary_failed(tmp_path: Path) -> None:
    session_dir = tmp_path
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    # only secondary artifact exists
    (result_dir / "multiple_testing.json").write_text("[]", encoding="utf-8")
    plan_json = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "H1: 差异检验",
                "hypothesis": "组间差异",
                "validation_plan_steps": ["A", "B"],
                "expected_artifacts": ["stats_results.json", "multiple_testing.json"],
                "validation_paths": [
                    {
                        "path_id": "path_a",
                        "method_family": "parametric_test",
                        "steps": ["A"],
                        "expected_artifacts": ["stats_results.json"],
                    },
                    {
                        "path_id": "path_b",
                        "method_family": "nonparametric_or_fdr",
                        "steps": ["B"],
                        "expected_artifacts": ["multiple_testing.json"],
                    },
                ],
            }
        ]
    }
    evidence_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "evidence_sources": ["result/multiple_testing.json"],
                "quant_metrics": {"q_lt_0_05": 1},
                "status": "partial",
            }
        ]
    }
    contrast_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "path_a": {"path_id": "path_a", "status": "missing", "metrics": {}},
                "path_b": {"path_id": "path_b", "status": "ok", "metrics": {"q_lt_0_05": 1}},
                "consistency": "unknown",
                "status": "partial",
                "conflict_reason": "",
            }
        ]
    }
    multipath = orchestration_graph._evaluate_hypothesis_validation_paths(
        session_dir, plan_json, evidence_payload, contrast_payload
    )
    assert multipath["hypotheses"][0]["status"] == "partial"
    assert any(p["status"] == "failed" for p in multipath["hypotheses"][0]["paths"])
    assert any(p["status"] in {"validated", "partial"} for p in multipath["hypotheses"][0]["paths"])
    assert multipath["hypotheses"][0]["recovery_action"] == "retry_secondary_or_code_repair"
