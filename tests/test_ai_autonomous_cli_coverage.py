from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import src.cli.ai_autonomous_cli as auto_cli


class _DummyStateManager:
    def __init__(self, root: Path):
        self.root = root
        self.updated = []
        self._sessions = [{"session_id": "sess-1", "session_name": "demo"}]

    def _get_session_path(self, session_id: str) -> Path:
        p = self.root / session_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def update_session_state(self, session_id: str, state):
        self.updated.append((session_id, state))

    def get_session_state(self, session_id: str):
        return {"session_id": session_id, "analysis_results": "ok", "hypotheses": ["h1"]}

    def list_sessions(self):
        return self._sessions


class _DummyGraph:
    def __init__(self, state):
        self.state = state

    def invoke(self, initial_state):
        return {**initial_state, **self.state}


def _make_cli(monkeypatch, tmp_path: Path):
    sm = _DummyStateManager(tmp_path)
    monkeypatch.setattr(auto_cli, "StateManager", lambda: sm)
    monkeypatch.setattr(auto_cli, "ErrorHandler", lambda: SimpleNamespace(handle_error=lambda *a, **k: "handled"))
    monkeypatch.setattr(auto_cli, "create_new_session", lambda session_name, tags: "sess-new")
    cli = auto_cli.AIAutonomousAnalyzerCLI()
    return cli, sm


def test_autonomous_cli_run_analysis_success(monkeypatch, tmp_path: Path) -> None:
    cli, sm = _make_cli(monkeypatch, tmp_path)
    data_file = tmp_path / "data.csv"
    data_file.write_text("a,b\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(auto_cli, "LLMClient", lambda: object())
    monkeypatch.setattr(
        auto_cli,
        "build_graph",
        lambda llm, config: _DummyGraph(
            {
                "session_id": "sess-new",
                "run_id": "run-1",
                "hypotheses": ["H1", "H2"],
                "analysis_results": "发现 1\n发现 2",
                "artifacts": [{"name": "a.txt"}],
                "visualizations": [{"name": "chart.png"}],
                "report": "full report",
            }
        ),
    )
    args = cli.parser.parse_args(["--data-file", str(data_file), "--analysis-goal", "goal", "--max-depth", "2"])
    assert cli.run_autonomous_analysis(args) is True
    assert sm.updated and sm.updated[0][0] == "sess-new"


def test_autonomous_cli_run_analysis_failure_and_continue(monkeypatch, tmp_path: Path) -> None:
    cli, sm = _make_cli(monkeypatch, tmp_path)
    monkeypatch.setattr(auto_cli, "LLMClient", lambda: object())
    monkeypatch.setattr(auto_cli, "build_graph", lambda llm, config: (_ for _ in ()).throw(RuntimeError("boom")))

    args = cli.parser.parse_args(["--session-id", "sess-old", "--continue"])
    assert cli.run_autonomous_analysis(args) is False

    args2 = cli.parser.parse_args(["--data-file", str(tmp_path / "missing.csv")])
    assert cli.run_autonomous_analysis(args2) is False


def test_autonomous_cli_interactive_and_run_entrypoints(monkeypatch, tmp_path: Path) -> None:
    cli, sm = _make_cli(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(cli, "run_autonomous_analysis", lambda args: calls.append(("run", args.data_file, args.session_id)) or True)
    inputs = iter(["help", "analyze demo.csv goal", "session list", "session info", "continue sess-1", "unknown", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    cli.interactive_mode(cli.parser.parse_args([]))
    assert any(item[0] == "run" for item in calls)

    monkeypatch.setattr(cli.parser, "parse_args", lambda: SimpleNamespace(interactive=False, data_file="x.csv", session_id=None, continue_session=False))
    with pytest.raises(SystemExit) as exc:
        cli.run()
    assert exc.value.code == 0

    monkeypatch.setattr(cli.parser, "parse_args", lambda: SimpleNamespace(interactive=False, data_file=None, session_id=None, continue_session=False))
    cli.run()
