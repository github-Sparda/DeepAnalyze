from __future__ import annotations

import json
from pathlib import Path

from src.core.analytics.resources import (
    build_hypothesis_evidence_pack,
    build_hypothesis_gate_report,
    load_feature_dictionary,
    load_method_dictionary,
    load_metric_dictionary,
)
from src.core.orchestration import graph as orchestration_graph
from src.core.orchestration.hypothesis_engine import _build_hypothesis_contrast, _build_hypothesis_evidence
from src.core.reporting.assembler import ReportAssembler


class AlwaysFailLLM:
    def chat(self, messages, max_tokens=1024):  # noqa: D401
        raise TimeoutError("llm timeout")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_data_ingest_fallback_without_role_error(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "sample.csv").write_text("group,x\nA,1\nB,2\n", encoding="utf-8")
    state = {
        "session_id": "t-fallback",
        "session_dir": str(session_dir),
        "data_sessions_active_dir": str(session_dir),
        "depth": 1,
        "max_depth": 1,
        "config": {"report_format": "html", "report_language": "zh"},
    }
    graph = orchestration_graph.build_graph(AlwaysFailLLM(), state["config"])
    graph.invoke(state)

    fallback_path = session_dir / "meta" / "plan_validation" / "file_summary_fallback.json"
    assert fallback_path.exists()
    manifest = json.loads((session_dir / "meta" / "role_manifest.json").read_text(encoding="utf-8"))
    latest = None
    for row in manifest:
        if isinstance(row, dict) and row.get("role_id") == "DataIngest":
            latest = row
    assert isinstance(latest, dict)
    assert latest.get("status") == "success"
    report_dir = session_dir / "report"
    assert report_dir.exists()
    assert any(report_dir.glob("report_v*.*"))


def test_h1_effect_metrics_promote_gate_effect_check(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    stats_rows = [
        {
            "feature": "f1",
            "p_value": 0.01,
            "fold_change": 1.8,
            "log2_fold_change": 0.85,
            "effect_size": 0.42,
        },
        {
            "feature": "f2",
            "p_value": 0.02,
            "fold_change": 1.3,
            "log2_fold_change": 0.38,
            "effect_size": 0.31,
        },
    ]
    _write_json(result_dir / "stats_results.json", stats_rows)
    _write_json(result_dir / "multiple_testing.json", [{"feature": "f1", "q_value": 0.03}, {"feature": "f2", "q_value": 0.04}])
    _write_json(result_dir / "top_features.json", [{"feature": "f1"}, {"feature": "f2"}])

    hypothesis_payload = {
        "hypotheses": [
            {
                "hypothesis": "H1: 组间差异",
                "missing": [],
                "expected_artifacts": ["result/stats_results.json"],
            }
        ]
    }
    evidence = _build_hypothesis_evidence(session_dir, hypothesis_payload)
    contrast = _build_hypothesis_contrast(evidence, session_dir)
    multipath = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "status": "validated",
                "paths": [
                    {"path_id": "path_a", "method_family": "parametric_test", "status": "validated", "missing_artifacts": []},
                    {"path_id": "path_b", "method_family": "nonparametric_or_fdr", "status": "validated", "missing_artifacts": []},
                ],
            }
        ]
    }
    pack = build_hypothesis_evidence_pack(
        evidence,
        contrast,
        multipath,
        load_metric_dictionary(session_dir),
        load_feature_dictionary(session_dir),
        load_method_dictionary(session_dir),
    )
    gate = build_hypothesis_gate_report(pack)

    row = next(item for item in gate["hypotheses"] if item.get("hypothesis_id") == "H1")
    assert row["checks"].get("has_effect_metric") is True


def test_gate_pass_clears_reason_code() -> None:
    pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H2",
                "claim": "预测性能",
                "status": "validated",
                "quant_metrics": [
                    {"name": "centroid_accuracy", "value": 0.7, "category": "performance"},
                    {"name": "cv_mean_accuracy", "value": 0.72, "category": "performance"},
                ],
                "effect_metrics": [{"name": "centroid_accuracy", "value": 0.7}],
                "method_trace": [],
                "evidence_sources": [],
                "consistency": {"flag": "consistent"},
                "reason_code": "assumption_violation",
                "recovery_action": "switch_nonparametric_or_transform_data",
            }
        ]
    }
    gate = build_hypothesis_gate_report(pack)
    row = gate["hypotheses"][0]
    assert row["gate_status"] == "pass"
    assert row["reason_code"] == ""
    assert row["recovery_action"] == ""


def test_quality_score_uses_conservative_closure_source(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    result_dir = session_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    _write_json(result_dir / "hypothesis_evidence_pack.json", {"hypotheses": [{"hypothesis_id": "H1", "quant_metrics": [{"name": "m1"}]}]})
    _write_json(result_dir / "hypothesis_validation_contract.json", {"hypotheses": [{"hypothesis_id": "H1", "executed_status": "validated"}]})
    _write_json(result_dir / "hypothesis_gate_report.json", {"hypotheses": [{"hypothesis_id": "H1", "gate_status": "partial"}]})
    _write_json(result_dir / "hypothesis_contrast.json", {"hypotheses": []})
    (result_dir / "analysis_results.md").write_text("m1=1", encoding="utf-8")

    score = orchestration_graph._build_analysis_quality_score(session_dir)
    assert score["hypothesis_closure_rate"] == 0.0
    assert score["closure_source"] == "min(contract,gate)"


def test_global_process_summary_fallback_uses_execution_chain() -> None:
    assembler = ReportAssembler(language="zh")
    process_md = """
1. 自动化执行流程（基于实际执行步骤）
2. H1：stats_tests -> multiple_testing -> stats_summary
3. H2：feature_selection -> model_train -> model_eval
"""
    rendered = "\n".join(assembler._render_global_process_summary(process_md))
    assert "未提取到全局流程要点" not in rendered
    assert "stats_tests -> multiple_testing -> stats_summary" in rendered
