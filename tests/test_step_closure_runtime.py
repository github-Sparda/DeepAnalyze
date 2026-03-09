from __future__ import annotations

import json
from pathlib import Path

from src.core.orchestration.closure import (
    build_phase_blockers,
    closure_completion_summary,
    evaluate_phase_closure,
)
from src.core.orchestration import graph as orchestration_graph
from src.core.reporting.assembler import ReportAssembler


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_plan_phase_closure_rejects_weak_plan(tmp_path: Path) -> None:
    closure = evaluate_phase_closure(
        "plan_analysis",
        tmp_path,
        {
            "plan_json": {
                "hypotheses": [
                    {
                        "id": "H1",
                        "title": "差异",
                        "hypothesis": "存在差异",
                        "validation_paths": [{"path_id": "path_a"}],
                    }
                ]
            },
            "config": {},
        },
    )
    assert closure is not None
    assert closure["status"] == "recoverable_failed"
    assert "hypothesis_count_lt_3" in closure["failed_checks"]


def test_parallel_generation_closure_marks_codegen_skip_as_blocking(tmp_path: Path) -> None:
    closure = evaluate_phase_closure(
        "parallel_generation",
        tmp_path,
        {
            "codegen_skipped": True,
            "config": {},
        },
    )
    assert closure is not None
    assert closure["status"] == "skipped"
    assert closure["blocking"] is True


def test_execution_guard_marks_runtime_failure_as_recoverable(tmp_path: Path) -> None:
    closure = evaluate_phase_closure(
        "execution_guard",
        tmp_path,
        {
            "execution_errors": [{"step": "analysis_step", "output": "Traceback", "statuses": ["error"]}],
            "execution_retry_requested": True,
            "execution_retry_count": 1,
            "config": {"execution_failure_max_retries": 2},
        },
    )
    assert closure is not None
    assert closure["status"] == "recoverable_failed"
    assert closure["recoverable"] is True
    assert closure["recovery_action"] == "invoke_code_repair_then_rerun"


def test_analyze_results_closure_requests_artifact_regeneration(tmp_path: Path) -> None:
    closure = evaluate_phase_closure(
        "analyze_results",
        tmp_path,
        {
            "docs_analysis_results": "",
            "config": {},
        },
    )
    assert closure is not None
    assert closure["status"] == "recoverable_failed"
    assert closure["recovery_action"] == "rebuild_analysis_artifacts_and_rerun"


def test_evidence_curation_closure_marks_invalid_pack_for_repair(tmp_path: Path) -> None:
    _write_json(tmp_path / "result" / "hypothesis_evidence_pack.json", {})
    _write_json(tmp_path / "result" / "hypothesis_gate_report.json", {"hypotheses": []})
    _write_json(tmp_path / "result" / "hypothesis_evidence_pack_validation.json", {"valid": False})
    closure = evaluate_phase_closure(
        "evidence_curation",
        tmp_path,
        {
            "hypothesis_evidence_pack_validation": {"valid": False},
            "config": {},
        },
    )
    assert closure is not None
    assert closure["status"] == "recoverable_failed"
    assert closure["recovery_action"] == "repair_evidence_binding_and_sync_hypotheses"


def test_completion_validation_consumes_phase_closure(tmp_path: Path) -> None:
    result_dir = tmp_path / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "analysis_results.md").write_text("ok", encoding="utf-8")
    _write_json(result_dir / "expected_artifact_validation.json", {"valid": True})
    _write_json(result_dir / "hypothesis_gate_report.json", {"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass"}]})
    _write_json(result_dir / "hypothesis_evidence_pack_validation.json", {"valid": True})
    payload = orchestration_graph._build_completion_validation(
        tmp_path,
        gate_payload={"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass"}]},
        pack_validation={"valid": True},
        artifact_validation={"missing_roles": [], "errors": []},
        pipeline_gate_failures=[],
        closure_status={
            "plan_analysis": {"status": "success", "blocking": False},
            "parallel_generation": {"status": "success", "blocking": False},
            "execution_guard": {"status": "success", "blocking": False},
            "analyze_results": {"status": "recoverable_failed", "blocking": True},
            "evidence_curation": {"status": "success", "blocking": False},
            "generate_report": {"status": "success", "blocking": False},
            "finalize_run": {"status": "success", "blocking": False},
        },
    )
    assert payload["complete"] is False
    assert "step_closure_incomplete" in payload["blocking_reasons"]
    assert payload["checks"]["phase_closure_incomplete_required"] == ["analyze_results"]


def test_closure_completion_summary_detects_missing_required_phase() -> None:
    summary = closure_completion_summary(
        {
            "plan_analysis": {"status": "success", "blocking": False},
            "parallel_generation": {"status": "success", "blocking": False},
        }
    )
    assert summary["complete"] is False
    assert "execution_guard" in summary["required_missing"]


def test_report_renders_phase_closure_summary(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "meta" / "closure_status" / "plan_analysis.json",
        {
            "phase": "plan_analysis",
            "status": "success",
            "failed_checks": [],
            "recovery_action": "",
        },
    )
    _write_json(
        tmp_path / "meta" / "closure_status" / "analyze_results.json",
        {
            "phase": "analyze_results",
            "status": "recoverable_failed",
            "failed_checks": ["missing:hypothesis_multipath.json"],
            "recovery_action": "rebuild_analysis_artifacts_and_rerun",
        },
    )
    assembler = ReportAssembler(language="zh")
    block = assembler._render_phase_closure_summary(tmp_path)
    assert "plan_analysis" in block
    assert "analyze_results" in block
    assert "经恢复后闭环" not in block
    assert "未闭环（可恢复）" in block


def test_build_phase_blockers_extracts_only_blocking_rows() -> None:
    blockers = build_phase_blockers(
        {
            "plan_analysis": {"blocking": False, "failed_checks": []},
            "analyze_results": {"blocking": True, "failed_checks": ["missing:analysis_results.md"]},
        }
    )
    assert blockers == {"analyze_results": ["missing:analysis_results.md"]}


def test_finalize_phase_closure_accepts_session_summary_file(tmp_path: Path) -> None:
    (tmp_path / "meta").mkdir(parents=True, exist_ok=True)
    (tmp_path / "meta" / "run_audit.json").write_text("{}", encoding="utf-8")
    (tmp_path / "meta" / "completion_validation.json").write_text("{}", encoding="utf-8")
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
    closure = evaluate_phase_closure("finalize_run", tmp_path, {"config": {}})
    assert closure is not None
    assert closure["status"] == "success"


def test_generate_report_closure_accepts_explicit_waiver(tmp_path: Path) -> None:
    closure = evaluate_phase_closure(
        "generate_report",
        tmp_path,
        {
            "report_versions": ["report/report_v1.html"],
            "report": "<h1>结构化中间报告</h1>",
            "completion_validation": {"complete": False, "blocking_reasons": ["unresolved_hypothesis_gate"]},
            "report_generation_waiver": {
                "allow": True,
                "reason": "structured_intermediate_report_allowed",
                "derived_from": ["unresolved_hypothesis_gate"],
            },
        },
    )
    assert closure is not None
    assert closure["status"] == "success"
    assert closure["waiver_reason"] == "structured_intermediate_report_allowed"
