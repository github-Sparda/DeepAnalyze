from __future__ import annotations

from typing import Any, TypedDict


class OrchestrationState(TypedDict, total=False):
    session_id: str
    workspace_dir: str
    input_files: list[str]
    file_summary: str
    plan: str
    hypotheses: list[str]
    code_steps: list[dict[str, Any]]
    exec_results: list[dict[str, Any]]
    analysis_results: str
    report_outline: str
    report: str
    depth: int
    max_depth: int
    should_recurse: bool
    errors: list[str]
    config: dict[str, Any]
