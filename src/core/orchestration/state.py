from __future__ import annotations

from typing import Any, TypedDict


class OrchestrationState(TypedDict, total=False):
     session_id: str
     run_id: str
     trace_id: str
     data_sessions_active_dir: str
     data_sessions_active_dirs: dict[str, str]
     input_files: list[str]
     file_summary: str
     plan: str
     plan_json: dict[str, Any]
     hypotheses: list[str]
     followup_hypotheses: list[str]
     code_steps: list[dict[str, Any]]
     exec_results: list[dict[str, Any]]
     docs_analysis_results: str
     docs_analysis_history: list[str]
     data_quality: dict[str, Any]
     data_quality_path: str
     visualization_plan: list[dict[str, Any]]
     execution_entries: list[dict[str, Any]]
     execution_retry_requested: bool
     execution_retry_count: int
     execution_retry_exhausted: bool
     execution_errors: list[dict[str, Any]]
     report_outline: str
     report: str
     report_versions: list[str]
     plan_id: str
     depth: int
     max_depth: int
     depth_prompt: str
     depth_decision: str
     should_recurse: bool
     continuation_required: bool
     artifacts: list[dict[str, Any]]
     visualizations: list[dict[str, Any]]
     run_summary: dict[str, Any]
     errors: list[str]
     telemetry: list[dict[str, Any]]
     document_manifest: dict[str, Any]
     config: dict[str, Any]
