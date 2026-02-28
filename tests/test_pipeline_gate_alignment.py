from __future__ import annotations

import json

from src.core.analytics.toolkit.pipelines import pipeline_registry
from src.core.orchestration import graph as orchestration_graph


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _seed_completion_files(session_dir) -> None:
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "analysis_results.md").write_text("ok", encoding="utf-8")
    _write_json(result_dir / "expected_artifact_validation.json", {"valid": True})
    _write_json(result_dir / "hypothesis_gate_report.json", {"hypotheses": []})
    _write_json(result_dir / "hypothesis_evidence_pack_validation.json", {"valid": True})


def _variant(variant_id: str):
    spec = pipeline_registry()["key_feature_screening"]
    return next(item for item in spec.variants if item.variant_id == variant_id)


def test_pipeline_contract_waives_when_equivalent_plot_exists(tmp_path) -> None:
    session_dir = tmp_path / "session"
    _write_json(session_dir / "result" / "stats_results.json", {"rows": []})
    (session_dir / "plots").mkdir(parents=True, exist_ok=True)
    (session_dir / "plots" / "volcano_plot.png").write_bytes(b"png")

    contract = orchestration_graph._evaluate_pipeline_variant_contract(
        session_dir,
        _variant("anova_manhattan"),
    )

    assert contract["status"] == "waived_by_equivalent_execution"
    assert contract["missing"] == []
    assert any(row.get("waiver_basis") == "artifact_alias" for row in contract["waivers"])


def test_pipeline_contract_keeps_real_missing_artifacts(tmp_path) -> None:
    session_dir = tmp_path / "session"
    _write_json(session_dir / "result" / "stats_results.json", {"rows": []})

    contract = orchestration_graph._evaluate_pipeline_variant_contract(
        session_dir,
        _variant("anova_manhattan"),
    )

    assert contract["status"] == "fail"
    assert "plots:manhattan_plot.png" in contract["missing"]


def test_pipeline_resolution_clears_false_failure_and_completion_can_pass(tmp_path) -> None:
    session_dir = tmp_path / "session"
    _seed_completion_files(session_dir)
    _write_json(session_dir / "result" / "stats_results.json", {"rows": []})
    (session_dir / "plots").mkdir(parents=True, exist_ok=True)
    (session_dir / "plots" / "volcano_plot.png").write_bytes(b"png")

    resolution = orchestration_graph._resolve_pipeline_gate_failures(
        session_dir,
        [
            {
                "pipeline_id": "key_feature_screening",
                "variant_id": "anova_manhattan",
                "missing": ["plots:manhattan_plot.png"],
                "fallback_variant": None,
            }
        ],
    )

    assert resolution["remaining_failures"] == []
    assert len(resolution["waived_records"]) == 1

    payload = orchestration_graph._build_completion_validation(
        session_dir,
        gate_payload={"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass"}]},
        pack_validation={"valid": True},
        artifact_validation={"missing_roles": [], "errors": []},
        pipeline_gate_failures=resolution["remaining_failures"],
        pipeline_gate_waivers=resolution["waived_records"],
    )

    assert payload["complete"] is True
    assert payload["checks"]["pipeline_gate_waived_count"] == 1
