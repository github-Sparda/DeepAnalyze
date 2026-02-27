from __future__ import annotations

from typing import Any, TypedDict


class OrchestrationState(TypedDict, total=False):
     session_id: str
     run_id: str
     trace_id: str
     data_sessions_active_dir: str
     data_sessions_active_dirs: dict[str, str]
     session_dir: str
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
     pipeline_variants: list[dict[str, Any]]
     pipeline_gate_failures: list[dict[str, Any]]
     pipeline_fallbacks: list[dict[str, Any]]
     hypothesis_multipath: dict[str, Any]
     path_adjudication: dict[str, Any]
     hypothesis_evidence_pack: dict[str, Any]
     hypothesis_gate_report: dict[str, Any]
     hypothesis_evidence_pack_validation: dict[str, Any]
     ml_repro_bundle: dict[str, Any]
     completion_validation: dict[str, Any]
     custom_line_records: list[dict[str, Any]]
     custom_line_summary: dict[str, Any]
     artifact_validation: dict[str, Any]
     code_repair_ran: bool
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
     iteration_count: int
     depth_prompt: str
     depth_decision: str
     should_recurse: bool
     continuation_required: bool
     recursion_context: dict[str, Any]
     iteration_lineage: list[dict[str, Any]]
     artifacts: list[dict[str, Any]]
     visualizations: list[dict[str, Any]]
     run_summary: dict[str, Any]
     errors: list[str]
     telemetry: list[dict[str, Any]]
     document_manifest: dict[str, Any]
     config: dict[str, Any]
