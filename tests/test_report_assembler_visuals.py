from __future__ import annotations

from pathlib import Path
import json

from src.core.reporting.assembler import ReportAssembler


def test_report_assembler_embeds_visuals_and_tables() -> None:
    assembler = ReportAssembler(language="zh")
    manifest = {
        "visualizations": [
            {"name": "volcano", "relative_path": "plots/volcano_plot.png"},
            {"name": "heatmap", "relative_path": "plots/heatmap.png"},
            {"name": "embedding", "relative_path": "plots/embedding_pca.png"},
            {"name": "interactive", "relative_path": "plots/interactive.html"},
        ],
        "tables": [
            {"name": "top_features.json", "relative_path": "result/top_features.json"},
            {"name": "stats_summary.json", "relative_path": "result/stats_summary.json"},
        ],
    }
    report_payload = {
        "title": "Test",
        "summary": "Summary",
        "sections": [
            {"title": "差异分析", "body": "diff"},
            {"title": "相关性分析", "body": "corr"},
            {"title": "聚类与降维", "body": "embed"},
        ],
    }
    html = assembler.assemble(
        outline="",
        analysis_md="analysis",
        document_manifest=manifest,
        report_payload=report_payload,
        execution_warning="",
    )
    assert "../plots/volcano_plot.png" in html
    assert "../plots/heatmap.png" in html
    assert "../plots/embedding_pca.png" in html
    assert "../plots/interactive.html" in html
    assert "table-preview" in html


def test_report_assembler_injects_plan_and_avoids_duplicate_visuals(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_1"
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plots").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    plan_text = (
        "### 1. 假设列表\n\n"
        "| 编号 | 假设 |\n|---|---|\n| H1 | 差异假设 |\n\n"
        "### 2. 详细分析步骤\n\n"
        "1. 清洗数据\n2. 差异检验\n\n"
        "### 3. 预期产物\n\n- 火山图\n"
    )
    (session_dir / "plan" / "analysis_plan.md").write_text(plan_text, encoding="utf-8")
    (session_dir / "result" / "top_features.json").write_text("[]", encoding="utf-8")
    (session_dir / "result" / "stats_summary.json").write_text("[]", encoding="utf-8")
    (session_dir / "plots" / "volcano_plot.png").write_bytes(b"fake")
    (session_dir / "plots" / "extra_plot.png").write_bytes(b"fake")

    assembler = ReportAssembler(language="zh")
    manifest = {
        "plans": [
            {
                "plan_id": "p1",
                "entries": [
                    {
                        "kind": "plan",
                        "path": str(session_dir / "plan" / "analysis_plan.md"),
                        "relative_path": "plan/analysis_plan.md",
                    }
                ],
            }
        ],
        "visualizations": [
            {
                "name": "volcano",
                "path": str(session_dir / "plots" / "volcano_plot.png"),
                "relative_path": "plots/volcano_plot.png",
                "metadata": {"type": "volcano"},
            },
            {
                "name": "extra",
                "path": str(session_dir / "plots" / "extra_plot.png"),
                "relative_path": "plots/extra_plot.png",
                "metadata": {"type": "other"},
            },
        ],
        "tables": [
            {"name": "top_features.json", "path": str(session_dir / "result" / "top_features.json"), "relative_path": "result/top_features.json"},
            {"name": "stats_summary.json", "path": str(session_dir / "result" / "stats_summary.json"), "relative_path": "result/stats_summary.json"},
        ],
    }
    html = assembler.assemble(
        outline="",
        analysis_md="analysis",
        document_manifest=manifest,
        report_payload={"title": "t", "summary": "", "sections": [{"title": "差异分析", "body": "x"}]},
        execution_warning="",
    )
    assert "研究目标与原始假设" in html
    assert "分析方法与实施过程" in html
    assert "差异假设" in html
    assert "清洗数据" in html
    assert html.count('<img src="../plots/volcano_plot.png"') == 1
    assert "附件（正文未展示）" in html
    assert "../plots/extra_plot.png" in html
    render_manifest_path = session_dir / "meta" / "render_manifest.json"
    assert render_manifest_path.exists()
    payload = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload.get("resources"), list)


def test_outline_structure_only_not_quoted(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_2"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="### 1. 假设\n- 这是大纲行",
        analysis_md="",
        document_manifest={"visualizations": [], "tables": []},
        report_payload={"title": "t", "summary": "", "sections": [], "outline_mode": "structure_only"},
        execution_warning="",
    )
    assert "structure_only" in html
    assert "> ### 1. 假设" not in html


def test_report_renders_ab_contrast_table(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_3"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "H1",
                        "title": "H1: test",
                        "hypothesis": "test hypothesis",
                        "validation_plan_steps": ["s1"],
                        "expected_artifacts": ["result/stats_results.json"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_matrix.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "status": "ok", "missing_artifacts": [], "reason": ""}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "coverage_report.json").write_text(
        json.dumps({"mode": "partial", "missing_features": [], "filter_info": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {"s1": {"status": "ok", "output": "ok"}}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "quant_metrics": {"m1": 1, "m2": 2}, "evidence_sources": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_contrast.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "path_a": {"status": "ok", "metrics": {"m1": 1}},
                        "path_b": {"status": "ok", "metrics": {"m2": 2}},
                        "consistency": "consistent",
                        "status": "validated",
                        "conflict_reason": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_results.json",
                    "path": str(session_dir / "result" / "hypothesis_results.json"),
                    "relative_path": "result/hypothesis_results.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "路径对照（A/B）" in html
    assert "一致性判定" in html


def test_report_hypothesis_matrix_uses_unified_columns(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_matrix"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "result" / "hypothesis_matrix.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis": "H2: 预测性能验证",
                        "base_status": "ok",
                        "path_status": "incomplete",
                        "gate_status": "partial",
                        "status": "基础完成但路径未闭环",
                        "missing_artifacts": ["roc_curve.png"],
                        "reason": "路径闭环状态=incomplete；证据判定未满足：has_dual_path_status",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler._render_hypothesis_matrix(session_dir)
    assert "基础证据" in html
    assert "路径闭环" in html
    assert "基础完成但路径未闭环" in html
    assert "roc_curve.png" in html


def test_cross_hypothesis_discussion_distinguishes_base_and_closed() -> None:
    assembler = ReportAssembler(language="zh")
    text = assembler._render_cross_hypothesis_discussion(
        [
            {
                "id": "H1",
                "title": "差异检验",
                "missing": [],
                "details": ["显著特征数为 10。"],
                "gate_status": "pass",
                "path_execution_overall": "complete",
                "conflict_count": 0,
                "matrix_status": "已闭环",
                "matrix_reason": "",
            },
            {
                "id": "H2",
                "title": "预测性能验证",
                "missing": [],
                "details": ["交叉验证准确率为 0.71。"],
                "gate_status": "partial",
                "path_execution_overall": "incomplete",
                "conflict_count": 0,
                "matrix_status": "基础完成但路径未闭环",
                "matrix_reason": "路径闭环状态=incomplete；证据判定未满足：has_dual_path_status",
            },
        ]
    )
    assert "已完成基础证据落盘" in text
    assert "达到双路径闭环要求" in text
    assert "基础完成但路径未闭环" in text


def test_appendix_pdf_preview_fallback(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_4"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "result" / "sample.pdf").write_bytes(b"%PDF-1.4")
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [],
            "plans": [{"plan_id": "p1", "entries": [{"kind": "result", "relative_path": "result/sample.pdf"}]}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "application/pdf" in html
    assert "PDF 预览失败，点击打开原文件" in html


def test_report_uses_feature_dictionary_in_table_explain(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_5"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "meta").mkdir(parents=True, exist_ok=True)
    (session_dir / "result" / "top_features.json").write_text(
        json.dumps([{"feature": "peak1"}, {"feature": "peak2"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "meta" / "feature_dictionary.json").write_text(
        json.dumps({"peak1": {"display_name": "峰值1", "meaning": "代谢物A"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "top_features.json", "path": str(session_dir / "result" / "top_features.json"), "relative_path": "result/top_features.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "峰值1（代谢物A）" in html
    assert "peak2（未知语义）" in html


def test_inconclusive_hypothesis_avoids_deterministic_language(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_6"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "H1", "hypothesis": "h1", "validation_plan_steps": ["s1"], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "quant_metrics": [], "effect_metrics": [], "method_trace": [], "evidence_sources": [], "claim": "", "status": "inconclusive", "consistency": {}, "reason_code": "method_conflict", "recovery_action": "x"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_contrast.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "status": "inconclusive", "consistency": "conflict", "path_a": {}, "path_b": {}, "conflict_reason": "x"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "gate_status": "fail", "checks": {}, "reason_code": "method_conflict", "recovery_action": "x"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_results.json",
                    "path": str(session_dir / "result" / "hypothesis_results.json"),
                    "relative_path": "result/hypothesis_results.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "待定" in html or "不确定" in html


def test_report_enforces_hypothesis_section_schema(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_7"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "差异假设", "hypothesis": "Normal 与 EP 存在差异", "validation_plan_steps": ["差异检验"], "expected_artifacts": ["result/stats_results.json"]}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {"差异检验": {"status": "ok", "output": "done"}}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [{"name": "p_value", "value": 0.01}, {"name": "effect_size", "value": 0.8}],
                        "effect_metrics": [{"effect_size": 0.8}],
                        "method_trace": [{"method_family": "parametric"}],
                        "evidence_sources": ["result/stats_results.json"],
                        "claim": "supported",
                        "status": "supported",
                        "consistency": {"status": "consistent"},
                        "reason_code": "",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_contrast.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "status": "validated", "consistency": "consistent", "path_a": {}, "path_b": {}}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "gate_status": "pass", "checks": {"quant_metric_count_ge_2": True}, "reason_code": "", "recovery_action": ""}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_gate_report.json",
                    "path": str(session_dir / "result" / "hypothesis_gate_report.json"),
                    "relative_path": "result/hypothesis_gate_report.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "#### 研究问题与假设" in html
    assert "#### 方法与前置条件检查" in html
    assert "#### 执行事实（产物与状态）" in html
    assert "#### 定量结果（指标与证据）" in html
    assert "#### 结果解释（引用具体数值）" in html
    assert "#### 一致性与冲突解释（A/B 路径）" in html
    assert "#### 局限性与下一步" in html


def test_report_includes_threshold_judgement_and_gate_rule_type(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_8"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "差异假设", "hypothesis": "Normal 与 EP 存在差异", "validation_plan_steps": ["差异检验"], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [
                            {"name": "significant_p_lt_0_05", "display_name": "显著特征数", "value": 5, "threshold": ">=1", "unit": "count", "category": "significance"},
                            {"name": "strongest_abs_corr", "display_name": "最强绝对相关系数", "value": 0.74, "threshold": ">=0.5", "unit": "corr", "category": "correlation"},
                        ],
                        "effect_metrics": [{"name": "strongest_abs_corr", "value": 0.74}],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "supported",
                        "status": "validated",
                        "consistency": {"flag": "consistent"},
                        "reason_code": "",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "gate_status": "pass",
                        "gate_rule_type": "significance_and_effect",
                        "calibration_profile": "standard",
                        "checks": {"has_significance_metric": True, "has_effect_metric": True},
                        "failed_checks": [],
                        "decision_evidence": [{"check": "has_significance_metric", "passed": True, "detail": {"value": 5}}],
                        "reason_code": "",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_gate_report.json",
                    "path": str(session_dir / "result" / "hypothesis_gate_report.json"),
                    "relative_path": "result/hypothesis_gate_report.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "关键数值与阈值判定如下" in html
    assert "判定规则（原规则类型）：" in html
    assert "显著性与效应量联合判定" in html
    assert "校准档位：standard" in html
    assert "判定依据：" in html
    assert "依据：" in html
    assert "反证/冲突：" in html
    assert "边界：" in html
    assert "下一步：" in html


def test_report_renders_planned_vs_executable_followup_block(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_followup"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "meta").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "H1",
                        "title": "差异稳健性验证",
                        "hypothesis": "验证差异特征的稳健性",
                        "validation_plan_steps": ["差异检验", "稳健性复核"],
                        "expected_artifacts": ["differential_features_table.csv", "volcano_plot.png"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "meta" / "followup_contract_binding.json").write_text(
        json.dumps(
            {
                "bindings": [
                    {
                        "hypothesis_id": "H1",
                        "depth": 2,
                        "planned_followup": {
                            "title": "核心标志物的统计稳健性假设",
                            "hypothesis": "尝试用更丰富的稳健性产物补强差异结论",
                            "expected_artifacts": ["Robustness_Summary.csv", "Volcano_Plot_Refined.png"],
                        },
                        "executable_contract": {
                            "title": "差异稳健性验证",
                            "hypothesis": "回退到运行时可执行的差异稳健性验证合同",
                            "expected_artifacts": ["differential_features_table.csv", "volcano_plot.png"],
                        },
                        "binding_source": "prior_plan_hypothesis_type",
                        "rejected_expected_artifacts": ["Robustness_Summary.csv", "Volcano_Plot_Refined.png"],
                        "rejected_method_families": ["robust_resampling"],
                        "rewrite_reason": "mapped_to_runtime_supported_profile",
                        "executable": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_matrix.json").write_text(
        json.dumps(
            {"hypotheses": [{"hypothesis_id": "H1", "status": "基础完成但路径未闭环", "missing_artifacts": ["volcano_plot.png"], "reason": ""}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "coverage_report.json").write_text(
        json.dumps({"mode": "partial", "missing_features": [], "filter_info": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps(
            {"hypotheses": [{"hypothesis": "H1", "steps": {"差异检验": {"status": "ok", "output": "done"}}, "missing": []}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence.json").write_text(
        json.dumps(
            {"hypotheses": [{"hypothesis_id": "H1", "quant_metrics": {"significant_p_lt_0_05": 12}, "evidence_sources": ["result/stats_results.json"]}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_contrast.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "path_a": {"status": "validated", "metrics": {"p_count": 12}},
                        "path_b": {"status": "partial", "metrics": {"effect_size": 0.4}},
                        "consistency": "partial",
                        "status": "partial",
                        "conflict_reason": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "gate_status": "partial",
                        "checks": {"has_dual_path_status": False},
                        "failed_checks": ["has_dual_path_status"],
                        "reason_code": "path_incomplete",
                        "recovery_action": "rerun_missing_step_and_verify_outputs",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "path_execution_status.json").write_text(
        json.dumps(
            {"hypotheses": [{"hypothesis_id": "H1", "overall": "incomplete", "path_total": 2, "path_success": 1, "path_failed": 1, "missing_artifacts": ["volcano_plot.png"]}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_results.json",
                    "path": str(session_dir / "result" / "hypothesis_results.json"),
                    "relative_path": "result/hypothesis_results.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "递进规划与执行约束" in html
    assert "<strong>计划 follow-up</strong>：" in html
    assert "<strong>已归一化为可执行验证合同</strong>：" in html
    assert "Robustness_Summary.csv" in html
    assert "prior_plan_hypothesis_type" in html


def test_report_drops_stale_incomplete_language_when_final_completion_is_complete(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_final_complete"
    (session_dir / "meta").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "meta" / "completion_validation.json").write_text(
        json.dumps({"complete": True, "checks": {}, "blocking_reasons": [], "recovery_actions": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [],
            "plans": [{"plan_id": "p1", "entries": [{"kind": "meta", "path": str(session_dir / "meta" / "completion_validation.json"), "relative_path": "meta/completion_validation.json"}]}],
        },
        report_payload={
            "title": "t",
            "summary": "假设集合、证据门槛或完成态校验未通过，已中止最终结论生成，仅保留可追溯结构化装配结果。",
            "sections": [],
        },
        execution_warning="完成态校验未通过：step_closure_incomplete。",
    )
    assert "完成态校验未通过" not in html
    assert "已中止最终结论生成" not in html
    assert "最终落盘产物重新装配" in html


def test_report_overview_prefers_executed_hypothesis_title_when_plan_title_drifts(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_overview"
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "H3",
                        "title": "样本异质性",
                        "hypothesis": "EP 组内部存在亚型差异",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H3: 相关结构验证", "steps": {"correlation": {"status": "ok"}}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_results.json", "path": str(session_dir / "result" / "hypothesis_results.json"), "relative_path": "result/hypothesis_results.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "H3 相关结构验证" in html
    assert "H3 样本异质性：EP 组内部存在亚型差异" not in html


def test_volcano_explanation_contains_axes_and_color_legend(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_9"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plots").mkdir(parents=True, exist_ok=True)
    (session_dir / "result" / "stats_results.json").write_text(
        json.dumps(
            [
                {"feature": "peak1", "group_a": "Normal", "group_b": "EP", "p_value": 0.01, "mean_diff": 0.5},
                {"feature": "peak2", "group_a": "Normal", "group_b": "EP", "p_value": 0.2, "mean_diff": -0.2},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "差异假设", "hypothesis": "Normal 与 EP 存在差异", "validation_plan_steps": [], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "quant_metrics": [], "effect_metrics": [], "method_trace": [], "evidence_sources": ["result/stats_results.json"], "claim": "", "status": "inconclusive", "consistency": {}, "reason_code": "", "recovery_action": ""}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "gate_status": "partial", "gate_rule_type": "significance_and_effect", "checks": {}, "failed_checks": [], "reason_code": "", "recovery_action": ""}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "visual_binding.json").write_text(
        json.dumps({"bindings": [{"artifact": "plots/volcano_plot.png", "hypothesis": "H1"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "plots" / "volcano_plot.png").write_bytes(b"fake")
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [
                {
                    "name": "volcano",
                    "path": str(session_dir / "plots" / "volcano_plot.png"),
                    "relative_path": "plots/volcano_plot.png",
                    "metadata": {"type": "volcano"},
                }
            ],
            "tables": [],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "X=mean_diff" in html
    assert "Y=-log10(p)" in html
    assert "红色表示 p<0.05" in html


def test_report_substance_audit_detects_missing_next_step() -> None:
    assembler = ReportAssembler(language="zh")
    report_text = (
        "### H1 假设\n"
        "依据：已获得定量证据。\n"
        "反证/冲突：未检测到冲突。\n"
        "边界：当前结论适用于当前数据。\n"
        # intentionally missing 下一步
    )
    audit = assembler._build_report_substance_audit(
        outcomes=[
            {
                "id": "H1",
                "title": "h1",
                "details": ["m1=1"],
                "missing": [],
                "quant_metrics": {"m1": 1},
                "evidence_sources": ["result/a.json"],
            }
        ],
        report_text=report_text,
    )
    assert audit["basis_coverage"] == 1.0
    assert audit["next_step_coverage"] == 0.0
    missing = audit.get("missing_elements_by_hypothesis", [])
    assert missing and "next_step" in missing[0].get("missing_elements", [])


def test_report_disables_free_text_when_hypotheses_missing() -> None:
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="自由文本分析",
        document_manifest={"visualizations": [], "tables": []},
        report_payload={"title": "t", "summary": "", "sections": [{"title": "差异分析", "body": "不应直接输出"}]},
        execution_warning="",
    )
    assert "未检测到可追溯假设结构，已禁用自由文本直出" in html
    assert "不应直接输出" not in html


def test_report_replaces_raw_unknown_threshold_string(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_unknown_threshold"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "性能假设", "hypothesis": "模型性能可用于区分分组", "validation_plan_steps": [], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [{"name": "cv_std_accuracy", "display_name": "交叉验证准确率标准差", "value": 0.0138, "unit": "ratio"}],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "",
                        "status": "inconclusive",
                        "consistency": {"flag": "unknown"},
                        "reason_code": "",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "gate_status": "partial", "gate_rule_type": "predictive_performance"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_gate_report.json", "path": str(session_dir / "result" / "hypothesis_gate_report.json"), "relative_path": "result/hypothesis_gate_report.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "阈值未定义，判定=unknown，方向解释=unknown" not in html


def test_front_matter_uses_overview_and_global_process_summary(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_front_matter"
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "差异假设", "hypothesis": "存在显著差异", "validation_plan_steps": [], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "plan" / "analysis_plan.md").write_text(
        "### 2. 详细分析步骤\n\n1. 数据清洗\n2. 差异检验\n3. 可视化\n",
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_results.json",
                    "path": str(session_dir / "result" / "hypothesis_results.json"),
                    "relative_path": "result/hypothesis_results.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "<ul>" in html and "H1 差异假设" in html
    assert "本节仅保留全局流程摘要" in html
    assert "实验假设与分析验证计划" not in html


def test_method_steps_filter_plan_metadata_noise() -> None:
    assembler = ReportAssembler(language="zh")
    rendered = assembler._render_method_steps(
        [
            "验证路径 A",
            "**预期产物**：火山图",
            "数据标准化",
            "成功判据：AUC>0.8",
            "后续行动：复核",
        ]
    )
    content = "\n".join(rendered)
    assert "预期产物" not in content
    assert "成功判据" not in content
    assert "后续行动" not in content
    assert "数据标准化" in content


def test_predictive_hypothesis_missing_fields_are_explicit(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_predictive_missing"
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H2", "title": "预测假设", "hypothesis": "多特征可用于分类", "validation_plan_steps": [], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H2", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H2",
                        "quant_metrics": [{"name": "cv_mean_accuracy", "value": 0.71}],
                        "method_trace": [],
                        "evidence_sources": ["result/model_eval.json"],
                        "status": "inconclusive",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"hypothesis_id": "H2", "gate_status": "partial", "gate_rule_type": "predictive_performance", "checks": {}}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_gate_report.json",
                    "path": str(session_dir / "result" / "hypothesis_gate_report.json"),
                    "relative_path": "result/hypothesis_gate_report.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "预测假设缺少模型名称" in html
    assert "预测假设缺少主性能指标" in html
    assert "仅作描述性解释，不直接参与通过/失败判定" in html


def test_report_includes_metric_conflict_explanation(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_metric_conflict"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {"hypotheses": [{"id": "H1", "title": "分类假设", "hypothesis": "特征组合能区分分组", "validation_plan_steps": [], "expected_artifacts": []}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [
                            {"name": "centroid_accuracy", "display_name": "质心分类准确率", "value": 0.0, "unit": "ratio", "threshold": ">=0.6"},
                            {"name": "cv_mean_accuracy", "display_name": "交叉验证平均准确率", "value": 0.71, "unit": "ratio", "threshold": ">=0.6"},
                        ],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "",
                        "status": "inconclusive",
                        "consistency": {"flag": "unknown"},
                        "reason_code": "",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis_id": "H1", "gate_status": "partial", "gate_rule_type": "predictive_performance"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_gate_report.json", "path": str(session_dir / "result" / "hypothesis_gate_report.json"), "relative_path": "result/hypothesis_gate_report.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "分类性能指标冲突" in html
    assert "centroid_accuracy=0" in html


def test_report_gate_failed_check_includes_review_suggestion(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_gate_review"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {"hypotheses": [{"id": "H1", "title": "一致性假设", "hypothesis": "A/B 路径应一致", "validation_plan_steps": [], "expected_artifacts": []}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [{"name": "cv_mean_accuracy", "display_name": "交叉验证平均准确率", "value": 0.62, "unit": "ratio", "threshold": ">=0.6"}],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "",
                        "status": "inconclusive",
                        "consistency": {"flag": "conflict"},
                        "reason_code": "path_conflict",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "gate_status": "partial",
                        "gate_rule_type": "predictive_performance",
                        "checks": {"path_consistency": False, "has_dual_path_status": True},
                        "failed_checks": ["path_consistency"],
                        "reason_code": "path_conflict",
                        "recovery_action": "run_third_path_and_compare_stability",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_gate_report.json", "path": str(session_dir / "result" / "hypothesis_gate_report.json"), "relative_path": "result/hypothesis_gate_report.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "建议复核" in html
    assert "核对路径 A/B 的特征清洗与标准化参数是否一致" in html


def test_report_gate_shows_mapping_coverage_warning_for_unknown_check(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_gate_unknown_mapping"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps({"hypotheses": [{"id": "H1", "title": "未知检查项", "hypothesis": "测试", "validation_plan_steps": [], "expected_artifacts": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [{"name": "cv_mean_accuracy", "display_name": "交叉验证平均准确率", "value": 0.62, "unit": "ratio", "threshold": ">=0.6"}],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "",
                        "status": "inconclusive",
                        "consistency": {"flag": "unknown"},
                        "reason_code": "unknown_reason_code",
                        "recovery_action": "unknown_recovery_action",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "gate_status": "partial",
                        "gate_rule_type": "predictive_performance",
                        "checks": {"unknown_check_key": False},
                        "failed_checks": ["unknown_check_key"],
                        "reason_code": "unknown_reason_code",
                        "recovery_action": "unknown_recovery_action",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_gate_report.json", "path": str(session_dir / "result" / "hypothesis_gate_report.json"), "relative_path": "result/hypothesis_gate_report.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "解释覆盖告警" in html
    assert "unknown_check_key" in html
    assert "unknown_reason_code" in html


def test_report_shows_gate_evidence_alignment_notes(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_gate_alignment"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {"hypotheses": [{"id": "H1", "title": "预测假设", "hypothesis": "特征可区分分组", "validation_plan_steps": [], "expected_artifacts": []}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [{"name": "cv_std_accuracy", "display_name": "交叉验证标准差", "value": 0.02}],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "",
                        "status": "inconclusive",
                        "consistency": {"flag": "unknown"},
                        "reason_code": "metric_missing",
                        "recovery_action": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "gate_status": "partial",
                        "gate_rule_type": "predictive_performance",
                        "checks": {"has_primary_performance": False},
                        "check_details": {},
                        "failed_checks": ["has_primary_performance"],
                        "reason_code": "method_conflict",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_gate_report.json", "path": str(session_dir / "result" / "hypothesis_gate_report.json"), "relative_path": "result/hypothesis_gate_report.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "证据绑定检查" in html
    assert "缺少主性能指标" in html
    assert "reason_code 不一致" in html


def test_report_result_next_step_uses_human_readable_recovery_action(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_recovery_humanized"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps({"hypotheses": [{"id": "H1", "title": "恢复动作", "hypothesis": "测试", "validation_plan_steps": [], "expected_artifacts": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [{"name": "centroid_accuracy", "display_name": "质心分类准确率", "value": 0.4, "threshold": ">=0.6", "unit": "ratio"}],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "claim": "",
                        "status": "inconclusive",
                        "consistency": {"flag": "conflict"},
                        "reason_code": "path_conflict",
                        "recovery_action": "run_third_path_and_compare_stability",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "gate_status": "partial",
                        "gate_rule_type": "predictive_performance",
                        "checks": {"path_consistency": False},
                        "failed_checks": ["path_consistency"],
                        "reason_code": "path_conflict",
                        "recovery_action": "run_third_path_and_compare_stability",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_gate_report.json", "path": str(session_dir / "result" / "hypothesis_gate_report.json"), "relative_path": "result/hypothesis_gate_report.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "增加第三验证路径并对比稳定性" in html


def test_report_substance_audit_contains_gate_exposure_metrics() -> None:
    assembler = ReportAssembler(language="zh")
    audit = assembler._build_report_substance_audit(
        outcomes=[],
        report_text="门槛类型：xxx 当前状态：yyy gate_rule_type=abc",
    )
    assert "gate_raw_exposure_rate" in audit
    assert "gate_raw_token_hits" in audit


def test_chart_table_conflict_note_detected(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_chart_table_conflict"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "result" / "top_features.json").write_text(
        json.dumps([{"feature": "peak999"}, {"feature": "peak1"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "stats_results.json").write_text(
        json.dumps([{"feature": "peak1"}, {"feature": "peak2"}], ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    notes = assembler._chart_table_conflict_notes(session_dir)
    assert notes
    assert "peak999" in notes[0]


def test_render_method_steps_supports_path_grouping() -> None:
    assembler = ReportAssembler(language="zh")
    lines = assembler._render_method_steps(
        [
            "验证路径 A（参数化统计）",
            "t-test",
            "FDR 校正",
            "验证路径 B（非参数重采样）",
            "置换检验",
        ]
    )
    joined = "\n".join(lines)
    assert "验证路径 A：" in joined
    assert "验证路径 B：" in joined
    assert "t-test" in joined
    assert "置换检验" in joined


def test_report_prefers_executed_hypothesis_semantics_on_mismatch(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_mismatch_semantics"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "H3",
                        "title": "H3: hypothesis",
                        "hypothesis": "临床诊断预测模型效能假设",
                        "validation_plan_steps": [],
                        "expected_artifacts": [],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "plan" / "analysis_plan.md").write_text(
        "#### 假设 3：临床诊断预测模型效能假设\n",
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H3: 相关性结构", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H3",
                        "claim": "变量间存在结构化相关网络",
                        "quant_metrics": [{"name": "strongest_abs_corr", "value": 0.8}],
                        "effect_metrics": [],
                        "method_trace": [],
                        "evidence_sources": [],
                        "status": "validated",
                        "consistency": {"flag": "consistent"},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"hypothesis_id": "H3", "gate_status": "pass", "gate_rule_type": "correlation_structure", "checks": {}}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [
                {
                    "name": "hypothesis_gate_report.json",
                    "path": str(session_dir / "result" / "hypothesis_gate_report.json"),
                    "relative_path": "result/hypothesis_gate_report.json",
                }
            ],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "### H3 相关性结构" in html
    assert "一致性注记" in html
    assert "变量间存在结构化相关网络" in html
