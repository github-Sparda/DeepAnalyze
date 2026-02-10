from __future__ import annotations

from pathlib import Path
import uuid
import platform
import importlib.metadata
from typing import Any, cast

from src.api.config import WORKSPACE_BASE_DIR

from .graph import create_graph
from .llm import LLMClient
from .state import OrchestrationState
from .io_utils import init_data_sessions_active, write_run_metadata, hash_file
from src.api.config import REPRO_METADATA_ENABLED, TRACE_ENABLED


def run_orchestrated_docs_analysis(
    session_id: str,
    config: dict[str, Any],
) -> OrchestrationState:
    workspace_base_dir = Path(config.get("workspace_base_dir", WORKSPACE_BASE_DIR))
    data_sessions_active_dir = workspace_base_dir / session_id
    data_sessions_active_dir.mkdir(parents=True, exist_ok=True)
    data_sessions_active_dirs = init_data_sessions_active(data_sessions_active_dir)

    max_depth = int(config.get("max_depth", 1))
    if max_depth > 3:
        max_depth = 3
    if max_depth < 0:
        max_depth = 0

    run_id = uuid.uuid4().hex[:12]
    trace_id = uuid.uuid4().hex[:12] if TRACE_ENABLED else ""

    if REPRO_METADATA_ENABLED:
        input_files = [str(p) for p in data_sessions_active_dir.iterdir() if p.is_file()]
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
        write_run_metadata(data_sessions_active_dir, metadata)

    initial_depth = 0 if max_depth == 0 else 1
    report_dir = Path(data_sessions_active_dirs["report"])
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
        "data_sessions_active_dir": str(data_sessions_active_dir),
        "session_dir": str(data_sessions_active_dir),
        "data_sessions_active_dirs": {k: str(v) for k, v in data_sessions_active_dirs.items()},
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
    graph = create_graph(llm, config)
    result = graph.invoke(initial)
    return cast(OrchestrationState, result)
