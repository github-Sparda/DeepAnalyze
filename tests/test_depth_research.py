from __future__ import annotations

import json
from pathlib import Path

from src.core.orchestration.depth_research import (
    build_depth_delta,
    build_research_digest,
    render_research_digest_markdown,
    select_depth_focus,
)
from src.core.orchestration.recursion import DepthRecursionController
from src.core.reporting.assembler import ReportAssembler


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_research_digest_collects_unresolved_and_stable(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "plan" / "analysis_plan.json",
        {
            "hypotheses": [
                {"id": "H1", "title": "差异检验"},
                {"id": "H2", "title": "预测性能"},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_gate_report.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "gate_status": "pass"},
                {"hypothesis_id": "H2", "gate_status": "partial", "reason_code": "metric_missing"},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_evidence_pack.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "quant_metrics": [{"name": "a", "value": 1.0}]},
                {"hypothesis_id": "H2", "quant_metrics": [{"name": "b", "value": 2.0}, {"name": "c", "value": 3.0}]},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "path_execution_status.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "overall": "complete", "missing_artifacts": []},
                {"hypothesis_id": "H2", "overall": "incomplete", "missing_artifacts": ["x.json"]},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_multipath.json",
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "consistency": "consistent"},
                {"hypothesis_id": "H2", "consistency": "conflict"},
            ]
        },
    )
    digest = build_research_digest(tmp_path, {"depth": 1, "closure_status": {"generate_report": {"blocking": True}}})
    assert digest["summary"]["stable_count"] == 1
    assert digest["summary"]["unresolved_count"] == 1
    assert digest["blocking_phases"] == ["generate_report"]


def test_select_depth_focus_prefers_unresolved_candidates() -> None:
    focus = select_depth_focus(
        {
            "unresolved_candidates": [
                {
                    "hypothesis_id": "H2",
                    "title": "预测性能",
                    "gate_status": "partial",
                    "path_overall": "incomplete",
                    "consistency": "conflict",
                    "quant_metric_count": 3,
                    "missing_artifact_count": 1,
                }
            ],
            "stable_findings": [
                {"hypothesis_id": "H1", "title": "差异检验", "quant_metric_count": 2}
            ],
        }
    )
    assert focus["mode"] == "closure_followup"
    assert focus["selected"][0]["hypothesis_id"] == "H2"


def test_build_depth_delta_marks_no_material_gain_when_counts_do_not_improve() -> None:
    delta = build_depth_delta(
        {
            "depth": 1,
            "summary": {"stable_count": 1, "unresolved_count": 2, "blocking_phase_count": 1},
            "hypotheses": [{"hypothesis_id": "H2", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 2}],
        },
        {
            "depth": 2,
            "summary": {"stable_count": 1, "unresolved_count": 2, "blocking_phase_count": 1},
            "hypotheses": [{"hypothesis_id": "H2", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 2}],
        },
        {"mode": "closure_followup", "selected": [{"hypothesis_id": "H2"}]},
    )
    assert delta["material_gain"] is False
    assert "未带来实质深度增益" in delta["summary"]


def test_build_depth_delta_does_not_treat_scope_narrowing_as_gain() -> None:
    delta = build_depth_delta(
        {
            "depth": 1,
            "summary": {"stable_count": 0, "unresolved_count": 4, "blocking_phase_count": 1},
            "hypotheses": [
                {"hypothesis_id": "H1", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 4},
                {"hypothesis_id": "H2", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 4},
                {"hypothesis_id": "H3", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 4},
            ],
        },
        {
            "depth": 2,
            "summary": {"stable_count": 0, "unresolved_count": 3, "blocking_phase_count": 2},
            "hypotheses": [
                {"hypothesis_id": "H1", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 4},
                {"hypothesis_id": "H2", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 4},
                {"hypothesis_id": "H3", "gate_status": "partial", "path_overall": "incomplete", "missing_artifact_count": 4},
            ],
        },
        {"mode": "closure_followup", "selected": [{"hypothesis_id": "H1"}, {"hypothesis_id": "H2"}, {"hypothesis_id": "H3"}]},
    )
    assert delta["material_gain"] is False


def test_render_research_digest_markdown_is_short_and_structured() -> None:
    md = render_research_digest_markdown(
        {
            "summary": {"total_hypotheses": 2, "stable_count": 1, "unresolved_count": 1, "blocking_phase_count": 0},
            "unresolved_candidates": [{"hypothesis_id": "H2", "title": "预测性能", "gate_status": "partial", "path_overall": "incomplete", "consistency": "conflict", "reason_code": "metric_missing", "missing_artifact_count": 1}],
            "stable_findings": [{"hypothesis_id": "H1", "title": "差异检验", "gate_status": "pass", "path_overall": "complete", "quant_metric_count": 2}],
            "blocking_phases": [],
        }
    )
    assert "Research Digest" in md
    assert "H2" in md
    assert len(md) < 1200


def test_report_renders_depth_progression(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "meta" / "depth_delta.json",
        {
            "summary": "第二轮相对首轮带来了实质增益。",
            "previous_depth": 1,
            "current_depth": 2,
            "selected_mode": "closure_followup",
            "selected_targets": ["H2"],
            "stable_count_delta": 1,
            "unresolved_count_delta": -1,
            "blocking_phase_count_delta": -1,
            "material_gain": True,
        },
    )
    text = ReportAssembler(language="zh")._render_depth_progression(tmp_path)
    assert "多轮递进摘要" in text
    assert "depth 1 -> depth 2" in text
    assert "H2" in text


def test_recursion_controller_stops_when_no_followup_value() -> None:
    decision = DepthRecursionController(max_depth=2, retry_limit=1).evaluate(
        depth=1,
        followups=[],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="",
        execution_retry_count=0,
        unresolved_pending=False,
    )
    assert decision["should_recurse"] is False
