from __future__ import annotations

from pathlib import Path

from src.core.reporting.exporter import export_report


def test_html_export_auto_converts_markdown_structure(tmp_path: Path) -> None:
    content = "# 报告标题\n\n- 要点一\n- 要点二"
    output = export_report(
        content,
        output_dir=tmp_path,
        report_format="html",
        export_mode="html",
        base_name="report_v1",
    )
    html = output.read_text(encoding="utf-8")
    assert "<h1>报告标题</h1>" in html
    assert "<li>要点一</li>" in html


def test_html_export_keeps_raw_when_no_markdown_structure(tmp_path: Path) -> None:
    content = "plain text body without markdown markers"
    output = export_report(
        content,
        output_dir=tmp_path,
        report_format="html",
        export_mode="html",
        base_name="report_v1",
    )
    html = output.read_text(encoding="utf-8")
    assert "plain text body without markdown markers" in html
