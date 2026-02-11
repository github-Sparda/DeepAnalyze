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
    assert "<iframe" in html
    assert "table-preview" in html
