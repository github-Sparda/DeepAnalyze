from __future__ import annotations

import json

from src.core.orchestration import graph as orchestration_graph


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_closure_rate_excludes_failed_and_partial(tmp_path) -> None:
    session_dir = tmp_path / "session"
    result_dir = session_dir / "result"
    _write_json(
        result_dir / "hypothesis_evidence_pack.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "quant_metrics": [{"name": "m1"}]},
                {"hypothesis_id": "H2", "quant_metrics": [{"name": "m1"}]},
                {"hypothesis_id": "H3", "quant_metrics": [{"name": "m1"}]},
            ]
        },
    )
    _write_json(
        result_dir / "hypothesis_validation_contract.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "executed_status": "validated"},
                {"hypothesis_id": "H2", "executed_status": "partial"},
                {"hypothesis_id": "H3", "executed_status": "failed"},
            ]
        },
    )
    _write_json(result_dir / "hypothesis_contrast.json", {"hypotheses": []})
    (result_dir / "analysis_results.md").write_text("m1=1", encoding="utf-8")

    score = orchestration_graph._build_analysis_quality_score(session_dir)
    assert score["hypothesis_closure_rate"] == 0.3333
