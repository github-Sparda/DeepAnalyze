from __future__ import annotations

import json

from src.core.orchestration import graph as orchestration_graph


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _seed_required_files(session_dir) -> None:
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "analysis_results.md").write_text("ok", encoding="utf-8")
    _write_json(result_dir / "expected_artifact_validation.json", {"valid": True})
    _write_json(result_dir / "hypothesis_gate_report.json", {"hypotheses": []})
    _write_json(result_dir / "hypothesis_evidence_pack_validation.json", {"valid": True})


def test_completion_validator_passes_when_all_checks_satisfied(tmp_path) -> None:
    session_dir = tmp_path / "session"
    _seed_required_files(session_dir)
    payload = orchestration_graph._build_completion_validation(
        session_dir,
        gate_payload={"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass"}]},
        pack_validation={"valid": True},
        artifact_validation={"missing_roles": [], "errors": []},
        pipeline_gate_failures=[],
    )
    assert payload["complete"] is True
    assert payload["blocking_reasons"] == []


def test_completion_validator_blocks_on_unresolved_gate(tmp_path) -> None:
    session_dir = tmp_path / "session"
    _seed_required_files(session_dir)
    payload = orchestration_graph._build_completion_validation(
        session_dir,
        gate_payload={"hypotheses": [{"hypothesis_id": "H2", "gate_status": "partial"}]},
        pack_validation={"valid": True},
        artifact_validation={"missing_roles": [], "errors": []},
        pipeline_gate_failures=[],
    )
    assert payload["complete"] is False
    assert "unresolved_hypothesis_gate" in payload["blocking_reasons"]
    assert payload["checks"]["unresolved_gate_hypotheses"] == ["H2"]


def test_completion_validator_requires_report_when_expected(tmp_path) -> None:
    session_dir = tmp_path / "session"
    _seed_required_files(session_dir)
    payload = orchestration_graph._build_completion_validation(
        session_dir,
        gate_payload={"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass"}]},
        pack_validation={"valid": True},
        artifact_validation={"missing_roles": [], "errors": []},
        pipeline_gate_failures=[],
        expect_report=True,
    )
    assert payload["complete"] is False
    assert "report_missing" in payload["blocking_reasons"]
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "report" / "report_v1.html").write_text("<html></html>", encoding="utf-8")
    payload2 = orchestration_graph._build_completion_validation(
        session_dir,
        gate_payload={"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass"}]},
        pack_validation={"valid": True},
        artifact_validation={"missing_roles": [], "errors": []},
        pipeline_gate_failures=[],
        expect_report=True,
    )
    assert payload2["complete"] is True
