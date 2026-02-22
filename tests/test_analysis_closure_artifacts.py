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


def test_analysis_quality_score_and_traces(tmp_path: Path) -> None:
    session_dir = tmp_path
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        result_dir / "hypothesis_evidence_pack.json",
        {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "quant_metrics": [{"name": "m1", "value": 1}, {"name": "m2", "value": 2}],
                    "evidence_sources": ["result/stats_results.json"],
                }
            ]
        },
    )
    _write_json(
        result_dir / "hypothesis_validation_contract.json",
        {"hypotheses": [{"hypothesis_id": "H1", "executed_status": "validated"}]},
    )
    _write_json(
        result_dir / "hypothesis_contrast.json",
        {"hypotheses": [{"hypothesis_id": "H1", "consistency": "consistent", "conflict_reason": ""}]},
    )
    _write_json(
        result_dir / "hypothesis_multipath.json",
        {"hypotheses": [{"hypothesis_id": "H1", "status": "partial"}]},
    )
    (result_dir / "analysis_results.md").write_text("包含数值 m1=1。另一句没有数值", encoding="utf-8")
    quality = orchestration_graph._build_analysis_quality_score(session_dir)
    trace = orchestration_graph._build_evidence_trace(session_dir)
    reasons = orchestration_graph._build_reason_code_summary(session_dir)
    assert quality["quant_metric_ge_2_rate"] == 1.0
    assert quality["hypothesis_closure_rate"] == 1.0
    assert trace["hypotheses"][0]["hypothesis_id"] == "H1"
    assert reasons["hypotheses"][0]["reason_code"] == "execution_error"


def test_plan_and_codegen_contract_validators() -> None:
    valid_plan = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "H1: test",
                "hypothesis": "test hypothesis",
                "expected_artifacts": ["result/stats_results.json"],
                "minimum_evidence_requirements": {"quant_metrics_min": 2},
                "validation_paths": [
                    {"path_id": "path_a", "expected_artifacts": ["result/stats_results.json"]},
                    {"path_id": "path_b", "expected_artifacts": ["result/multiple_testing.json"]},
                ],
            }
        ]
    }
    ok, errors = orchestration_graph._validate_plan_json_contract(valid_plan)
    assert ok is True
    assert errors == []

    bad_plan = {"hypotheses": [{"id": "bad", "validation_paths": []}]}
    ok2, errors2 = orchestration_graph._validate_plan_json_contract(bad_plan)
    assert ok2 is False
    assert errors2

    ok3, errors3 = orchestration_graph._validate_codegen_steps(
        [{"filename": "a.py", "code": "print(1)"}]
    )
    assert ok3 is True
    assert errors3 == []

    ok4, errors4 = orchestration_graph._validate_codegen_steps([{"filename": "", "code": ""}])
    assert ok4 is False
    assert errors4


def test_normalized_plan_contains_evidence_requirements() -> None:
    normalized = orchestration_graph._normalize_plan_json(
        {"hypotheses": [{"id": "H1", "title": "H1", "hypothesis": "x", "validation_plan_steps": ["s1"], "expected_artifacts": ["a.json"]}]},
        "### 1. 假设列表\n- H1\n",
    )
    hyp = normalized["hypotheses"][0]
    assert "minimum_evidence_requirements" in hyp
    assert hyp["minimum_evidence_requirements"]["quant_metrics_min"] == 2
    assert "assumption_checks" in hyp


def test_normalized_plan_does_not_infer_from_markdown_sections() -> None:
    normalized = orchestration_graph._normalize_plan_json(
        {},
        "### 1. 假设列表\n- H1\n### 4. 成功判据\n- xxx\n",
    )
    assert normalized["hypotheses"] == []


def test_hypothesis_set_consistency_detects_mismatch(tmp_path: Path) -> None:
    session_dir = tmp_path
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    _write_json(
        session_dir / "plan" / "analysis_plan.json",
        {"hypotheses": [{"id": "H1", "title": "t", "hypothesis": "x", "validation_paths": [{"path_id": "path_a"}, {"path_id": "path_b"}]}]},
    )
    _write_json(session_dir / "result" / "hypothesis_results.json", {"hypotheses": [{"hypothesis": "H1"}]})
    _write_json(session_dir / "result" / "hypothesis_multipath.json", {"hypotheses": [{"hypothesis_id": "H1"}]})
    _write_json(session_dir / "result" / "hypothesis_evidence_pack.json", {"hypotheses": []})
    _write_json(session_dir / "result" / "hypothesis_gate_report.json", {"hypotheses": []})
    (session_dir / "report" / "report_v1.html").write_text("<h3>H1</h3>", encoding="utf-8")
    consistency = orchestration_graph._build_hypothesis_set_consistency(session_dir)
    assert consistency["satisfied"] is False
    assert "evidence_pack_ids" in consistency["mismatches"]


def test_strict_markdown_hypothesis_fallback_ignores_sections() -> None:
    plan_md = (
        "* **假设 H1（差异性假设）**：A 与 B 存在差异。\n"
        "* **假设 H2（分类假设）**：可以区分。\n"
        "#### 4. 成功判据\n"
        "- AUC > 0.8\n"
        "| 假设 | 路径 A | 路径 B |\n"
        "| H1 | s1 | result/stats_results.json |\n"
        "| H2 | s2 | result/model_eval.json |\n"
    )
    payload = orchestration_graph._strict_markdown_hypothesis_fallback(plan_md)
    hypotheses = payload.get("hypotheses", [])
    assert len(hypotheses) == 2
    assert [h["id"] for h in hypotheses] == ["H1", "H2"]


def test_strict_markdown_hypothesis_fallback_accepts_numeric_form() -> None:
    plan_md = (
        "#### **假设 1：A 与 B 差异显著。**\n"
        "#### **假设 2：可用于分类。**\n"
    )
    payload = orchestration_graph._strict_markdown_hypothesis_fallback(plan_md)
    assert [h["id"] for h in payload.get("hypotheses", [])] == ["H1", "H2"]


def test_find_first_dataset_prefers_tabular_over_manifest(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data.xlsx").write_text("x", encoding="utf-8")
    picked = orchestration_graph._find_first_dataset(tmp_path)
    assert picked is not None
    assert picked.name == "data.xlsx"


def test_has_advanced_artifacts_ignores_expected_artifact_validation(tmp_path: Path) -> None:
    result_dir = tmp_path / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "summary.json").write_text("{}", encoding="utf-8")
    (result_dir / "expected_artifact_validation.json").write_text("{}", encoding="utf-8")
    assert orchestration_graph._has_advanced_artifacts(tmp_path) is False


def test_extract_hypothesis_ids_from_report_prefers_headings(tmp_path: Path) -> None:
    report = tmp_path / "report_v1.html"
    report.write_text(
        "### H1 差异\n正文提及 H4 但不是章节。\n<h3>H2 分类</h3>\n",
        encoding="utf-8",
    )
    ids = orchestration_graph._extract_hypothesis_ids_from_report(report)
    assert ids == ["H1", "H2"]


def test_plan_validator_rejects_duplicate_path_id_and_missing_requirements() -> None:
    bad_plan = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "H1",
                "hypothesis": "x",
                "expected_artifacts": ["result/a.json"],
                "validation_paths": [
                    {"path_id": "path_a", "expected_artifacts": ["result/a.json"]},
                    {"path_id": "path_a", "expected_artifacts": ["result/b.json"]},
                ],
            }
        ]
    }
    ok, errors = orchestration_graph._validate_plan_json_contract(bad_plan)
    assert ok is False
    assert any("duplicate_validation_path_id" in e for e in errors)
    assert any("missing_minimum_evidence_requirements" in e for e in errors)


def test_plan_validation_suggestions_generated() -> None:
    suggestions = orchestration_graph._plan_validation_suggestions(
        [
            "missing_hypotheses",
            "hypothesis[0]_missing_dual_validation_paths",
            "hypothesis[0]_non_path_like_expected_artifacts:1",
        ]
    )
    assert suggestions
    assert any("两条验证路径" in s for s in suggestions)


def test_multipath_stats_split_invalid_vs_missing_artifacts(tmp_path: Path) -> None:
    session_dir = tmp_path
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "stats_results.json").write_text("[]", encoding="utf-8")
    plan_json = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "H1",
                "hypothesis": "x",
                "validation_plan_steps": ["A", "B"],
                "expected_artifacts": ["result/stats_results.json"],
                "invalid_expected_artifacts": ["显著结果输出"],
                "validation_paths": [
                    {"path_id": "path_a", "method_family": "parametric_test", "steps": ["A"], "expected_artifacts": ["result/stats_results.json"]},
                    {"path_id": "path_b", "method_family": "nonparametric_or_fdr", "steps": ["B"], "expected_artifacts": ["result/missing.json"]},
                ],
            }
        ]
    }
    evidence_payload = {"hypotheses": [{"hypothesis_id": "H1", "evidence_sources": [], "quant_metrics": {}, "status": "partial"}]}
    contrast_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "path_a": {"status": "ok", "metrics": {}},
                "path_b": {"status": "missing", "metrics": {}},
                "consistency": "unknown",
                "status": "partial",
                "conflict_reason": "",
            }
        ]
    }
    payload = orchestration_graph._evaluate_hypothesis_validation_paths(session_dir, plan_json, evidence_payload, contrast_payload)
    assert payload["stats"]["invalid_expected_artifact_total"] == 1
    assert payload["stats"]["missing_expected_artifact_total"] >= 1
