from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from API.utils import collect_file_info, execute_code_safe
from API.config import CODE_EXECUTION_TIMEOUT

from .io_utils import ensure_dir, write_json, write_text
from .llm import LLMClient
from .prompts import (
    ANALYSIS_PROMPT,
    FILE_SUMMARY_PROMPT,
    PLANNING_PROMPT,
    CODE_FIX_PROMPT,
    CODEGEN_PROMPT,
    REPORT_OUTLINE_PROMPT,
    REPORT_PROMPT,
    SYSTEM_BASE,
)
from deepanalyze.reporting.exporter import export_report
from deepanalyze.reporting.templates import template_from_config
from .state import OrchestrationState


def _safe_json_load(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return {}


def build_graph(llm: LLMClient, config: dict[str, Any]):
    graph = StateGraph(OrchestrationState)

    def understand_files(state: OrchestrationState) -> OrchestrationState:
        workspace_dir = Path(state["workspace_dir"])
        file_info = collect_file_info(str(workspace_dir))
        messages = [
            {"role": "system", "content": SYSTEM_BASE},
            {
                "role": "user",
                "content": f"{FILE_SUMMARY_PROMPT}\n\nFiles:\n{file_info}",
            },
        ]
        summary = llm.chat(messages, max_tokens=2048)
        write_text(workspace_dir / "file_summary.md", summary)
        return {"file_summary": summary}

    def plan_analysis(state: OrchestrationState) -> OrchestrationState:
        summary = state.get("file_summary", "")
        messages = [
            {"role": "system", "content": SYSTEM_BASE},
            {
                "role": "user",
                "content": f"{PLANNING_PROMPT}\n\nSummary:\n{summary}",
            },
        ]
        plan = llm.chat(messages, max_tokens=4096)
        plan_path = Path(state["workspace_dir"]) / "analysis_plan.md"
        write_text(plan_path, plan)
        return {"plan": plan}

    def generate_code(state: OrchestrationState) -> OrchestrationState:
        plan = state.get("plan", "")
        messages = [
            {"role": "system", "content": SYSTEM_BASE},
            {
                "role": "user",
                "content": f"{CODEGEN_PROMPT}\n\nPlan:\n{plan}",
            },
        ]
        code_json = llm.chat(messages, max_tokens=4096)
        payload = _safe_json_load(code_json)
        steps = payload.get("steps", []) if isinstance(payload, dict) else []
        if not steps:
            steps = [
                {
                    "name": "analysis_step",
                    "filename": "analysis_step.py",
                    "code": "# TODO: add analysis code",
                }
            ]
        step_dir = ensure_dir(Path(state["workspace_dir"]) / "generated" / "steps")
        recorded = []
        for idx, step in enumerate(steps, start=1):
            filename = step.get("filename") or f"step_{idx}.py"
            code = step.get("code") or ""
            path = step_dir / filename
            write_text(path, code)
            recorded.append({"name": step.get("name", filename), "path": str(path)})
        write_json(step_dir / "steps.json", recorded)
        return {"code_steps": recorded}

    def execute_steps(state: OrchestrationState) -> OrchestrationState:
        results_dir = ensure_dir(Path(state["workspace_dir"]) / "generated" / "results")
        exec_results: list[dict[str, Any]] = []
        for step in state.get("code_steps", []):
            path = Path(step["path"])
            code = path.read_text(encoding="utf-8") if path.exists() else ""
            output = ""
            for attempt in range(2):
                output = execute_code_safe(
                    code, state["workspace_dir"], CODE_EXECUTION_TIMEOUT
                )
                if "[Error]" not in output and "Traceback" not in output:
                    break
                fix_messages = [
                    {"role": "system", "content": SYSTEM_BASE},
                    {
                        "role": "user",
                        "content": (
                            f"{CODE_FIX_PROMPT}\n\nError:\n{output}\n\nCode:\n{code}"
                        ),
                    },
                ]
                code = llm.chat(fix_messages, max_tokens=2048)
                write_text(path, code)
            result_path = results_dir / f"{path.stem}_output.txt"
            write_text(result_path, output)
            exec_results.append(
                {"step": step.get("name"), "output": output, "path": str(result_path)}
            )
        write_json(results_dir / "exec_results.json", exec_results)
        return {"exec_results": exec_results}

    def analyze_results(state: OrchestrationState) -> OrchestrationState:
        outputs = state.get("exec_results", [])
        summary = "\n".join([o.get("output", "") for o in outputs])
        visual_style = state.get("config", {}).get("visual_style", "academic")
        visual_interactive = state.get("config", {}).get(
            "visual_interactive", False
        )
        messages = [
            {"role": "system", "content": SYSTEM_BASE},
            {
                "role": "user",
                "content": (
                    f"{ANALYSIS_PROMPT}\n\n"
                    f"Visual style: {visual_style}\n"
                    f"Interactive: {visual_interactive}\n\n"
                    f"Outputs:\n{summary}"
                ),
            },
        ]
        analysis = llm.chat(messages, max_tokens=4096)
        write_text(Path(state["workspace_dir"]) / "analysis_results.md", analysis)
        return {"analysis_results": analysis}

    def decide_recurse(state: OrchestrationState) -> OrchestrationState:
        depth = int(state.get("depth", 1))
        max_depth = int(state.get("max_depth", 1))
        should_recurse = depth < max_depth
        return {"should_recurse": should_recurse}

    def advance_depth(state: OrchestrationState) -> OrchestrationState:
        depth = int(state.get("depth", 1))
        return {"depth": depth + 1}

    def report_outline(state: OrchestrationState) -> OrchestrationState:
        analysis = state.get("analysis_results", "")
        messages = [
            {"role": "system", "content": SYSTEM_BASE},
            {
                "role": "user",
                "content": f"{REPORT_OUTLINE_PROMPT}\n\nAnalysis:\n{analysis}",
            },
        ]
        outline = llm.chat(messages, max_tokens=2048)
        write_text(Path(state["workspace_dir"]) / "report_outline.md", outline)
        return {"report_outline": outline}

    def generate_report(state: OrchestrationState) -> OrchestrationState:
        outline = state.get("report_outline", "")
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        report_format = state.get("config", {}).get("report_format", "html")
        export_mode = state.get("config", {}).get("report_export_mode", "html_convert")
        messages = [
            {"role": "system", "content": SYSTEM_BASE},
            {
                "role": "user",
                "content": (
                    f"{REPORT_PROMPT}\n\nLanguage: {language}\nFormat: {report_format}\n"
                    f"Export mode: {export_mode}\n"
                    f"Outline:\n{outline}\n\nAnalysis:\n{analysis}"
                ),
            },
        ]
        report = llm.chat(messages, max_tokens=4096)
        export_report(
            report,
            output_dir=Path(state["workspace_dir"]),
            report_format=report_format,
            export_mode=export_mode,
            template=template_from_config(),
        )
        return {"report": report}

    graph.add_node("understand_files", understand_files)
    graph.add_node("plan_analysis", plan_analysis)
    graph.add_node("generate_code", generate_code)
    graph.add_node("execute_steps", execute_steps)
    graph.add_node("analyze_results", analyze_results)
    graph.add_node("decide_recurse", decide_recurse)
    graph.add_node("advance_depth", advance_depth)
    graph.add_node("report_outline", report_outline)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("understand_files")
    graph.add_edge("understand_files", "plan_analysis")
    graph.add_edge("plan_analysis", "generate_code")
    graph.add_edge("generate_code", "execute_steps")
    graph.add_edge("execute_steps", "analyze_results")
    graph.add_edge("analyze_results", "decide_recurse")
    graph.add_conditional_edges(
        "decide_recurse",
        lambda s: "recurse" if s.get("should_recurse") else "report",
        {
            "recurse": "advance_depth",
            "report": "report_outline",
        },
    )
    graph.add_edge("advance_depth", "plan_analysis")
    graph.add_edge("report_outline", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()
