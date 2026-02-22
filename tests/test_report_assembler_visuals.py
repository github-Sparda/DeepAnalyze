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
    assert "阈值判定结果：" in html
    assert "规则类型：significance_and_effect" in html
    assert "校准档位：standard" in html
    assert "判定依据" in html
    assert "依据：" in html
    assert "反证/冲突：" in html
    assert "边界：" in html
    assert "下一步：" in html


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
