from __future__ import annotations

import json

from src.core.orchestration import graph as orchestration_graph


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_ml_repro_bundle_contract_outputs_required_files(tmp_path) -> None:
    result_dir = tmp_path / "result"
    _write_json(
        result_dir / "model_results.json",
        {
            "model": "centroid",
            "label_col": "group",
            "numeric_features": ["peak1", "peak2"],
            "random_seed": 0,
            "train_size": 40,
            "test_size": 10,
            "n_samples": 50,
            "train_accuracy": 0.8,
            "test_accuracy": 0.7,
        },
    )
    _write_json(
        result_dir / "model_eval.json",
        {"metrics": {"majority_accuracy": 0.6, "centroid_accuracy": 0.7}},
    )
    _write_json(
        result_dir / "cv_results.json",
        {"status": "ok", "mean_accuracy": 0.71, "std_accuracy": 0.02},
    )
    gate_report = {
        "hypotheses": [
            {"hypothesis_id": "H2", "gate_rule_type": "predictive_performance", "gate_status": "partial"}
        ]
    }
    payload = orchestration_graph._build_ml_repro_bundle(tmp_path, gate_report)
    assert payload["enabled"] is True
    item = payload["hypotheses"][0]
    assert item["hypothesis_id"] == "H2"
    assert item["complete"] is True
    bundle_dir = tmp_path / item["bundle_dir"]
    assert (bundle_dir / "model_spec.json").exists()
    assert (bundle_dir / "data_split.json").exists()
    assert (bundle_dir / "metrics.json").exists()
    assert (bundle_dir / "training_log.txt").exists()
