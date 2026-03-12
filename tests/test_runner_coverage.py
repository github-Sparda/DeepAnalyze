from __future__ import annotations

import json
from pathlib import Path

from src.core.orchestration import runner


class _DummyGraph:
    def __init__(self) -> None:
        self.initial = None

    def invoke(self, initial):
        self.initial = initial
        return {**initial, "result": "ok"}


def test_run_orchestrated_docs_analysis_clamps_depth_and_force_rounds(monkeypatch, tmp_path: Path) -> None:
    graph = _DummyGraph()
    writes: list[dict] = []

    def fake_init_data_sessions_active(session_dir: Path) -> dict[str, Path]:
        report_dir = session_dir / "report"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "report_v1.html").write_text("latest report", encoding="utf-8")
        return {
            "report": report_dir,
            "result": session_dir / "result",
            "meta": session_dir / "meta",
        }

    monkeypatch.setattr(runner, "create_graph", lambda llm, config: graph)
    monkeypatch.setattr(runner, "LLMClient", lambda: object())
    monkeypatch.setattr(runner, "init_data_sessions_active", fake_init_data_sessions_active)
    monkeypatch.setattr(runner, "REPRO_METADATA_ENABLED", True)
    monkeypatch.setattr(runner, "TRACE_ENABLED", True)
    monkeypatch.setattr(runner, "FORCE_ROUNDS", 1)
    monkeypatch.setattr(runner, "hash_file", lambda p: f"hash:{Path(p).name}")
    monkeypatch.setattr(runner, "write_run_metadata", lambda session_dir, payload: writes.append(payload))

    data_file = tmp_path / "session-a" / "input.csv"
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text("a,b\n1,2\n", encoding="utf-8")

    result = runner.run_orchestrated_docs_analysis(
        session_id="session-a",
        config={"workspace_base_dir": str(tmp_path), "max_depth": 9, "force_rounds": 9},
    )

    assert result["result"] == "ok"
    assert graph.initial is not None
    assert graph.initial["max_depth"] == 3
    assert graph.initial["force_rounds"] == 3
    assert graph.initial["report"] == "latest report"
    assert graph.initial["report_versions"]
    assert writes and writes[0]["config"]["force_rounds"] == 3
    assert "input.csv" in json.dumps(writes[0]["input_files"], ensure_ascii=False)


def test_run_orchestrated_docs_analysis_allows_zero_depth(monkeypatch, tmp_path: Path) -> None:
    graph = _DummyGraph()

    monkeypatch.setattr(runner, "create_graph", lambda llm, config: graph)
    monkeypatch.setattr(runner, "LLMClient", lambda: object())
    monkeypatch.setattr(
        runner,
        "init_data_sessions_active",
        lambda session_dir: {"report": session_dir / "report", "result": session_dir / "result"},
    )
    monkeypatch.setattr(runner, "REPRO_METADATA_ENABLED", False)
    monkeypatch.setattr(runner, "TRACE_ENABLED", False)
    monkeypatch.setattr(runner, "FORCE_ROUNDS", 2)

    runner.run_orchestrated_docs_analysis(
        session_id="session-b",
        config={"workspace_base_dir": str(tmp_path), "max_depth": 0},
    )

    assert graph.initial is not None
    assert graph.initial["depth"] == 0
    assert graph.initial["max_depth"] == 0
    assert graph.initial["force_rounds"] == 0
    assert graph.initial["trace_id"] == ""
