from __future__ import annotations

from types import SimpleNamespace

from src.core.orchestration import graph as orchestration_graph


def test_run_path_c_adjudication_generates_verdict(monkeypatch, tmp_path) -> None:
    dataset = tmp_path / "data.csv"
    dataset.write_text("a,b\n1,2\n", encoding="utf-8")

    monkeypatch.setattr(orchestration_graph, "_find_first_dataset", lambda _: dataset)
    monkeypatch.setattr(orchestration_graph, "run_step", lambda *args, **kwargs: {"status": "ok"})
    monkeypatch.setattr(orchestration_graph, "_check_quality_gates", lambda *args, **kwargs: [])

    variant = SimpleNamespace(
        variant_id="u_test_variant",
        steps=[SimpleNamespace(name="model_eval", method="baseline")],
        required_artifacts=[],
        quality_gates=[],
        fallback_variant=None,
    )
    scored = SimpleNamespace(pipeline_id="differential_testing", variant=variant)
    monkeypatch.setattr(orchestration_graph, "select_pipeline_variants", lambda *_args, **_kwargs: [scored])

    payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "status": "inconclusive",
                "consistency": "conflict",
                "paths": [
                    {"path_id": "path_a", "method_family": "statistical", "status": "validated"},
                    {"path_id": "path_b", "method_family": "correlation", "status": "failed"},
                ],
            }
        ],
        "stats": {"conflict_rate": 1.0},
    }
    updated, adjudication = orchestration_graph._run_path_c_adjudication(
        tmp_path,
        {"numeric_columns": ["a"], "column_names": ["a", "group"]},
        payload,
        conflict_threshold=0.0,
    )
    assert adjudication["enabled"] is True
    assert adjudication["hypotheses"][0]["verdict"] == "validated"
    assert updated["hypotheses"][0]["status"] == "validated"
    assert any(p.get("path_id") == "path_c" for p in updated["hypotheses"][0]["paths"])
