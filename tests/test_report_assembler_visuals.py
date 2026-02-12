from __future__ import annotations

from pathlib import Path

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
    assert html.count("../plots/volcano_plot.png") == 1
    assert "附件（正文未展示）" in html
    assert "../plots/extra_plot.png" in html
