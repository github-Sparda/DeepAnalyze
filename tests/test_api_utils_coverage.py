from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.api import utils


def test_api_utils_workspace_message_and_parsing_helpers(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(utils, "WORKSPACE_BASE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setattr(utils, "HTTP_SERVER_BASE", "http://localhost:9000")

    workspace = utils.get_thread_workspace("thread-1")
    assert Path(workspace).exists()
    assert utils.build_download_url("thread-1", "report.md") == "http://localhost:9000/thread-1/report.md"

    data_dir = tmp_path / "messages"
    data_dir.mkdir()
    (data_dir / "a.csv").write_text("x\n1\n", encoding="utf-8")
    messages = utils.prepare_vllm_messages(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "text", "text": {"value": "hello"}}]}],
        str(data_dir),
    )
    assert messages[-1]["content"].startswith("# Instruction")
    assert "# Data" in messages[-1]["content"]

    assert utils.extract_text_from_content([{"type": "text", "text": {"value": "A"}}, {"type": "x"}]) == "A"
    assert utils.extract_code_from_segment("<Code>```python\nprint(1)\n```</Code>") == "print(1)"
    assert utils.fix_tags_and_codeblock("<Code>```python\nprint(1)") .endswith("</Code>")
    assert "Appendix: Detailed Process" in utils.extract_sections_from_history(
        [{"role": "assistant", "content": "<Analyze>x</Analyze><Answer>y</Answer>"}]
    )


def test_api_utils_code_execution_and_reports(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(utils, "ALLOW_ABSOLUTE_IO", False)
    assert utils._detect_disallowed_io("open('/tmp/x')") is True
    assert "42" in utils.execute_code_safe("print(42)", str(tmp_path))
    assert "[Error]: blocked file IO outside workspace" in utils.execute_code_safe("open('/tmp/x')", str(tmp_path))

    async_output = asyncio.run(utils.execute_code_safe_async("print('async')", str(tmp_path)))
    assert "async" in async_output

    md_path = utils.save_markdown_report("# hello", "report", tmp_path)
    assert md_path.exists()

    sink: list[dict[str, str]] = []
    report_block = utils.generate_report_from_messages(
        [{"role": "user", "content": "q"}],
        "<Answer>done</Answer>",
        str(tmp_path),
        "thread-2",
        generated_files_sink=sink,
    )
    assert report_block == "\n"
    assert sink and sink[0]["name"].endswith(".md")

    artifact = tmp_path / "artifact.txt"
    artifact.write_text("ok", encoding="utf-8")
    sink2: list[dict[str, str]] = []
    assert utils.render_file_block([artifact], str(tmp_path), "thread-2", sink2) == ""
    assert sink2 and sink2[0]["name"] == "artifact.txt"

    manifest = [{"path": str(artifact), "kind": "text", "source": "unit", "timestamp": "now"}]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    artifacts = utils.build_artifact_list(str(tmp_path), "thread-2")
    assert artifacts[0]["kind"] == "text"


def test_workspace_tracker_collects_added_and_modified_files(tmp_path: Path) -> None:
    generated_dir = tmp_path / "generated"
    tracker = utils.WorkspaceTracker(str(tmp_path), str(generated_dir))

    added = tmp_path / "new.txt"
    added.write_text("new", encoding="utf-8")
    changed = tmp_path / "existing.txt"
    changed.write_text("old", encoding="utf-8")
    tracker.before_state = {changed.resolve(): (1, 1)}
    changed.write_text("changed", encoding="utf-8")

    artifacts = tracker.diff_and_collect()
    names = {p.name for p in artifacts}
    assert any(name.startswith("new") for name in names)
    assert any("existing_modified" in name for name in names)
