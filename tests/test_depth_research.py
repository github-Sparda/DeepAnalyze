from __future__ import annotations

import json
from pathlib import Path

from src.core.orchestration.depth_research import (
    build_depth_delta,
    build_research_digest,
    render_research_digest_markdown,
    select_depth_focus,
)
from src.core.orchestration import graph as orchestration_graph
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


def test_build_research_digest_prefers_executed_titles_over_drifted_plan_titles(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "plan" / "analysis_plan.json",
        {
            "hypotheses": [
                {"id": "H2", "title": "相关结构验证"},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_results.json",
        {
            "hypotheses": [
                {"hypothesis": "H2: 预测性能验证", "steps": {"model_eval": {"status": "ok"}}, "missing": []},
            ]
        },
    )
    _write_json(
        tmp_path / "result" / "hypothesis_gate_report.json",
        {"hypotheses": [{"hypothesis_id": "H2", "gate_status": "pass"}]},
    )
    _write_json(
        tmp_path / "result" / "hypothesis_evidence_pack.json",
        {"hypotheses": [{"hypothesis_id": "H2", "quant_metrics": [{"name": "auc", "value": 0.91}]}]},
    )
    _write_json(
        tmp_path / "result" / "path_execution_status.json",
        {"hypotheses": [{"hypothesis_id": "H2", "overall": "complete", "missing_artifacts": []}]},
    )
    _write_json(
        tmp_path / "result" / "hypothesis_multipath.json",
        {"hypotheses": [{"hypothesis_id": "H2", "consistency": "consistent"}]},
    )
    digest = build_research_digest(tmp_path, {"depth": 1, "closure_status": {}})
    assert digest["hypotheses"][0]["title"] == "预测性能验证"


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


def test_select_depth_focus_stops_when_all_closed_and_no_extension_space() -> None:
    focus = select_depth_focus(
        {
            "unresolved_candidates": [],
            "stable_findings": [
                {
                    "hypothesis_id": "H1",
                    "title": "差异检验",
                    "gate_status": "pass",
                    "path_overall": "complete",
                    "consistency": "consistent",
                    "reason_code": "",
                    "quant_metric_count": 6,
                    "missing_artifact_count": 0,
                    "evidence_sources": ["result/stats_results.json", "result/top_features.json"],
                },
                {
                    "hypothesis_id": "H2",
                    "title": "预测性能",
                    "gate_status": "pass",
                    "path_overall": "complete",
                    "consistency": "consistent",
                    "reason_code": "",
                    "quant_metric_count": 8,
                    "missing_artifact_count": 0,
                    "evidence_sources": ["result/model_eval.json", "result/cv_results.json"],
                },
            ],
        }
    )
    assert focus["mode"] == "stop"
    assert focus["selected"] == []


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
    _write_json(
        tmp_path / "meta" / "iteration_lineage.json",
        {
            "iterations": [
                {
                    "depth": 1,
                    "forced_round": True,
                    "followups": ["FORCED_ROUND_2: 基于首轮证据执行第 2 轮复核。"],
                }
            ]
        },
    )
    text = ReportAssembler(language="zh")._render_depth_progression(tmp_path)
    assert "多轮递进摘要" in text
    assert "depth 1 -> depth 2" in text
    assert "H2" in text
    assert "强制递进" in text


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


def test_recursion_controller_force_rounds_overrides_stop_before_required_round() -> None:
    decision = DepthRecursionController(max_depth=2, force_rounds=2, retry_limit=1).evaluate(
        depth=1,
        followups=[],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="",
        execution_retry_count=0,
        unresolved_pending=False,
    )
    assert decision["should_recurse"] is True
    assert decision["forced_round"] is True


def test_recursion_controller_force_rounds_is_clamped_by_max_depth() -> None:
    controller = DepthRecursionController(max_depth=2, force_rounds=5, retry_limit=1)
    assert controller.force_rounds == 2


def test_recursive_followup_binding_rewrites_speculative_paths_to_runtime_contract(tmp_path: Path) -> None:
    prior_plan = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "差异特征性验证",
                "hypothesis_type": "difference",
                "expected_artifacts": ["differential_features_table.csv", "volcano_plot.png"],
                "validation_paths": [{"path_id": "path_a"}, {"path_id": "path_b"}],
            }
        ]
    }
    raw_plan = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "核心标志物的统计稳健性假设",
                "hypothesis": "希望通过更严格方法验证差异稳定性",
                "expected_artifacts": ["Robustness_Summary.csv", "Volcano_Plot_Refined.png"],
                "validation_paths": [
                    {"path_id": "h1_a", "method_family": "parametric_statistical_inference", "expected_artifacts": ["Robustness_Summary.csv"]},
                    {"path_id": "h1_b", "method_family": "non-parametric_resampling", "expected_artifacts": ["Volcano_Plot_Refined.png"]},
                ],
            }
        ]
    }
    normalized = orchestration_graph._normalize_plan_json(
        raw_plan,
        "",
        session_dir=tmp_path,
        prior_plan_json=prior_plan,
        depth=2,
    )
    row = normalized["hypotheses"][0]
    assert row["hypothesis_type"] == "difference"
    assert row["title"] == "差异特征性验证"
    assert "differential_features_table.csv" in row["expected_artifacts"]
    assert "Robustness_Summary.csv" not in row["expected_artifacts"]
    binding = normalized["followup_contract_binding"]["bindings"][0]
    assert binding["binding_source"] == "prior_plan_hypothesis_type"
    assert "Robustness_Summary.csv" in binding["rejected_expected_artifacts"]


def test_align_plan_json_to_runtime_hypotheses_rewrites_first_round_identity() -> None:
    plan_json = {
        "hypotheses": [
            {"id": "H1", "title": "差异显著性假设", "hypothesis_type": "difference"},
            {"id": "H2", "title": "空间聚类假设", "hypothesis_type": "embedding"},
            {"id": "H3", "title": "诊断效能假设", "hypothesis_type": "predictive"},
        ]
    }
    hypothesis_payload = {
        "hypotheses": [
            {"hypothesis": "H1: 分组差异检验", "hypothesis_type": "difference", "expected_artifacts": ["stats_results.json"]},
            {"hypothesis": "H2: 预测性能验证", "hypothesis_type": "predictive", "expected_artifacts": ["model_eval.json"]},
            {"hypothesis": "H3: 相关结构验证", "hypothesis_type": "correlation", "expected_artifacts": ["correlation.json"]},
        ]
    }
    aligned, meta = orchestration_graph._align_plan_json_to_runtime_hypotheses(plan_json, hypothesis_payload)
    rows = {row["id"]: row for row in aligned["hypotheses"]}
    assert meta["changed"] is True
    assert rows["H1"]["title"] == "分组差异检验"
    assert rows["H2"]["title"] == "预测性能验证"
    assert rows["H2"]["hypothesis_type"] == "predictive"
    assert rows["H3"]["title"] == "相关结构验证"
    assert rows["H3"]["hypothesis_type"] == "correlation"


def test_recursive_followup_binding_marks_unsupported_profile_as_research_only(tmp_path: Path) -> None:
    raw_plan = {
        "hypotheses": [
            {
                "id": "H9",
                "title": "全新机制发现假设",
                "hypothesis": "提出一个当前工具链不支持的全新机制假设",
                "hypothesis_type": "generic",
                "expected_artifacts": ["novel_mechanism_bundle.zip"],
                "validation_paths": [
                    {"path_id": "path_a", "method_family": "novel_method", "expected_artifacts": ["novel_mechanism_bundle.zip"]},
                    {"path_id": "path_b", "method_family": "another_novel_method", "expected_artifacts": ["novel_mechanism_bundle.zip"]},
                ],
            }
        ]
    }
    normalized = orchestration_graph._normalize_plan_json(
        raw_plan,
        "",
        session_dir=tmp_path,
        prior_plan_json={},
        depth=2,
    )
    assert normalized["hypotheses"] == []
    binding = normalized["followup_contract_binding"]["bindings"][0]
    assert binding["executable"] is False
    assert binding["rewrite_reason"] == "no_runtime_supported_equivalent"


def test_recursive_followup_binding_preserves_prior_identity_for_h2_predictive(tmp_path: Path) -> None:
    prior_plan = {
        "hypotheses": [
            {
                "id": "H2",
                "title": "预测性能验证",
                "hypothesis": "利用关键特征区分 Normal 与 EP",
                "hypothesis_type": "predictive",
            }
        ]
    }
    raw_plan = {
        "hypotheses": [
            {
                "id": "H2",
                "title": "相关结构验证",
                "hypothesis": "尝试基于相关网络继续分析",
                "hypothesis_type": "correlation",
                "expected_artifacts": ["network.png"],
                "validation_paths": [
                    {"path_id": "path_a", "method_family": "pearson_network", "expected_artifacts": ["network.png"]},
                    {"path_id": "path_b", "method_family": "embedding_projection", "expected_artifacts": ["tsne_umap_plot.png"]},
                ],
            }
        ]
    }
    normalized = orchestration_graph._normalize_plan_json(
        raw_plan,
        "",
        session_dir=tmp_path,
        prior_plan_json=prior_plan,
        depth=2,
    )
    row = normalized["hypotheses"][0]
    assert row["hypothesis_type"] == "predictive"
    assert row["title"] == "预测性能验证"
    binding = normalized["followup_contract_binding"]["bindings"][0]
    assert binding["binding_source"] == "prior_plan_hypothesis_type"
    assert binding["planned_followup"]["title"] == "相关结构验证"
