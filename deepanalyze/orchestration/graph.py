from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
from langgraph.graph import END, StateGraph

from API.utils import collect_file_info
from API.config import (
    CODE_EXECUTION_TIMEOUT,
    EXECUTION_MAX_RETRIES,
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
    artifact_dir,
    copy_artifact,
)
from .llm import LLMClient
from .plan_store import PlanStore, ArtifactRegistry
from .prompts import get_prompt, get_system, render_role_prompt
from .agents import HypothesisPlanner
from .coordinator import CodeExecutionOrchestrator, ExecutionMonitor
from deepanalyze.visualization.writer import visualization_writer
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


def _artifact_context(registry: ArtifactRegistry, plan_id: str) -> str:
    entries = registry.list(plan_id)
    if not entries:
        return "Artifacts: none"
    lines = ["Artifacts:"]
    for entry in entries[-12:]:
        kind = entry.get("kind", "unknown")
        path = entry.get("path", "")
        status = entry.get("status", "")
        lines.append(f"- {kind}: {path} ({status})")
    return "\n".join(lines)


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
                state.get("workspace_dir", ""),
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
        workspace_dir = Path(state.get("workspace_dir", ""))
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
        workspace_dir = Path(state.get("workspace_dir", ""))
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
        return {"data_quality": results, "data_quality_path": str(quality_path)}

    def plan_analysis(state: OrchestrationState) -> OrchestrationState:
        summary = state.get("file_summary", "")
        language = state.get("config", {}).get("report_language", "zh")
        plan_store = PlanStore(Path(state.get("workspace_dir", "")))
        planner = HypothesisPlanner(llm, language)
        plan = planner.plan(summary, state.get("analysis_history", []))
        plan_path = Path(state.get("workspace_dir", "")) / "plan" / "analysis_plan.md"
        write_text(plan_path, plan)
        record_artifact(state.get("workspace_dir", ""), plan_path, "plan", "plan_analysis")

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
        plan_json_path = Path(state.get("workspace_dir", "")) / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state.get("workspace_dir", ""), plan_json_path, "plan", "plan_analysis")
        hypotheses = [
            h.get("title") for h in plan_json.get("hypotheses", []) if h.get("title")
        ]
        if not hypotheses:
            hypotheses = _extract_hypotheses(plan)
        cleaned_hypotheses = [str(item) for item in hypotheses if item]
        plan_id, _ = plan_store.save_plan(plan, plan_json, cleaned_hypotheses)
        artifact_registry = ArtifactRegistry(Path(state.get("workspace_dir", "")))
        artifact_plan_dir = artifact_dir(state.get("workspace_dir", ""), plan_id, "plan")
        artifact_plan_md = artifact_plan_dir / "analysis_plan.md"
        artifact_plan_json = artifact_plan_dir / "analysis_plan.json"
        artifact_registry.register(plan_id, "plan", artifact_plan_md, {"phase": "plan_analysis"})
        if artifact_plan_json.exists():
            artifact_registry.register(plan_id, "plan", artifact_plan_json, {"phase": "plan_analysis"})
        data_quality_path = state.get("data_quality_path")
        if data_quality_path:
            copied = copy_artifact(data_quality_path, artifact_dir(state.get("workspace_dir", ""), plan_id, "data"))
            artifact_registry.register(plan_id, "data", copied, {"phase": "data_quality"})
        return {"plan": plan, "plan_json": plan_json, "hypotheses": cleaned_hypotheses, "plan_id": plan_id}

    def parallel_generation(state: OrchestrationState) -> OrchestrationState:
        plan = state.get("plan", "")
        plan_json = state.get("plan_json", {})
        plan_id = state.get("plan_id", "")
        language = state.get("config", {}).get("report_language", "zh")
        retries = int(config.get("execution_max_retries", EXECUTION_MAX_RETRIES))
        workspace_dir = Path(state.get("workspace_dir", ""))
        artifact_registry = ArtifactRegistry(workspace_dir)

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
            artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
            messages = render_role_prompt(
                "codegen",
                language,
                prompt_key="codegen",
                plan=step["description"],
                plan_id=plan_id,
                artifact_context=artifact_context,
            )
            if not messages:
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

        orchestrator = CodeExecutionOrchestrator(llm, config, workspace_dir, plan_id)
        recorded = orchestrator.generate(steps, _generate)
        legacy_code_dir = ensure_dir(workspace_dir / "code")
        write_json(legacy_code_dir / "steps.json", recorded)
        record_artifact(workspace_dir, legacy_code_dir / "steps.json", "code", "parallel_generation")
        if plan_id:
            steps_path = artifact_dir(workspace_dir, plan_id, "code") / "steps.json"
            write_json(steps_path, recorded)
            artifact_registry.register(plan_id, "code", steps_path, {"phase": "parallel_generation"})

        monitor = ExecutionMonitor(workspace_dir, plan_id)
        exec_results = orchestrator.execute(recorded, CODE_EXECUTION_TIMEOUT, monitor, retries)
        legacy_results_dir = ensure_dir(workspace_dir / "result")
        write_json(legacy_results_dir / "exec_results.json", exec_results)
        record_artifact(workspace_dir, legacy_results_dir / "exec_results.json", "result", "parallel_generation")
        if plan_id:
            exec_path = artifact_dir(workspace_dir, plan_id, "result") / "exec_results.json"
            write_json(exec_path, exec_results)
            artifact_registry.register(plan_id, "result", exec_path, {"phase": "parallel_generation"})
        return {"code_steps": recorded, "exec_results": exec_results}

    def analyze_results(state: OrchestrationState) -> OrchestrationState:
        outputs = state.get("exec_results", [])
        summary = "\n".join([o.get("output", "") for o in outputs])
        visual_style = state.get("config", {}).get("visual_style", "academic")
        visual_interactive = state.get("config", {}).get("visual_interactive", False)
        language = state.get("config", {}).get("report_language", "zh")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("workspace_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        prompt = get_prompt("analysis", language)
        messages = render_role_prompt(
            "analysis",
            language,
            prompt_key="analysis",
            outputs=(
                f"Visual style: {visual_style}\nInteractive: {visual_interactive}\n\n{summary}"
            ),
            plan_id=plan_id,
            artifact_context=artifact_context,
        )
        if not messages:
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
        analysis_path = Path(state.get("workspace_dir", "")) / "result" / "analysis_results.md"
        write_text(analysis_path, analysis)
        record_artifact(state.get("workspace_dir", ""), analysis_path, "result", "analyze_results")
        if plan_id:
            artifact_registry = ArtifactRegistry(Path(state.get("workspace_dir", "")))
            copied = copy_artifact(analysis_path, artifact_dir(state.get("workspace_dir", ""), plan_id, "result"))
            artifact_registry.register(plan_id, "result", copied, {"phase": "analysis_results"})
        history = list(state.get("analysis_history", []))
        history.append(analysis)
        return {"analysis_results": analysis, "analysis_history": history}

    def generate_visualizations(state: OrchestrationState) -> OrchestrationState:
        plan_id = state.get("plan_id", "")
        if not plan_id:
            return {}
        data_quality = state.get("data_quality", {})
        datasets = data_quality.get("datasets", []) if isinstance(data_quality, dict) else []
        if not datasets:
            return {}
        missing_rate = datasets[0].get("missing_rate", {})
        if not missing_rate:
            return {}
        visual_style = state.get("config", {}).get("visual_style", "academic")
        workspace_dir = Path(state.get("workspace_dir", ""))
        artifact_registry = ArtifactRegistry(workspace_dir)

        import matplotlib.pyplot as plt

        columns = list(missing_rate.keys())
        rates = [missing_rate[col] for col in columns]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(columns, rates, color="#4C78A8")
        ax.set_title("Missing Rate by Column")
        ax.set_ylabel("Missing Rate")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        entries = visualization_writer(
            fig,
            workspace_dir=workspace_dir,
            plan_id=plan_id,
            style=visual_style,
            name="missing_rate",
            registry=artifact_registry,
            metadata={"source": "data_quality"},
        )
        plt.close(fig)
        return {"visualizations": entries}

    def refine_hypotheses(state: OrchestrationState) -> OrchestrationState:
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        prompt = get_prompt("hypothesis_refine", language)
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("workspace_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        messages = [
            {"role": "system", "content": get_system(language)},
            {
                "role": "user",
                "content": f"{prompt}\n\nAnalysis:\n{analysis}\n\nPlan ID: {plan_id}\n{artifact_context}",
            },
        ]
        raw = llm.chat(messages, max_tokens=1024)
        followups = _extract_hypotheses(raw)
        followup_path = Path(state.get("workspace_dir", "")) / "plan" / "followup_hypotheses.md"
        write_text(followup_path, raw)
        record_artifact(state.get("workspace_dir", ""), followup_path, "plan", "refine_hypotheses")
        return {"followup_hypotheses": followups}

    def decide_recurse(state: OrchestrationState) -> OrchestrationState:
        max_depth = int(state.get("max_depth", 0))
        depth = int(state.get("depth", 1))
        depth_decision = str(state.get("depth_decision", "")).strip().lower()
        depth_prompt = ""
        if max_depth == 0:
            if depth_decision == "continue":
                return {"should_recurse": True, "continuation_required": False, "depth_prompt": ""}
            if depth_decision == "stop":
                return {"should_recurse": False, "continuation_required": False, "depth_prompt": ""}
            depth_prompt = "初次分析已完成。\n回复 'continue' 以开始更深一层的分析，否则输入 'stop' 结束。"
            return {"should_recurse": False, "continuation_required": True, "depth_prompt": depth_prompt}
        should_recurse = depth < max_depth
        return {"should_recurse": should_recurse, "continuation_required": False, "depth_prompt": depth_prompt}

    def advance_depth(state: OrchestrationState) -> OrchestrationState:
        depth = int(state.get("depth", 1))
        return {"depth": depth + 1}

    def report_outline(state: OrchestrationState) -> OrchestrationState:
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("workspace_dir", "")))
        plan_store = PlanStore(Path(state.get("workspace_dir", "")))
        plan_payload = plan_store.load_plan(plan_id) if plan_id else {}
        plan_text = plan_payload.get("plan_text", "")
        plan_json = plan_payload.get("plan_json", {})
        plan_summary = plan_text or json.dumps(plan_json, ensure_ascii=False)
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        prompt = get_prompt("report_outline", language)
        messages = render_role_prompt(
            "report_outline",
            language,
            prompt_key="report_outline",
            analysis=f"{analysis}\n\nPlan Summary:\n{plan_summary}",
            plan_id=plan_id,
            artifact_context=artifact_context,
        )
        if not messages:
            messages = [
                {"role": "system", "content": get_system(language)},
                {"role": "user", "content": f"{prompt}\n\nAnalysis:\n{analysis}"},
            ]
        outline = llm.chat(messages, max_tokens=2048)
        outline_path = Path(state.get("workspace_dir", "")) / "report" / "report_outline.md"
        write_text(outline_path, outline)
        record_artifact(state.get("workspace_dir", ""), outline_path, "report", "report_outline")
        if plan_id:
            copied = copy_artifact(
                outline_path,
                artifact_dir(state.get("workspace_dir", ""), plan_id, "report"),
            )
            artifact_registry.register(plan_id, "report", copied, {"phase": "report_outline"})
        return {"report_outline": outline}

    def generate_report(state: OrchestrationState) -> OrchestrationState:
        outline = state.get("report_outline", "")
        analysis = state.get("analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        report_format = state.get("config", {}).get("report_format", "html")
        export_mode = state.get("config", {}).get("report_export_mode", "html_convert")
        prompt = get_prompt("report", language)
        previous_report = state.get("report", "")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("workspace_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        messages = render_role_prompt(
            "report",
            language,
            prompt_key="report",
            language=language,
            format=report_format,
            mode=export_mode,
            outline=outline,
            analysis=f"{analysis}\n\nPrevious report:\n{previous_report}",
            plan_id=plan_id,
            artifact_context=artifact_context,
        )
        if not messages:
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
            output_dir=Path(state.get("workspace_dir", "")) / "report",
            report_format=report_format,
            export_mode=export_mode,
            template=template_from_config(language),
            base_name=f"report_v{version}",
        )
        record_artifact(state.get("workspace_dir", ""), report_path, "report", "generate_report")
        versions = list(state.get("report_versions", []))
        versions.append(str(report_path))
        if plan_id:
            copied = copy_artifact(
                report_path,
                artifact_dir(state.get("workspace_dir", ""), plan_id, "report"),
            )
            artifact_registry.register(plan_id, "report", copied, {"phase": "generate_report"})
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
        record_run_summary(state.get("workspace_dir", ""), summary)
        return {"run_summary": summary}

    graph.add_node("understand_files", _run_node("understand_files", understand_files, config))
    graph.add_node("data_quality", _run_node("data_quality", data_quality, config))
    graph.add_node("plan_analysis", _run_node("plan_analysis", plan_analysis, config))
    graph.add_node("parallel_generation", _run_node("parallel_generation", parallel_generation, config))
    graph.add_node("analyze_results", _run_node("analyze_results", analyze_results, config))
    graph.add_node("generate_visualizations", _run_node("generate_visualizations", generate_visualizations, config))
    graph.add_node("refine_hypotheses", _run_node("refine_hypotheses", refine_hypotheses, config))
    graph.add_node("decide_recurse", _run_node("decide_recurse", decide_recurse, config))
    graph.add_node("advance_depth", _run_node("advance_depth", advance_depth, config))
    graph.add_node("report_outline", _run_node("report_outline", report_outline, config))
    graph.add_node("generate_report", _run_node("generate_report", generate_report, config))
    graph.add_node("finalize_run", _run_node("finalize_run", finalize_run, config))

    graph.set_entry_point("understand_files")
    graph.add_edge("understand_files", "data_quality")
    graph.add_edge("data_quality", "plan_analysis")
    graph.add_edge("plan_analysis", "parallel_generation")
    graph.add_edge("parallel_generation", "analyze_results")
    graph.add_edge("analyze_results", "generate_visualizations")
    graph.add_edge("generate_visualizations", "refine_hypotheses")
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
