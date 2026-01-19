from __future__ import annotations

from pathlib import Path
from typing import Any

from API.config import WORKSPACE_BASE_DIR

from .graph import build_graph
from .llm import LLMClient
from .state import OrchestrationState


def run_orchestrated_analysis(
    session_id: str,
    config: dict[str, Any],
) -> OrchestrationState:
    workspace_dir = Path(WORKSPACE_BASE_DIR) / session_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    max_depth = int(config.get("max_depth", 1))
    if max_depth > 3:
        max_depth = 3
    if max_depth < 1:
        max_depth = 1

    initial: OrchestrationState = {
        "session_id": session_id,
        "workspace_dir": str(workspace_dir),
        "depth": 1,
        "max_depth": max_depth,
        "config": config,
    }

    llm = LLMClient()
    graph = build_graph(llm, config)
    return graph.invoke(initial)
