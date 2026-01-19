from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd
from langgraph.graph import END, StateGraph

from API.utils import collect_file_info, execute_code_safe
from API.config import (
    CODE_EXECUTION_TIMEOUT,
    EXECUTION_MAX_RETRIES,
    CODEGEN_CONCURRENCY,
    EXECUTION_CONCURRENCY,
    GRAPH_MONITORING,
    TRACE_ENABLED,
    DATA_QUALITY_ENABLED,
)

from .io_utils import (
    ensure_dir,
    init_workspace,
    write_json,
    write_text,
    record_artifact,
    record_node_log,
    record_run_summary,
)
from .llm import LLMClient
from .prompts import get_prompt, get_system, render_role_prompt
from deepanalyze.reporting.exporter import export_report
from deepanalyze.reporting.templates import template_from_config
from .state import OrchestrationState


def _safe_json_load(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _extract_hypotheses(plan_text: str) -> list[str]:
    hypotheses = []
    for line in plan_text.splitlines():
        stripped = line.strip().lstrip("- ")
        if not stripped:
            continue
        if stripped.lower().startswith("hypothesis"):
            hypotheses.append(stripped)
    return hypotheses[:10]


def _run_node(name: str, func, config: dict[str, Any]):
    def wrapper(state: OrchestrationState) -> OrchestrationState:
        monitoring = config.get("graph_monitoring", GRAPH_MONITORING)
        start = time.time()
        error = None
        output: dict[str, Any] = {}
        try:
            output = func(state)
        except Exception as exc:
            error = str(exc)
            output = {"errors": [error]}
        duration = time.time() - start
        telemetry = list(state.get("telemetry", []))
        telemetry.append(
            {
                "node": name,
                "status": "error" if error else "success",
                "duration_sec": round(duration, 3),
                "timestamp": int(start),
            }
        )
        output["telemetry"] = telemetry
        if monitoring:
            record_node_log(
                state["workspace_dir"],
                name,
                {
                    "node": name,
                    "output": output,
                    "error": error,
                    "duration_sec": duration,
                    "trace_id": state.get("trace_id") if TRACE_ENABLED else "",
                },
            )
        return output

    return wrapper


def build_graph(llm: LLMClient, config: dict[str, Any]):
    graph = StateGraph(OrchestrationState)

    def understand_files(state: OrchestrationState) -> OrchestrationState:
        workspace_dir = Path(state["workspace_dir"])
        init_workspace(workspace_dir)
        file_info = collect_file_info(str(workspace_dir))
        language = state.get("config", {}).get("report_language", "zh")
        messages = render_role_prompt(
            "file_understanding",
            language,
            prompt_key="file_summary",
            file_info=file_info,
        )
        summary = llm.chat(messages, max_tokens=2048)
        summary_path = workspace_dir / "plan" / "file_summary.md"
        write_text(summary_path, summary)
        record_artifact(workspace_dir, summary_path, "plan", "understand_files")
        return {"file_summary": summary}

    def data_quality(state: OrchestrationState) -> OrchestrationState:
        if not config.get("data_quality_enabled", DATA_QUALITY_ENABLED):
            return {}
        workspace_dir = Path(state["workspace_dir"])
        results: dict[str, Any] = {"datasets": []}
        for path in workspace_dir.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".csv", ".tsv", ".xlsx", ".xls", ".json"}:
                continue
            try:
                if path.suffix.lower() in {".csv", ".tsv"}:
                    df = pd.read_csv(path)
                elif path.suffix.lower() in {".xlsx", ".xls"}:
                    df = pd.read_excel(path)
                else:
                    df = pd.read_json(path)
                missing = df.isna().mean().to_dict()
                stats = json.loads(df.describe(include="all").to_json())
                results["datasets"].append(
                    {
                        "file": path.name,
                        "rows": int(df.shape[0]),
                        "cols": int(df.shape[1]),
                        "missing_rate": missing,
                        "stats": stats,
                    }
                )
            except Exception as exc:
                results["datasets"].append({"file": path.name, "error": str(exc)})
        quality_path = workspace_dir / "result" / "data_quality.json"
        write_json(quality_path, results)
        record_artifact(workspace_dir, quality_path, "result", "data_quality")
        return {"data_quality": results}

    def plan_analysis(state: OrchestrationState) -> OrchestrationState:
        summary = state.get("file_summary", "")
        language = state.get("config", {}).get("report_language", "zh")
        messages = render_role_prompt(
            "planning",
            language,
            prompt_key="planning",
            summary=summary,
        )
        plan = llm.chat(messages, max_tokens=4096)
        plan_path = Path(state["workspace_dir"]) / "plan" / "analysis_plan.md"
        write_text(plan_path, plan)
        record_artifact(state["workspace_dir"], plan_path, "plan", "plan_analysis")

        struct_prompt = get_prompt("planning_struct", language)
        struct_messages = [
            {"role": "system", "content": get_system(language)},
            {"role": "user", "content": f"{struct_prompt}\n\nPlan:\n{plan}"},
        ]
        plan_json_raw = llm.chat(struct_messages, max_tokens=2048)
        plan_json = _safe_json_load(plan_json_raw)
        if not plan_json:
            plan_json = {
                "hypotheses": [
                    {"title": "hypothesis_1", "steps": [], "artifacts": []}
                ]
            }
        plan_json_path = Path(state["workspace_dir"]) / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state["workspace_dir"], plan_json_path, "plan", "plan_analysis")
        hypotheses = [
            h.get("title") for h in plan_json.get("hypotheses", []) if h.get("title")
        ]
        if not hypotheses:
            hypotheses = _extract_hypotheses(plan)
        return {"plan": plan, "plan_json": plan_json, "hypotheses": hypotheses}

    def generate_code(state: OrchestrationState) -> OrchestrationState:
        plan = state.get("plan", "")
        plan_json = state.get("plan_json", {})
        language = state.get("config", {}).get("report_language", "zh")
        code_dir = ensure_dir(Path(state["workspace_dir"]) / "code")

        steps: list[dict[str, Any]] = []
        hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
        for hypothesis in hypotheses:
            for idx, step in enumerate(hypothesis.get("steps", []) or []):
                steps.append(
                    {
                        "name": f"{hypothesis.get('title','hypothesis')}_{idx+1}",
                        "description": step,
                    }
                )
        if not steps:
            steps = [{"name": "analysis_step", "description": plan}]

        def _generate(step: dict[str, Any]) -> dict[str, Any]:
            prompt = get_prompt("codegen", language)
            messages = [
                {"role": "system", "content": get_system(language)},
                {
                    "role": "user",
                    "content": f"{prompt}\n\nPlan Step:\n{step['description']}",
                },
            ]
            code_json = llm.chat(messages, max_tokens=4096)
            payload = _safe_json_load(code_json)
            if isinstance(payload, dict) and payload.get("steps"):
                entry = payload["steps"][0]
            else:
                entry = {
                    "name": step["name"],
                    "filename": f"{step['name']}.py",
                    "code": "# TODO",
                }
            return entry

        recorded = []
        workers = max(1, int(config.get("codegen_concurrency", CODEGEN_CONCURRENCY)))
        if workers > 1 and len(steps) > 1:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for entry in executor.map(_generate, steps):
                    filename = entry.get("filename") or f"{entry.get('name','step')}.py"
                    path = code_dir / filename
                    write_text(path, entry.get("code") or "")
                    record_artifact(state["workspace_dir"], path, "code", "generate_code")
                    recorded.append({"name": entry.get("name", filename), "path": str(path)})
        else:
            for step in steps:
                entry = _generate(step)
                filename = entry.get("filename") or f"{entry.get('name','step')}.py"
                path = code_dir / filename
                write_text(path, entry.get("code") or "")
                record_artifact(state["workspace_dir"], path, "code", "generate_code")
                recorded.append({"name": entry.get("name", filename), "path": str(path)})

        write_json(code_dir / "steps.json", recorded)
        return {"code_steps": recorded}

    def execute_steps(state: OrchestrationState) -> OrchestrationState:
        results_dir = ensure_dir(Path(state["workspace_dir"]) / "result")
        retries = int(config.get("execution_max_retries", EXECUTION_MAX_RETRIES))
        steps = list(state.get("code_steps", []))

        def _run_step(step: dict[str, Any]) -> dict[str, Any]:
            path = Path(step["path"])
            code = path.read_text(encoding="utf-8") if path.exists() else ""
            output = ""
            for attempt in range(retries + 1):
                output = execute_code_safe(
                    code, state["workspace_dir"], CODE_EXECUTION_TIMEOUT
                )
                if "[Error]" not in output and "Traceback" not in output:
                    break
                fix_messages = [
                    {"role": "system", "content": get_system("en")},
                    {
                        "role": "user",
                        "content": (
                            f"{get_prompt('code_fix','en')}\n\nError:\n{output}\n\nCode:\n{code}"
                        ),
                    },
                ]
                code = llm.chat(fix_messages, max_tokens=2048)
                write_text(path, code)
            result_path = results_dir / f"{path.stem}_output.txt"
            write_text(result_path, output)
            record_artifact(state["workspace_dir"], result_path, "result", "execute_steps")
            return {
                "step": step.get("name"),
                "output": output,
                "path": str(result_path),
            }

        workers = max(1, int(config.get("execution_concurrency", EXECUTION_CONCURRENCY)))
        if workers > 1 and len(steps) > 1:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                exec_results = list(executor.map(_run_step, steps))
        else:
            exec_results = [_run_step(step) for step in steps]
        write_json(results_dir / "exec_results.json", exec_results)
        return {"exec_results": exec_results}

    def analyze_results(state: OrchestrationState) -> OrchestrationState:
        outputs = state.get("exec_results", [])
        summary = "\n".join([o.get("output", "") for o in outputs])
        visual_style = state.get("config", {}).get("visual_style", "academic")
        visual_interactive = state.get("config", {}).get("visual_interactive", False)
        language = state.get("config", {}).get("report_language", "zh")
        prompt = get_prompt("analysis", language)
        messages = [
            {"role": "system", "content": get_system(language)},
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\nVisual style: {visual_style}\n"
                    f"Interactive: {visual_interactive}\n\nOutputs:\n{summary}"
                ),
            },
        ]
        analysis = llm.chat(messages, max_tokens=4096)
        analysis_path = Path(state["workspace_dir"]) / "result" / "analysis_results.md"
        write_text(analysis_path, analysis)
        record_artifact(state["workspace_dir"], analysis_path, "result", "analyze_results")
        history = list(state.get("analysis_history", []))
        history.append(analysis)
        return {"analysis_results": analysis, "analysis_history": history}

    def refine_hypotheses(state: OrchestrationState) -> OrchestrationState:
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        prompt = get_prompt("hypothesis_refine", language)
        messages = [
            {"role": "system", "content": get_system(language)},
            {"role": "user", "content": f"{prompt}\n\nAnalysis:\n{analysis}"},
        ]
        raw = llm.chat(messages, max_tokens=1024)
        followups = _extract_hypotheses(raw)
        followup_path = Path(state["workspace_dir"]) / "plan" / "followup_hypotheses.md"
        write_text(followup_path, raw)
        record_artifact(state["workspace_dir"], followup_path, "plan", "refine_hypotheses")
        return {"followup_hypotheses": followups}

    def decide_recurse(state: OrchestrationState) -> OrchestrationState:
        max_depth = int(state.get("max_depth", 0))
        if max_depth == 0:
            return {"should_recurse": False, "continuation_required": True}
        depth = int(state.get("depth", 1))
        should_recurse = depth < max_depth
        return {"should_recurse": should_recurse}

    def advance_depth(state: OrchestrationState) -> OrchestrationState:
        depth = int(state.get("depth", 1))
        return {"depth": depth + 1}

    def report_outline(state: OrchestrationState) -> OrchestrationState:
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        prompt = get_prompt("report_outline", language)
        messages = [
            {"role": "system", "content": get_system(language)},
            {"role": "user", "content": f"{prompt}\n\nAnalysis:\n{analysis}"},
        ]
        outline = llm.chat(messages, max_tokens=2048)
        outline_path = Path(state["workspace_dir"]) / "report" / "report_outline.md"
        write_text(outline_path, outline)
        record_artifact(state["workspace_dir"], outline_path, "report", "report_outline")
        return {"report_outline": outline}

    def generate_report(state: OrchestrationState) -> OrchestrationState:
        outline = state.get("report_outline", "")
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        report_format = state.get("config", {}).get("report_format", "html")
        export_mode = state.get("config", {}).get("report_export_mode", "html_convert")
        prompt = get_prompt("report", language)
        previous_report = state.get("report", "")
        messages = [
            {"role": "system", "content": get_system(language)},
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\nLanguage: {language}\nFormat: {report_format}\n"
                    f"Export mode: {export_mode}\n"
                    f"Outline:\n{outline}\n\nAnalysis:\n{analysis}\n\n"
                    f"Previous report (if any):\n{previous_report}"
                ),
            },
        ]
        report = llm.chat(messages, max_tokens=4096)
        version = len(state.get("report_versions", [])) + 1
        report_path = export_report(
            report,
            output_dir=Path(state["workspace_dir"]) / "report",
            report_format=report_format,
            export_mode=export_mode,
            template=template_from_config(language),
            base_name=f"report_v{version}",
        )
        record_artifact(state["workspace_dir"], report_path, "report", "generate_report")
        versions = list(state.get("report_versions", []))
        versions.append(str(report_path))
        return {"report": report, "report_versions": versions}

    def finalize_run(state: OrchestrationState) -> OrchestrationState:
        summary = {
            "run_id": state.get("run_id"),
            "trace_id": state.get("trace_id"),
            "telemetry": state.get("telemetry", []),
            "reports": state.get("report_versions", []),
            "followup_hypotheses": state.get("followup_hypotheses", []),
            "continuation_required": state.get("continuation_required", False),
        }
        record_run_summary(state["workspace_dir"], summary)
        return {"run_summary": summary}

    graph.add_node("understand_files", _run_node("understand_files", understand_files, config))
    graph.add_node("data_quality", _run_node("data_quality", data_quality, config))
    graph.add_node("plan_analysis", _run_node("plan_analysis", plan_analysis, config))
    graph.add_node("generate_code", _run_node("generate_code", generate_code, config))
    graph.add_node("execute_steps", _run_node("execute_steps", execute_steps, config))
    graph.add_node("analyze_results", _run_node("analyze_results", analyze_results, config))
    graph.add_node("refine_hypotheses", _run_node("refine_hypotheses", refine_hypotheses, config))
    graph.add_node("decide_recurse", _run_node("decide_recurse", decide_recurse, config))
    graph.add_node("advance_depth", _run_node("advance_depth", advance_depth, config))
    graph.add_node("report_outline", _run_node("report_outline", report_outline, config))
    graph.add_node("generate_report", _run_node("generate_report", generate_report, config))
    graph.add_node("finalize_run", _run_node("finalize_run", finalize_run, config))

    graph.set_entry_point("understand_files")
    graph.add_edge("understand_files", "data_quality")
    graph.add_edge("data_quality", "plan_analysis")
    graph.add_edge("plan_analysis", "generate_code")
    graph.add_edge("generate_code", "execute_steps")
    graph.add_edge("execute_steps", "analyze_results")
    graph.add_edge("analyze_results", "refine_hypotheses")
    graph.add_edge("refine_hypotheses", "decide_recurse")
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
    graph.add_edge("generate_report", "finalize_run")
    graph.add_edge("finalize_run", END)

    return graph.compile()
