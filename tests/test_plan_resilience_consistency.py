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
