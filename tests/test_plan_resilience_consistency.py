from __future__ import annotations

import json
from pathlib import Path

from src.core.orchestration import graph as orchestration_graph


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_synthesize_plan_from_hypothesis_results(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "result" / "hypothesis_results.json",
        {
            "hypotheses": [
                {
                    "hypothesis": "H1: 差异检验",
                    "expected_artifacts": ["stats_results.json"],
                    "steps": {"stats_tests": {"status": "ok"}},
                }
            ]
        },
    )
    plan = orchestration_graph._synthesize_plan_from_hypothesis_results(tmp_path, {})
    assert plan.get("hypotheses")
    assert plan["hypotheses"][0]["id"] == "H1"
    assert "validation_paths" in plan["hypotheses"][0]


def test_synthesize_plan_fallback_keeps_deterministic_hypothesis_order(tmp_path: Path) -> None:
    data_quality = {
        "datasets": [
            {
                "dtypes": {
                    "Group": "object",
                    "peak1": "float64",
                    "peak2": "float64",
                }
            }
        ]
    }
    plan = orchestration_graph._synthesize_plan_from_hypothesis_results(tmp_path, data_quality)
    titles = [item.get("title") for item in plan.get("hypotheses", [])]
    types = [item.get("hypothesis_type") for item in plan.get("hypotheses", [])]
    assert titles[:3] == ["分组差异检验", "预测性能验证", "相关结构验证"]
    assert types[:3] == ["difference", "predictive", "correlation"]


def test_consistency_infers_base_ids_without_plan(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "result" / "hypothesis_results.json",
        {"hypotheses": [{"hypothesis": "H1: test"}, {"hypothesis": "H2: test"}]},
    )
    _write_json(
        tmp_path / "result" / "hypothesis_evidence_pack.json",
        {"hypotheses": [{"hypothesis_id": "H1"}, {"hypothesis_id": "H2"}]},
    )
    _write_json(
        tmp_path / "result" / "hypothesis_gate_report.json",
        {"hypotheses": [{"hypothesis_id": "H1"}, {"hypothesis_id": "H2"}]},
    )
    _write_json(
        tmp_path / "result" / "hypothesis_multipath.json",
        {"hypotheses": [{"hypothesis_id": "H1"}, {"hypothesis_id": "H2"}]},
    )
    payload = orchestration_graph._build_hypothesis_set_consistency(
        tmp_path, {}, require_report_ids=False
    )
    assert payload["satisfied"] is True
    assert str(payload["checks"]["base_source"]).startswith("inferred:")


def test_consistency_detects_semantic_mismatch_between_plan_and_results(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "plan" / "analysis_plan.json",
        {
            "hypotheses": [
                {"id": "H1", "title": "分组差异检验", "hypothesis_type": "difference"},
                {"id": "H2", "title": "相关结构验证", "hypothesis_type": "correlation"},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_results.json",
        {
            "hypotheses": [
                {"hypothesis": "H1: 分组差异检验", "hypothesis_type": "difference"},
                {"hypothesis": "H2: 预测性能验证", "hypothesis_type": "predictive"},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_evidence_pack.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "hypothesis_type": "difference"},
                {"hypothesis_id": "H2", "hypothesis_type": "predictive"},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_gate_report.json",
        {"hypotheses": [{"hypothesis_id": "H1"}, {"hypothesis_id": "H2"}]},
    )
    _write_json(
        tmp_path / "result" / "hypothesis_multipath.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "title": "分组差异检验"},
                {"hypothesis_id": "H2", "title": "预测性能验证"},
            ]
        },
    )
    payload = orchestration_graph._build_hypothesis_set_consistency(tmp_path, {}, require_report_ids=False)
    assert payload["satisfied"] is False
    assert "results_signatures" in payload["semantic_mismatches"]
    assert "H2" in payload["semantic_mismatches"]["results_signatures"]


def test_artifact_validation_uses_latest_status(tmp_path: Path) -> None:
    manifest = [
        {"role_id": "DataIngest", "status": "success"},
        {"role_id": "DataQuality", "status": "success"},
        {"role_id": "Hypothesis", "status": "error"},
        {"role_id": "Hypothesis", "status": "success"},
        {"role_id": "CodeGen", "status": "success"},
        {"role_id": "Insights", "status": "success"},
        {"role_id": "EvidenceCurator", "status": "success"},
        {"role_id": "Visualization", "status": "success"},
        {"role_id": "RunGuard", "status": "success"},
    ]
    _write_json(tmp_path / "meta" / "role_manifest.json", manifest)
    report = orchestration_graph._artifact_validation_report(tmp_path)
    assert report["missing_roles"] == []
    assert report["errors"] == []


def test_sync_hypothesis_alignment_artifacts_rewrites_filtered_matrix_and_binding(tmp_path: Path) -> None:
    payload = {
        "hypotheses": [
            {"hypothesis": "H1: 分组差异检验", "hypothesis_type": "difference", "expected_artifacts": [], "missing": [], "steps": {}},
            {"hypothesis": "H2: 预测性能验证", "hypothesis_type": "predictive", "expected_artifacts": [], "missing": [], "steps": {}},
            {"hypothesis": "H3: 相关结构验证", "hypothesis_type": "correlation", "expected_artifacts": [], "missing": [], "steps": {}},
        ]
    }
    orchestration_graph._sync_hypothesis_alignment_artifacts(tmp_path, payload)
    matrix = json.loads((tmp_path / "result" / "hypothesis_matrix.json").read_text(encoding="utf-8"))
    binding = json.loads((tmp_path / "result" / "visual_binding.json").read_text(encoding="utf-8"))
    matrix_titles = [row.get("hypothesis", "") for row in matrix.get("hypotheses", [])]
    binding_hypotheses = [row.get("hypothesis", "") for row in binding.get("bindings", [])]
    assert all(not str(item).startswith("H4") for item in matrix_titles)
    assert all(not str(item).startswith("H4") for item in binding_hypotheses)


def test_llm_unavailable_error_detection() -> None:
    assert orchestration_graph._is_llm_unavailable_error("429 model_not_found")
    assert orchestration_graph._is_llm_unavailable_error("service unavailable")
    assert not orchestration_graph._is_llm_unavailable_error("value error in local parse")


def test_fallback_followups_from_gate_report(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "result" / "hypothesis_gate_report.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "gate_status": "pass"},
                {"hypothesis_id": "H2", "gate_status": "partial", "reason_code": "metric_missing"},
            ]
        },
    )
    followups = orchestration_graph._fallback_followup_hypotheses(tmp_path)
    assert followups
    assert followups[0].startswith("H2")


def test_fallback_report_outline_uses_plan_hypotheses() -> None:
    outline = orchestration_graph._fallback_report_outline(
        {
            "plan_json": {
                "hypotheses": [
                    {"id": "H1", "title": "分组差异检验"},
                    {"id": "H2", "title": "预测性能验证"},
                ]
            }
        }
    )
    assert "### H1 分组差异检验" in outline
    assert "## 四、跨假设综合讨论" in outline


def test_strong_fallback_plan_gate_rejects_weak_plan() -> None:
    ok, reason = orchestration_graph._strong_fallback_plan_ok(
        {"hypotheses": [{"id": "H1", "title": "A", "hypothesis_type": "difference", "steps": ["x"], "validation_paths": [{"path_id": "A"}]}]}
    )
    assert ok is False
    assert reason in {"hypothesis_count_lt_3", "H1_validation_paths_lt_2"}


def test_strong_fallback_report_gate_requires_core_checks() -> None:
    ok, reasons = orchestration_graph._strong_fallback_report_ok(
        {"complete": False},
        {"satisfied": True},
        {"valid": True},
    )
    assert ok is False
    assert "completion_validation_failed" in reasons


def test_build_path_execution_status_counts_paths() -> None:
    payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "status": "validated",
                "paths": [
                    {"path_id": "a", "status": "ok"},
                    {"path_id": "b", "status": "ok"},
                ],
            },
            {
                "hypothesis_id": "H2",
                "status": "failed",
                "paths": [
                    {"path_id": "a", "status": "failed", "missing_artifacts": ["x.png"]},
                    {"path_id": "b", "status": "partial", "missing_artifacts": ["y.csv"]},
                ],
            },
        ]
    }
    status = orchestration_graph._build_path_execution_status(payload)
    rows = {row["hypothesis_id"]: row for row in status.get("hypotheses", [])}
    assert rows["H1"]["overall"] == "complete"
    assert rows["H1"]["path_success"] == 2
    assert rows["H2"]["overall"] == "incomplete"
    assert set(rows["H2"]["missing_artifacts"]) == {"x.png", "y.csv"}
