"""Graph 工具函数模块.

从原 graph.py 中提取的工具函数,用于支持工作流图的构建和执行.
"""

from .json_utils import (
    extract_json_candidates,
    safe_json_load,
    safe_json_any,
    load_json_if_exists,
)
from .config import load_analysis_runtime_config
from .fallback import (
    is_llm_unavailable_error,
    record_llm_degradation,
    has_llm_unavailable_event,
    strong_fallback_plan_ok,
    strong_fallback_report_ok,
    fallback_followup_hypotheses,
    fallback_report_outline,
    fallback_analysis_code,
)
from .plan import (
    parse_plan_markdown,
    extract_plan_table_hypotheses,
    extract_hypothesis_descriptions,
    extract_hypothesis_table_steps_artifacts,
    normalize_plan_json,
    render_plan_markdown_from_json,
    synthesize_plan_from_hypothesis_results,
)
from .hypothesis import (
    extract_hypothesis_id_from_label,
    active_hypothesis_ids_from_plan,
    filter_hypothesis_results_payload,
    hypothesis_title_only,
    extract_hypotheses,
    extract_hypothesis_ids_from_report,
    sync_hypothesis_alignment_artifacts,
)
from .validation import (
    infer_method_family,
    runtime_bound_validation_templates,
    canonical_hypothesis_identity,
    parse_result_hypothesis_identity,
    align_plan_json_to_runtime_hypotheses,
    default_validation_paths,
    merge_validation_paths,
)
from .pipeline import (
    variant_method_family,
    pick_path_c_variant,
    status_vote,
    run_path_c_adjudication,
    maybe_run_pipeline_variants,
)
from .audit import (
    telemetry_context,
    cleanup_dir_contents,
    rollback_plan_outputs,
    run_audit,
    build_evidence_trace,
    build_reason_code_summary,
    build_analysis_quality_score,
    quality_consistency_errors,
    build_completion_validation,
)

__all__ = [
    # json_utils
    "extract_json_candidates",
    "safe_json_any",
    "safe_json_load",
    "load_json_if_exists",
    # config
    "load_analysis_runtime_config",
    # fallback
    "is_llm_unavailable_error",
    "record_llm_degradation",
    "has_llm_unavailable_event",
    "strong_fallback_plan_ok",
    "strong_fallback_report_ok",
    "fallback_followup_hypotheses",
    "fallback_report_outline",
    "fallback_analysis_code",
    # plan
    "parse_plan_markdown",
    "extract_plan_table_hypotheses",
    "extract_hypothesis_descriptions",
    "extract_hypothesis_table_steps_artifacts",
    "normalize_plan_json",
    "render_plan_markdown_from_json",
    "synthesize_plan_from_hypothesis_results",
    # hypothesis
    "extract_hypothesis_id_from_label",
    "active_hypothesis_ids_from_plan",
    "filter_hypothesis_results_payload",
    "hypothesis_title_only",
    "extract_hypotheses",
    "extract_hypothesis_ids_from_report",
    "sync_hypothesis_alignment_artifacts",
    # validation
    "infer_method_family",
    "runtime_bound_validation_templates",
    "canonical_hypothesis_identity",
    "parse_result_hypothesis_identity",
    "align_plan_json_to_runtime_hypotheses",
    "default_validation_paths",
    "merge_validation_paths",
    # pipeline
    "variant_method_family",
    "pick_path_c_variant",
    "status_vote",
    "run_path_c_adjudication",
    "maybe_run_pipeline_variants",
    # audit
    "telemetry_context",
    "cleanup_dir_contents",
    "rollback_plan_outputs",
    "run_audit",
    "build_evidence_trace",
    "build_reason_code_summary",
    "build_analysis_quality_score",
    "quality_consistency_errors",
    "build_completion_validation",
]