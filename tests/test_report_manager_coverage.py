from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.reporting.manager import (
    ExportFormat,
    ReportManager,
    ReportType,
    ReportStatus,
    create_new_report,
    get_report_manager,
    list_session_reports,
)


def test_report_manager_create_get_list_update_delete(monkeypatch, tmp_path: Path) -> None:
    updates = []
    monkeypatch.setattr("src.core.reporting.manager.update_session_state", lambda sid, payload: updates.append((sid, payload)) or True)
    monkeypatch.setattr("src.core.reporting.manager.get_session_state", lambda sid: {"dummy": True})
    manager = ReportManager(tmp_path)

    meta = manager.create_report(
        "s1",
        title="分析报告",
        content="# hello",
        report_type=ReportType.EXECUTIVE,
        template_id="executive",
        metadata={"author": "tester", "tags": ["a"], "keywords": ["k"]},
    )
    assert meta.status == ReportStatus.DRAFT
    got = manager.get_report("s1", meta.report_id)
    assert got and got["metadata"]["title"] == "分析报告"

    listed = manager.list_reports("s1")
    assert listed and listed[0].report_id == meta.report_id

    assert manager.update_report("s1", meta.report_id, content="# updated", metadata_updates={"title": "新标题"}) is True
    assert manager.get_report("s1", meta.report_id)["metadata"]["title"] == "新标题"
    assert manager.delete_report("s1", meta.report_id) is True
    assert manager.delete_report("s1", meta.report_id) is False
    assert updates


def test_report_manager_export_and_helpers(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("src.core.reporting.manager.update_session_state", lambda sid, payload: True)
    monkeypatch.setattr("src.core.reporting.manager.get_session_state", lambda sid: {})
    manager = ReportManager(tmp_path)
    meta = manager.create_report("s2", "报告", "# 标题\n正文", metadata={"author": "tester"})

    html_path = manager.export_report("s2", meta.report_id, ExportFormat.HTML)
    md_path = manager.export_report("s2", meta.report_id, ExportFormat.MARKDOWN)
    json_path = manager.export_report("s2", meta.report_id, ExportFormat.JSON)
    assert Path(html_path).exists()
    assert Path(md_path).exists()
    assert json.loads(Path(json_path).read_text(encoding="utf-8"))["metadata"]["title"] == "报告"

    # fallback branches without optional deps
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"weasyprint", "docx"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    pdf_path = manager.export_report("s2", meta.report_id, ExportFormat.PDF, str(tmp_path / "x.pdf"))
    docx_path = manager.export_report("s2", meta.report_id, ExportFormat.DOCX, str(tmp_path / "x.docx"))
    assert pdf_path.endswith(".md")
    assert docx_path.endswith(".md")

    assert "<p>" in manager._markdown_to_html("# hi\n\nbody")
    assert isinstance(get_report_manager(tmp_path), ReportManager)
    helper_meta = create_new_report("s3", "新报告", "内容")
    assert helper_meta.title == "新报告"
    assert isinstance(list_session_reports("s3"), list)
