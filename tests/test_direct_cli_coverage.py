from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import src.cli.direct_cli as direct_cli


class _DummyAssistantEngine:
    def process_message(self, session_id, message, context=None):
        return {"response": f"reply:{message}:{context.get('k') if context else ''}"}


class _DummyReportManager:
    def create_report(self, session_id, report_type, title, content):
        return SimpleNamespace(report_id="r1", title=title, content=content)


def _build_cli(monkeypatch, tmp_path: Path):
    state = {"visualizations": []}
    monkeypatch.setattr(direct_cli, "StateManager", lambda: object())
    monkeypatch.setattr(direct_cli, "ErrorHandler", lambda: object())
    monkeypatch.setattr(direct_cli, "AIAssistantEngine", lambda: _DummyAssistantEngine())
    monkeypatch.setattr(direct_cli, "ReportManager", lambda: _DummyReportManager())
    monkeypatch.setattr(direct_cli, "create_new_session", lambda session_name, tags: "sess-1")
    monkeypatch.setattr(direct_cli, "get_session_state", lambda session_id: state)
    monkeypatch.setattr(direct_cli, "update_session_state", lambda session_id, payload: state.update(payload))
    cli = direct_cli.DirectDeepAnalyzeCLI()
    return cli, state


def test_direct_cli_analyze_and_assistant_paths(monkeypatch, tmp_path: Path) -> None:
    cli, state = _build_cli(monkeypatch, tmp_path)
    data_file = tmp_path / "data.csv"
    data_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    monkeypatch.setattr("src.api.config.USE_ORCHESTRATOR", False)
    monkeypatch.setattr(direct_cli, "analyze_dataset", lambda file_path, session_id, analysis_types=None: {"summary": "ok"})
    result = cli.analyze_data_direct(str(data_file), ["descriptive"])
    assert result is not None and result["summary"] == "ok"
    assert state["data_file"] == str(data_file.resolve())

    monkeypatch.setattr("src.api.config.USE_ORCHESTRATOR", True)
    monkeypatch.setattr(cli, "_run_llm_orchestrated_analysis", lambda file_path, analysis_types=None: {"llm": True})
    result = cli.analyze_data_direct(str(data_file))
    assert result == {"llm": True, "data_file": str(data_file.resolve())}

    response = cli.ai_assistant_direct("question", {"k": "v"})
    assert response == "reply:question:v"
    assert "analysis_history" in state


def test_direct_cli_visualization_and_report_paths(monkeypatch, tmp_path: Path) -> None:
    cli, state = _build_cli(monkeypatch, tmp_path)
    data_file = tmp_path / "data.csv"
    data_file.write_text("x,y\n1,2\n2,3\n3,4\n", encoding="utf-8")
    cli.last_data_file = str(data_file)

    out = tmp_path / "chart.png"
    out.write_text("img", encoding="utf-8")
    monkeypatch.setattr(direct_cli, "render_distribution", lambda df, column, output_path, style="academic": Path(out))
    viz = cli.generate_visualization_direct({}, chart_type="distribution", output_path=str(out))
    assert viz == str(out)
    assert state["visualizations"][0]["type"] == "distribution"

    report = cli.generate_report_direct({"score": 1}, include_visualizations=False)
    assert report.report_id == "r1"
    assert state["reports"][0]["report_id"] == "r1"

    existing_viz = tmp_path / "viz.png"
    existing_viz.write_text("x", encoding="utf-8")
    state["visualizations"] = [{"path": str(existing_viz), "metadata": {"type": "distribution"}}]
    content = cli._embed_visualizations_in_report("主体")
    assert "可视化图表" in content and str(existing_viz) in content


def test_direct_cli_orchestrated_and_sample_visualizations(monkeypatch, tmp_path: Path) -> None:
    cli, state = _build_cli(monkeypatch, tmp_path)
    data_file = tmp_path / "data.csv"
    data_file.write_text("a,b\n1,2\n", encoding="utf-8")

    monkeypatch.setattr("src.api.config.MAX_RECURSION_DEPTH", 2)
    monkeypatch.setattr("src.api.config.REPORT_FORMAT", "html")
    monkeypatch.setattr("src.api.config.REPORT_LANGUAGE", "zh")
    monkeypatch.setattr("src.api.config.REPORT_EXPORT_MODE", "inline")
    monkeypatch.setattr("src.api.config.WORKSPACE_BASE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setattr(
        "src.core.orchestration.runner.run_orchestrated_docs_analysis",
        lambda session_id, config: {
            "report": "ready",
            "depth_prompt": "",
            "continuation_required": False,
            "docs/analysis_results": "",
        },
    )

    state_payload = cli.run_orchestrated_analysis(str(data_file), "goal", max_depth=2)
    assert state_payload["report"] == "ready"

    called = []
    monkeypatch.setattr(direct_cli, "render_distribution", lambda *args, **kwargs: called.append("distribution"))
    monkeypatch.setattr(direct_cli, "render_trend", lambda *args, **kwargs: called.append("trend"))
    monkeypatch.setattr(direct_cli, "render_comparison", lambda *args, **kwargs: called.append("comparison"))
    cli._generate_sample_visualizations()
    assert {"distribution", "trend", "comparison"} <= set(called)


def test_direct_cli_error_and_command_paths(monkeypatch, tmp_path: Path) -> None:
    state = {}
    monkeypatch.setattr(direct_cli, "StateManager", lambda: object())
    monkeypatch.setattr(direct_cli, "ErrorHandler", lambda: object())
    monkeypatch.setattr(direct_cli, "AIAssistantEngine", lambda: _DummyAssistantEngine())
    monkeypatch.setattr(direct_cli, "ReportManager", lambda: _DummyReportManager())
    monkeypatch.setattr(direct_cli, "create_new_session", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("no session")))
    monkeypatch.setattr(direct_cli, "get_session_state", lambda session_id: state)
    monkeypatch.setattr(direct_cli, "update_session_state", lambda session_id, payload: state.update(payload))
    cli = direct_cli.DirectDeepAnalyzeCLI()
    assert cli.current_session_id is None

    assert cli.analyze_data_direct(str(tmp_path / "missing.csv")) is None
    monkeypatch.setattr("src.api.config.USE_ORCHESTRATOR", False)
    monkeypatch.setattr(direct_cli, "analyze_dataset", lambda **kwargs: {"error": "bad"})
    bad_file = tmp_path / "data.csv"
    bad_file.write_text("a\n1\n", encoding="utf-8")
    assert cli.analyze_data_direct(str(bad_file)) is None
    monkeypatch.setattr(direct_cli, "analyze_dataset", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    assert cli.analyze_data_direct(str(bad_file)) is None

    monkeypatch.setattr("src.core.orchestration.runner.run_orchestrated_docs_analysis", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("orchestrator")))
    monkeypatch.setattr("src.api.config.MAX_RECURSION_DEPTH", 1)
    monkeypatch.setattr("src.api.config.REPORT_FORMAT", "html")
    monkeypatch.setattr("src.api.config.REPORT_LANGUAGE", "zh")
    monkeypatch.setattr(direct_cli, "analyze_dataset", lambda file_path, session_id, analysis_types=None: {"fallback": True})
    assert cli._run_llm_orchestrated_analysis(bad_file) == {"fallback": True}

    # visualization edge cases
    cli.last_data_file = None
    assert cli.generate_visualization_direct({}, output_path=str(tmp_path / "out.png")) is None
    json_file = tmp_path / "data.json"
    json_file.write_text('[{"label":"x"}]', encoding="utf-8")
    cli.last_data_file = str(json_file)
    assert cli.generate_visualization_direct({}, output_path=str(tmp_path / "out.png")) is None
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("x", encoding="utf-8")
    cli.last_data_file = str(txt_file)
    assert cli.generate_visualization_direct({}, output_path=str(tmp_path / "out.png")) is None
    csv_one_numeric = tmp_path / "one.csv"
    csv_one_numeric.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
    cli.last_data_file = str(csv_one_numeric)
    assert cli.generate_visualization_direct({}, chart_type="correlation", output_path=str(tmp_path / "corr.png")) is None

    # ai assistant / report failures
    monkeypatch.setattr(cli.assistant_engine, "process_message", lambda **kwargs: None)
    assert cli.ai_assistant_direct("q") is None
    monkeypatch.setattr(cli.assistant_engine, "process_message", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("x")))
    assert cli.ai_assistant_direct("q") is None
    monkeypatch.setattr(cli.report_manager, "create_report", lambda **kwargs: None)
    assert cli.generate_report_direct({"a": 1}) is None
    monkeypatch.setattr(cli.report_manager, "create_report", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("x")))
    assert cli.generate_report_direct({"a": 1}) is None
    content = cli._prepare_enhanced_report_content(object(), include_visualizations=False)
    assert "object" in content

    # session info / list results / commands
    cli.current_session_id = "sess-x"
    monkeypatch.setattr(direct_cli, "get_session_state", lambda session_id: None)
    cli.show_session_info()
    monkeypatch.setattr(direct_cli, "get_session_state", lambda session_id: {"analysis_results": {"data_summary": {"rows": 1}, "insights": ["i1"]}})
    cli.list_analysis_results()
    monkeypatch.setattr(direct_cli.Confirm, "ask", staticmethod(lambda *a, **k: True))
    calls = []
    monkeypatch.setattr(cli, "show_help", lambda: calls.append("help"))
    monkeypatch.setattr(cli, "show_session_info", lambda: calls.append("info"))
    monkeypatch.setattr(cli, "analyze_data_direct", lambda *a, **k: calls.append("analyze"))
    monkeypatch.setattr(cli, "run_orchestrated_analysis", lambda *a, **k: calls.append("orchestrate"))
    monkeypatch.setattr(cli, "generate_visualization_direct", lambda *a, **k: calls.append("viz"))
    monkeypatch.setattr(cli, "generate_report_direct", lambda *a, **k: calls.append("report"))
    monkeypatch.setattr(cli, "list_analysis_results", lambda: calls.append("results"))
    monkeypatch.setattr(direct_cli, "get_session_state", lambda session_id: {"analysis_results": {"x": 1}})
    assert cli.handle_direct_command("help")
    assert cli.handle_direct_command("info")
    assert cli.handle_direct_command(f"analyze {bad_file}")
    assert cli.handle_direct_command(f"orchestrate {bad_file} 1 more goal")
    assert cli.handle_direct_command("viz correlation")
    assert cli.handle_direct_command("report analytical --no-viz")
    assert cli.handle_direct_command("results")
    assert cli.handle_direct_command("clear")
    assert cli.handle_direct_command("unknown") is False
    assert calls


def test_direct_cli_batch_interactive_and_main(monkeypatch, tmp_path: Path) -> None:
    cli, _ = _build_cli(monkeypatch, tmp_path)
    args = SimpleNamespace(orchestrated="file.csv", analysis_goal="goal", max_depth=1, analyze=None, analysis_types=None, visualize=False, chart_type="auto", report=False, report_type="analytical", include_visualizations=True, query=None, session_info=False, results=False)
    called = []
    monkeypatch.setattr(cli, "run_orchestrated_analysis", lambda *a, **k: called.append("orch"))
    cli.run_batch_mode(args)
    args.orchestrated = None
    args.analyze = "file.csv"
    monkeypatch.setattr(cli, "analyze_data_direct", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(cli, "generate_visualization_direct", lambda *a, **k: called.append("viz"))
    monkeypatch.setattr(cli, "generate_report_direct", lambda *a, **k: called.append("report"))
    args.visualize = True
    args.report = True
    cli.run_batch_mode(args)
    args.analyze = None
    args.query = "hello"
    monkeypatch.setattr(cli, "ai_assistant_direct", lambda *a, **k: called.append("query"))
    cli.run_batch_mode(args)
    args.query = None
    args.session_info = True
    monkeypatch.setattr(cli, "show_session_info", lambda: called.append("info"))
    cli.run_batch_mode(args)
    args.session_info = False
    args.results = True
    monkeypatch.setattr(cli, "list_analysis_results", lambda: called.append("results"))
    cli.run_batch_mode(args)
    assert {"orch", "viz", "report", "query", "info", "results"} <= set(called)

    monkeypatch.setattr(direct_cli, "DirectDeepAnalyzeCLI", lambda: SimpleNamespace(interactive_mode=lambda: called.append("interactive"), run_batch_mode=lambda args: called.append("batch")))
    monkeypatch.setattr(direct_cli.console, "print", lambda *a, **k: None)
    monkeypatch.setattr(direct_cli.argparse.ArgumentParser, "parse_args", lambda self: SimpleNamespace(analyze=None, orchestrated=None, query=None, session_info=False, results=False, interactive=True))
    direct_cli.main()
    monkeypatch.setattr(direct_cli.argparse.ArgumentParser, "parse_args", lambda self: SimpleNamespace(analyze="x", orchestrated=None, query=None, session_info=False, results=False, interactive=False))
    direct_cli.main()
    assert "interactive" in called and "batch" in called
