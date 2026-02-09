from __future__ import annotations

import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from langgraph.graph import END, StateGraph

from .io_utils import (
    ensure_dir,
    init_data_dir,
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
from visualization.writer import visualization_writer
from reporting.exporter import export_report
from reporting.templates import template_from_config
from .state import OrchestrationState
from .document_manager import DocumentManager

# Configuration constants (these should be imported from config)
CODE_EXECUTION_TIMEOUT = 30
EXECUTION_MAX_RETRIES = 2
GRAPH_MONITORING = True
TRACE_ENABLED = True
DATA_QUALITY_ENABLED = True

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
    
    # Define all the node functions here
    # This is a simplified version - the full implementation would include all 12+ nodes
    
    def understand_files(state: OrchestrationState) -> OrchestrationState:
        session_dir = Path(state.get("session_dir", ""))
        init_data_dir(session_dir)
        file_info = "Mock file information collected for demonstration"
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
        # Mock data quality analysis
        results["datasets"].append({
            "file": "mock_data.csv",
            "rows": 1000,
            "cols": 10,
            "missing_rate": {"col1": 0.01, "col2": 0.05},
            "dtypes": {"col1": "int64", "col2": "float64"}
        })
        quality_path = session_dir / "result" / "data_quality.json"
        write_json(quality_path, results)
        record_artifact(session_dir, quality_path, "result", "data_quality")
        return {"data_quality": results, "data_quality_path": str(quality_path)}
    
    def plan_analysis(state: OrchestrationState) -> OrchestrationState:
        summary = state.get("file_summary", "")
        language = state.get("config", {}).get("report_language", "zh")
        plan_store = PlanStore(Path(state.get("session_dir", "")))
        planner = HypothesisPlanner(llm, language)
        plan_id_hint = state.get("plan_id", "")
        
        # Simplified planning - in full implementation this would be more sophisticated
        plan = "# Analysis Plan\n\n1. Data exploration\n2. Statistical analysis\n3. Visualization\n4. Reporting"
        plan_json = {
            "hypotheses": [
                {
                    "title": "Data Distribution Analysis",
                    "steps": ["Explore data distributions", "Identify outliers"],
                    "artifacts": ["distribution_plots", "summary_statistics"]
                }
            ]
        }
        
        plan_path = Path(state.get("session_dir", "")) / "plan" / "analysis_plan.md"
        write_text(plan_path, plan)
        record_artifact(state.get("session_dir", ""), plan_path, "plan", "plan_analysis")
        
        plan_json_path = Path(state.get("session_dir", "")) / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state.get("session_dir", ""), plan_json_path, "plan", "plan_analysis")
        
        hypotheses = ["Data Distribution Analysis"]
        plan_id, _ = plan_store.save_plan(plan, plan_json, hypotheses)
        return {"plan": plan, "plan_json": plan_json, "hypotheses": hypotheses, "plan_id": plan_id}
    
    # Add nodes to graph
    graph.add_node("understand_files", _run_node("understand_files", understand_files, config))
    graph.add_node("data_quality", _run_node("data_quality", data_quality, config))
    graph.add_node("plan_analysis", _run_node("plan_analysis", plan_analysis, config))
    
    # Set up edges
    graph.set_entry_point("understand_files")
    graph.add_edge("understand_files", "data_quality")
    graph.add_edge("data_quality", "plan_analysis")
    graph.add_edge("plan_analysis", END)
    
    return graph.compile()

# 导出主要函数
__all__ = ['create_graph']