from __future__ import annotations

from pathlib import Path
import uuid
import platform
import importlib.metadata
from typing import Any, cast

from API.config import WORKSPACE_BASE_DIR

from .graph import build_graph
from .llm import LLMClient
from .state import OrchestrationState
from .io_utils import init_workspace, write_run_metadata, hash_file
from API.config import REPRO_METADATA_ENABLED, TRACE_ENABLED


def run_orchestrated_analysis(
    session_id: str,
    config: dict[str, Any],
) -> OrchestrationState:
    workspace_dir = Path(WORKSPACE_BASE_DIR) / session_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    workspace_dirs = init_workspace(workspace_dir)

    max_depth = int(config.get("max_depth", 1))
    if max_depth > 3:
        max_depth = 3
    if max_depth < 0:
        max_depth = 0

    run_id = uuid.uuid4().hex[:12]
    trace_id = uuid.uuid4().hex[:12] if TRACE_ENABLED else ""

    if REPRO_METADATA_ENABLED:
        input_files = [str(p) for p in workspace_dir.iterdir() if p.is_file()]
        file_hashes = {p: hash_file(p) for p in input_files}
        metadata = {
            "run_id": run_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "config": config,
            "input_files": file_hashes,
            "python_version": platform.python_version(),
            "dependencies": {
                dist.metadata["Name"]: dist.version
                for dist in importlib.metadata.distributions()
            },
        }
        write_run_metadata(workspace_dir, metadata)

    initial_depth = 0 if max_depth == 0 else 1
    report_dir = Path(workspace_dirs["report"])
    existing_reports = sorted(report_dir.glob("report_v*.*"), key=lambda p: p.stat().st_mtime)
    latest_report = ""
    if existing_reports:
        try:
            latest_report = existing_reports[-1].read_text(encoding="utf-8")
        except Exception:
            latest_report = ""

    initial: OrchestrationState = {
        "session_id": session_id,
        "run_id": run_id,
        "trace_id": trace_id,
        "workspace_dir": str(workspace_dir),
        "workspace_dirs": {k: str(v) for k, v in workspace_dirs.items()},
        "depth": initial_depth,
        "max_depth": max_depth,
        "config": config,
        "report": latest_report,
        "report_versions": [str(p) for p in existing_reports],
        "plan_id": "",
        "depth_prompt": "",
        "depth_decision": str(config.get("depth_decision", "")).strip().lower(),
        "artifacts": [],
        "visualization_plan": [],
        "execution_retry_requested": False,
        "execution_retry_count": 0,
        "execution_retry_exhausted": False,
        "execution_errors": [],
    }
    llm = LLMClient()
    graph = build_graph(llm, config)
    result = graph.invoke(initial)
    return cast(OrchestrationState, result)
