from __future__ import annotations

import json
from pathlib import Path

from src.core.reporting.assembler import ReportAssembler


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_path_adjudication_section_shows_not_triggered_reason(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "result" / "path_adjudication.json",
        {
            "enabled": False,
            "reason": "conflict_rate_below_threshold",
            "conflict_rate": 0.0,
            "threshold": 0.3,
            "hypotheses": [],
        },
    )
    assembler = ReportAssembler(language="zh")
    text = assembler._render_path_adjudication(tmp_path)
    assert "未触发原因" in text
    assert "conflict_rate_below_threshold" in text


def test_predictive_completeness_accepts_ml_repro_bundle_as_model_evidence() -> None:
    assembler = ReportAssembler(language="zh")
    missing = assembler._predictive_completeness_missing(
        gate_entry={
            "gate_rule_type": "predictive_performance",
            "ml_repro_bundle": {"bundle_dir": "result/ml_repro/h2", "complete": True},
        },
        evidence_entry={
            "quant_metrics": [
                {"name": "centroid_accuracy", "value": 0.71},
                {"name": "cv_mean_accuracy", "value": 0.70},
                {"name": "cv_std_accuracy", "value": 0.01},
            ]
        },
        step_map={"feature_selection": {"status": "ok"}},
        contrast_entry={},
    )
    assert "predictive_model_name_missing" not in missing
