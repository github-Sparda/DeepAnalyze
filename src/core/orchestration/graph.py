from __future__ import annotations

import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from langgraph.graph import END, StateGraph

from src.api.config import (
    CODE_EXECUTION_TIMEOUT,
    EXECUTION_MAX_RETRIES,
    GRAPH_MONITORING,
    TRACE_ENABLED,
    DATA_QUALITY_ENABLED,
)
from src.api.utils import collect_file_info

from .io_utils import (
    ensure_dir,
    init_data_sessions_active,
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
from .recursion import DepthRecursionController
from .visualization_planner import VisualizationPlanner, load_dataframe
from src.core.visualization.writer import visualization_writer
from src.core.reporting.exporter import export_report
from src.core.reporting.templates import template_from_config
from .state import OrchestrationState
from .document_manager import DocumentManager


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


def _extract_visualization_goals(plan_json: dict[str, Any] | None) -> list[str]:
    goals: list[str] = []
    if not isinstance(plan_json, dict):
        return goals
    for hypothesis in plan_json.get("hypotheses", []):
        artifacts = hypothesis.get("artifacts", [])
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            for key in ("goal", "description", "type"):
                value = artifact.get(key)
                if isinstance(value, str):
                    goals.append(value)
    return goals


def _telemetry_context(
    state: OrchestrationState,
    registry: ArtifactRegistry | None = None,
    plan_id: str | None = None,
) -> str:
    telemetry = state.get("telemetry", [])
    lines: list[str] = []
    if telemetry:
        lines.append("Telemetry summary:")
        for entry in telemetry[-5:]:
            node = entry.get("node", "unknown")
            status = entry.get("status", "unknown")
            duration = entry.get("duration_sec", 0)
            lines.append(f"- {node}: {status} ({duration:.2f}s)")
    if registry and plan_id:
        entries = registry.list(plan_id)
        if entries:
            counts = Counter(entry.get("kind", "unknown") for entry in entries)
            summary = ", ".join(f"{kind}:{count}" for kind, count in counts.items())
            lines.append(f"Artifact counts: {summary}")
    retries = int(state.get("execution_retry_count", 0))
    requested = bool(state.get("execution_retry_requested"))
    exhausted = bool(state.get("execution_retry_exhausted"))
    lines.append(
        f"Execution retries: {retries} requested={requested} exhausted={exhausted}"
    )
    errors = state.get("execution_errors", []) or []
    if errors:
        lines.append("Execution errors:")
        for error in errors[-3:]:
            step = error.get("step", "unknown")
            output = error.get("output", "")
            lines.append(f"- {step}: {output}")
    if state.get("rollback_performed"):
        lines.append("Rollback performed for previous failures.")
    if not lines:
        return "Telemetry: none"
    return "\n".join(lines)


def _cleanup_dir_contents(directory: Path) -> None:
    if not directory.exists():
        return
    for child in directory.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except Exception:
            continue


def _rollback_plan_outputs(session_dir: Path, plan_id: str) -> None:
    if not plan_id:
        return
    _cleanup_dir_contents(session_dir / "result")
    _cleanup_dir_contents(session_dir / "artifacts" / plan_id / "result")
    _cleanup_dir_contents(session_dir / "generated")


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
                state.get("session_dir", ""),
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


def create_graph(llm: LLMClient, config: dict[str, Any]):
    graph = StateGraph(OrchestrationState)

    def understand_files(state: OrchestrationState) -> OrchestrationState:
        session_dir = Path(state.get("session_dir", ""))
        init_data_sessions_active(session_dir)
        file_info = collect_file_info(str(session_dir))
        language = state.get("config", {}).get("report_language", "zh")
        messages = render_role_prompt(
            "file_understanding",
            language,
            prompt_key="file_summary",
            file_info=file_info,
        )
        summary = llm.chat(messages, max_tokens=2048)
        summary_path = session_dir / "plan" / "file_summary.md"
        write_text(summary_path, summary)
        record_artifact(session_dir, summary_path, "plan", "understand_files")
        return {"file_summary": summary}

    def data_quality(state: OrchestrationState) -> OrchestrationState:
        if not config.get("data_quality_enabled", DATA_QUALITY_ENABLED):
            return {}
        session_dir = Path(state.get("session_dir", ""))
        results: dict[str, Any] = {"datasets": []}
        for path in session_dir.iterdir():
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
                        "path": str(path),
                        "rows": int(df.shape[0]),
                        "cols": int(df.shape[1]),
                        "missing_rate": missing,
                        "stats": stats,
                        "dtypes": df.dtypes.apply(str).to_dict(),
                    }
                )
            except Exception as exc:
                results["datasets"].append({"file": path.name, "error": str(exc)})
        quality_path = session_dir / "result" / "data_quality.json"
        write_json(quality_path, results)
        record_artifact(session_dir, quality_path, "result", "data_quality")
        return {"data_quality": results, "data_quality_path": str(quality_path)}

    def plan_visualizations(state: OrchestrationState) -> OrchestrationState:
        data_quality_payload = state.get("data_quality", {})
        datasets = data_quality_payload.get("datasets", [])
        if not datasets:
            return {"visualization_plan": []}
        session_dir = Path(state.get("session_dir", ""))
        planner = VisualizationPlanner(
            session_dir, max_items=int(config.get("visualization_max_items", 6))
        )
        plan_json = state.get("plan_json", {})
        goal_hints = _extract_visualization_goals(plan_json)
        goal_hint = (state.get("config", {}).get("analysis_goal", "") or "").strip()
        if not goal_hint:
            goal_hint = (state.get("config", {}).get("docs/analysis_goal", "") or "").strip()
        if goal_hint:
            goal_hints.append(goal_hint)
        instructions = planner.plan(datasets, goals=goal_hints)
        plan_path = session_dir / "plan" / "visualization_plan.json"
        write_json(plan_path, instructions)
        record_artifact(session_dir, plan_path, "plan", "plan_visualizations")
        return {"visualization_plan": instructions}

    def plan_analysis(state: OrchestrationState) -> OrchestrationState:
        summary = state.get("file_summary", "")
        language = state.get("config", {}).get("report_language", "zh")
        plan_store = PlanStore(Path(state.get("session_dir", "")))
        planner = HypothesisPlanner(llm, language)
        plan_id_hint = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_context = _artifact_context(
            artifact_registry, plan_id_hint
        ) if plan_id_hint else ""
        telemetry_context = _telemetry_context(
            state, artifact_registry, plan_id_hint
        )
        goal_hint = (state.get("config", {}).get("analysis_goal", "") or "").strip()
        if not goal_hint:
            goal_hint = (state.get("config", {}).get("docs/analysis_goal", "") or "").strip()
        plan = planner.plan(
            summary,
            state.get("docs_analysis_history", []),
            plan_id=plan_id_hint,
            artifact_context=artifact_context,
            telemetry_context=telemetry_context,
            goal_hint=goal_hint,
        )
        plan_path = Path(state.get("session_dir", "")) / "plan" / "analysis_plan.md"
        write_text(plan_path, plan)
        record_artifact(state.get("session_dir", ""), plan_path, "plan", "plan_analysis")

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
        plan_json_path = Path(state.get("session_dir", "")) / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state.get("session_dir", ""), plan_json_path, "plan", "plan_analysis")
        hypotheses = [
            h.get("title") for h in plan_json.get("hypotheses", []) if h.get("title")
        ]
        if not hypotheses:
            hypotheses = _extract_hypotheses(plan)
        cleaned_hypotheses = [str(item) for item in hypotheses if item]
        plan_id, _ = plan_store.save_plan(plan, plan_json, cleaned_hypotheses)
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_plan_dir = artifact_dir(state.get("session_dir", ""), plan_id, "plan")
        artifact_plan_md = artifact_plan_dir / "analysis_plan.md"
        artifact_plan_json = artifact_plan_dir / "analysis_plan.json"
        artifact_registry.register(plan_id, "plan", artifact_plan_md, {"phase": "plan_analysis"})
        if artifact_plan_json.exists():
            artifact_registry.register(plan_id, "plan", artifact_plan_json, {"phase": "plan_analysis"})
        data_quality_path = state.get("data_quality_path")
        if data_quality_path:
            copied = copy_artifact(data_quality_path, artifact_dir(state.get("session_dir", ""), plan_id, "data"))
            artifact_registry.register(plan_id, "data", copied, {"phase": "data_quality"})
        viz_plan_path = Path(state.get("session_dir", "")) / "plan" / "visualization_plan.json"
        if viz_plan_path.exists():
            viz_copied = copy_artifact(viz_plan_path, artifact_dir(state.get("session_dir", ""), plan_id, "plan"))
            artifact_registry.register(plan_id, "plan", viz_copied, {"phase": "visualization_plan"})
        return {"plan": plan, "plan_json": plan_json, "hypotheses": cleaned_hypotheses, "plan_id": plan_id}

    def parallel_generation(state: OrchestrationState) -> OrchestrationState:
        plan = state.get("plan", "")
        plan_json = state.get("plan_json", {})
        plan_id = state.get("plan_id", "")
        language = state.get("config", {}).get("report_language", "zh")
        retries = int(config.get("execution_max_retries", EXECUTION_MAX_RETRIES))
        session_dir = Path(state.get("session_dir", ""))
        artifact_registry = ArtifactRegistry(session_dir)
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""

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
            messages = render_role_prompt(
                "codegen",
                language,
                prompt_key="codegen",
                plan=step["description"],
                plan_id=plan_id,
                artifact_context=artifact_context,
                telemetry_context=telemetry_context,
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

        orchestrator = CodeExecutionOrchestrator(llm, config, session_dir, plan_id)
        recorded = orchestrator.generate(steps, _generate)
        legacy_code_dir = ensure_dir(session_dir / "code")
        write_json(legacy_code_dir / "steps.json", recorded)
        record_artifact(session_dir, legacy_code_dir / "steps.json", "code", "parallel_generation")
        if plan_id:
            steps_path = artifact_dir(session_dir, plan_id, "code") / "steps.json"
            write_json(steps_path, recorded)
            artifact_registry.register(plan_id, "code", steps_path, {"phase": "parallel_generation"})

        monitor = ExecutionMonitor(session_dir, plan_id)
        exec_results = orchestrator.execute(
            recorded,
            int(config.get("code_execution_timeout", CODE_EXECUTION_TIMEOUT)),
            monitor,
            retries,
        )
        execution_entries = list(monitor.entries)
        legacy_results_dir = ensure_dir(session_dir / "result")
        write_json(legacy_results_dir / "exec_results.json", exec_results)
        record_artifact(session_dir, legacy_results_dir / "exec_results.json", "result", "parallel_generation")
        if plan_id:
            exec_path = artifact_dir(session_dir, plan_id, "result") / "exec_results.json"
            write_json(exec_path, exec_results)
            artifact_registry.register(plan_id, "result", exec_path, {"phase": "parallel_generation"})
        return {
            "code_steps": recorded,
            "exec_results": exec_results,
            "execution_entries": execution_entries,
        }

    def execution_guard(state: OrchestrationState) -> OrchestrationState:
        exec_results = state.get("exec_results", [])
        retry_count = int(state.get("execution_retry_count", 0))
        failures: list[dict[str, Any]] = []
        session_dir = Path(state.get("session_dir", ""))
        plan_id = state.get("plan_id", "")
        for result in exec_results:
            statuses = result.get("statuses", [])
            if statuses and statuses[-1] == "error":
                failures.append(
                    {
                        "step": result.get("step"),
                        "output": result.get("output"),
                        "statuses": statuses,
                    }
                )
        max_retries = int(config.get("execution_failure_max_retries", 1))
        next_retry = retry_count
        requested = False
        exhausted = False
        if failures:
            next_retry += 1
            requested = next_retry <= max_retries
            exhausted = next_retry > max_retries
            if requested:
                _rollback_plan_outputs(session_dir, plan_id)
        return {
            "execution_retry_requested": requested,
            "execution_retry_count": next_retry,
            "execution_retry_exhausted": exhausted,
            "execution_errors": failures,
            "rollback_performed": requested,
        }

    def analyze_results(state: OrchestrationState) -> OrchestrationState:
        outputs = state.get("exec_results", [])
        summary = "\n".join([o.get("output", "") for o in outputs])
        visual_style = state.get("config", {}).get("visual_style", "academic")
        visual_interactive = state.get("config", {}).get("visual_interactive", False)
        language = state.get("config", {}).get("report_language", "zh")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        prompt = get_prompt("analysis", language)
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        messages = render_role_prompt(
            "analysis",
            language,
            prompt_key="analysis",
            outputs=(
                f"Visual style: {visual_style}\nInteractive: {visual_interactive}\n\n{summary}"
            ),
            plan_id=plan_id,
            artifact_context=artifact_context,
            telemetry_context=telemetry_context,
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
        analysis_text = llm.chat(messages, max_tokens=4096)
        analysis_path = Path(state.get("session_dir", "")) / "result" / "analysis_results.md"
        write_text(analysis_path, analysis_text)
        record_artifact(state.get("session_dir", ""), analysis_path, "result", "analyze_results")
        if plan_id:
            copied = copy_artifact(analysis_path, artifact_dir(state.get("session_dir", ""), plan_id, "result"))
            artifact_registry.register(plan_id, "result", copied, {"phase": "analysis_results"})
        history = list(state.get("docs_analysis_history", []))
        history.append(analysis_text)
        return {"docs_analysis_results": analysis_text, "docs_analysis_history": history}

    def generate_visualizations(state: OrchestrationState) -> OrchestrationState:
        plan_id = state.get("plan_id", "")
        instructions = state.get("visualization_plan", []) or []
        if not (plan_id and instructions):
            return {}
        visual_style = state.get("config", {}).get("visual_style", "academic")
        session_dir = Path(state.get("session_dir", ""))
        artifact_registry = ArtifactRegistry(session_dir)
        rendered: list[dict[str, Any]] = []

        def _build_figure(instruction: dict[str, Any]) -> Any:
            dataset_path = instruction.get("dataset_path")
            if not dataset_path:
                return None
            df = load_dataframe(Path(dataset_path))
            if df is None or df.empty:
                return None
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 4))
            viz_type = instruction.get("type", "distribution")
            columns = instruction.get("columns") or []
            if viz_type == "distribution" and columns:
                column = columns[0]
                ax.hist(df[column].dropna(), bins=24, color="#4C78A8")
                ax.set_title(f"Distribution of {column}")
            elif viz_type == "correlation" and columns:
                subset = df[columns].select_dtypes(include="number")
                corr = subset.corr()
                im = ax.imshow(corr, cmap="RdYlBu", vmin=-1, vmax=1)
                fig.colorbar(im, ax=ax)
                ax.set_xticks(range(len(corr.columns)))
                ax.set_xticklabels(corr.columns, rotation=45, ha="right")
                ax.set_yticks(range(len(corr.columns)))
                ax.set_yticklabels(corr.columns)
                ax.set_title("Correlation matrix")
            elif viz_type == "trend" and len(columns) >= 2:
                x_col, y_col = columns[:2]
                ax.plot(df[x_col], df[y_col], marker="o")
                ax.set_title(f"{y_col} over {x_col}")
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
            elif viz_type == "comparison" and len(columns) >= 2:
                cat, num = columns[:2]
                grouped = (
                    df.groupby(cat)[num]
                    .mean()
                    .sort_values(ascending=False)
                    .head(10)
                )
                grouped.plot(kind="bar", ax=ax, color="#4C78A8")
                ax.set_title(f"{num} by {cat}")
                ax.set_xlabel(cat)
                ax.set_ylabel(num)
            elif viz_type == "table" and columns:
                table_df = df[columns].head(5)
                ax.axis("off")
                table = ax.table(
                    cellText=table_df.values,
                    colLabels=table_df.columns,
                    loc="center",
                )
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                ax.set_title("Sample rows")
            else:
                ax.text(0.5, 0.5, "Visualization not available", ha="center", va="center")
                ax.axis("off")
            fig.tight_layout()
            return fig

        for idx, instruction in enumerate(instructions):
            fig = _build_figure(instruction)
            if fig is None:
                continue
            name = instruction.get("name") or f"{instruction.get('type', 'visual')}_{idx+1}"
            entries = visualization_writer(
                fig,
                session_dir=session_dir,
                plan_id=plan_id,
                style=visual_style,
                name=name,
                registry=artifact_registry,
                metadata=instruction,
            )
            rendered.extend(entries)
            import matplotlib.pyplot as plt

            plt.close(fig)
        return {"visualizations": rendered}

    def refine_hypotheses(state: OrchestrationState) -> OrchestrationState:
        analysis_text = state.get("docs_analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        prompt = get_prompt("hypothesis_refine", language)
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        messages = [
            {"role": "system", "content": get_system(language)},
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\nAnalysis:\n{analysis_text}\n\nPlan ID: {plan_id}\n"
                    f"{artifact_context}\nTelemetry:\n{telemetry_context}"
                ),
            },
        ]
        raw = llm.chat(messages, max_tokens=1024)
        followups = _extract_hypotheses(raw)
        followup_path = Path(state.get("session_dir", "")) / "plan" / "followup_hypotheses.md"
        write_text(followup_path, raw)
        record_artifact(state.get("session_dir", ""), followup_path, "plan", "refine_hypotheses")
        return {"followup_hypotheses": followups}

    def decide_recurse(state: OrchestrationState) -> OrchestrationState:
        max_depth = int(state.get("max_depth", 0))
        depth = int(state.get("depth", 1))
        depth_decision = str(state.get("depth_decision", "")).strip().lower()
        controller = DepthRecursionController(
            max_depth,
            retry_limit=int(config.get("execution_failure_max_retries", 1)),
        )
        return controller.evaluate(
            depth,
            state.get("followup_hypotheses", []),
            state.get("execution_retry_requested", False),
            state.get("execution_retry_exhausted", False),
            depth_decision,
            int(state.get("execution_retry_count", 0)),
        )

    def advance_depth(state: OrchestrationState) -> OrchestrationState:
        depth = int(state.get("depth", 1))
        return {"depth": depth + 1}

    def report_outline(state: OrchestrationState) -> OrchestrationState:
        analysis_text = state.get("docs_analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        plan_store = PlanStore(Path(state.get("session_dir", "")))
        plan_payload = plan_store.load_plan(plan_id) if plan_id else {}
        plan_text = plan_payload.get("plan_text", "")
        plan_json = plan_payload.get("plan_json", {})
        plan_summary = plan_text or json.dumps(plan_json, ensure_ascii=False)
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        prompt = get_prompt("report_outline", language)
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        messages = render_role_prompt(
            "report_outline",
            language,
            prompt_key="report_outline",
            analysis=f"{analysis_text}\n\nPlan Summary:\n{plan_summary}",
            plan_id=plan_id,
            artifact_context=artifact_context,
            telemetry_context=telemetry_context,
        )
        if not messages:
            messages = [
                {"role": "system", "content": get_system(language)},
                {"role": "user", "content": f"{prompt}\n\nAnalysis:\n{analysis_text}"},
            ]
        outline = llm.chat(messages, max_tokens=2048)
        outline_path = Path(state.get("session_dir", "")) / "report" / "report_outline.md"
        write_text(outline_path, outline)
        record_artifact(state.get("session_dir", ""), outline_path, "report", "report_outline")
        if plan_id:
            copied = copy_artifact(
                outline_path,
                artifact_dir(state.get("session_dir", ""), plan_id, "report"),
            )
            artifact_registry.register(plan_id, "report", copied, {"phase": "report_outline"})
        return {"report_outline": outline}

    def generate_report(state: OrchestrationState) -> OrchestrationState:
        outline = state.get("report_outline", "")
        analysis_text = state.get("docs_analysis_results", "")
        language = state.get("config", {}).get("report_language", "zh")
        report_format = state.get("config", {}).get("report_format", "html")
        export_mode = state.get("config", {}).get("report_export_mode", "html_convert")
        prompt = get_prompt("report", language)
        previous_report = state.get("report", "")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        messages = render_role_prompt(
            "report",
            language,
            prompt_key="report",
            language=language,
            format=report_format,
            mode=export_mode,
            outline=outline,
            analysis=f"{analysis_text}\n\nPrevious report:\n{previous_report}",
            plan_id=plan_id,
            artifact_context=artifact_context,
            telemetry_context=telemetry_context,
        )
        if not messages:
            messages = [
                {"role": "system", "content": get_system(language)},
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nLanguage: {language}\nFormat: {report_format}\n"
                        f"Export mode: {export_mode}\n"
                        f"Outline:\n{outline}\n\nAnalysis:\n{analysis_text}\n\n"
                        f"Previous report (if any):\n{previous_report}"
                    ),
                },
            ]
        report = llm.chat(messages, max_tokens=4096)
        version = len(state.get("report_versions", [])) + 1
        report_path = export_report(
            report,
            output_dir=Path(state.get("session_dir", "")) / "report",
            report_format=report_format,
            export_mode=export_mode,
            template=template_from_config(language),
            base_name=f"report_v{version}",
        )
        record_artifact(state.get("session_dir", ""), report_path, "report", "generate_report")
        versions = list(state.get("report_versions", []))
        versions.append(str(report_path))
        if plan_id:
            copied = copy_artifact(
                report_path,
                artifact_dir(state.get("session_dir", ""), plan_id, "report"),
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
        session_dir = Path(state.get("session_dir", ""))
        doc_manager = DocumentManager(session_dir)
        document_manifest = doc_manager.manifest()
        record_artifact(
            session_dir,
            doc_manager.manifest_path,
            "meta",
            "document_manifest",
        )
        summary["documents"] = document_manifest
        record_run_summary(session_dir, summary)
        return {"run_summary": summary, "document_manifest": document_manifest}

    graph.add_node("understand_files", _run_node("understand_files", understand_files, config))
    graph.add_node("data_quality", _run_node("data_quality", data_quality, config))
    graph.add_node("plan_visualizations", _run_node("plan_visualizations", plan_visualizations, config))
    graph.add_node("plan_analysis", _run_node("plan_analysis", plan_analysis, config))
    graph.add_node("parallel_generation", _run_node("parallel_generation", parallel_generation, config))
    graph.add_node("execution_guard", _run_node("execution_guard", execution_guard, config))
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
    graph.add_edge("data_quality", "plan_visualizations")
    graph.add_edge("plan_visualizations", "plan_analysis")
    graph.add_edge("plan_analysis", "parallel_generation")
    graph.add_edge("parallel_generation", "execution_guard")
    graph.add_conditional_edges(
        "execution_guard",
        lambda s: "retry" if s.get("execution_retry_requested") else "continue",
        {"retry": "plan_analysis", "continue": "analyze_results"},
    )
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


__all__ = ["create_graph"]
