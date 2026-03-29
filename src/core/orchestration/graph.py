from __future__ import annotations

import json
import re
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
    ANALYSIS_USE_LLM,
    REPORT_USE_LLM,
    MAX_ITERATIONS,
    CUSTOM_LINE_SUMMARY_DAYS,
    CUSTOM_LINE_PROMO_MIN_RUNS,
    CUSTOM_LINE_PROMO_MIN_SUCCESS,
    ROLE_GUARD_ENABLED,
    ARTIFACT_COPY_ENABLED,
    ARTIFACT_MIRROR_ENABLED,
    CUSTOM_LINE_COOLDOWN_SEC,
    PATHC_CONFLICT_THRESHOLD,
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
    record_role_output,
    artifact_dir,
    copy_artifact,
    artifact_link,
)
from .llm import LLMClient
from .plan_store import PlanStore, ArtifactRegistry
from .prompts import get_prompt, get_system, render_role_prompt
from .agents import HypothesisPlanner
from .agents import CodeGenerator
from .coordinator import CodeExecutionOrchestrator, ExecutionMonitor
from .recursion import DepthRecursionController
from .visualization_planner import VisualizationPlanner, load_dataframe
from src.core.visualization.writer import visualization_writer
from src.core.agents.registry import role_id_for_node
from src.core.reporting.exporter import export_report
from src.core.reporting.templates import template_from_config
from src.core.reporting.assembler import (
    ReportAssembler,
    analysis_payload_to_markdown,
    normalize_analysis_payload,
    normalize_report_payload,
    parse_structured_payload,
)
from src.core.analytics.toolkit.runner import run_pipeline as run_analysis_toolkit, run_step
from src.core.analytics.toolkit.selector import select_pipeline_variants
from src.core.analytics.toolkit.custom_lines import (
    register_line,
    record_usage,
    maybe_summarize,
)
from src.core.analytics.toolkit.cooldown import record_failure, in_cooldown
from src.core.analytics.resources import (
    build_hypothesis_evidence_pack,
    build_hypothesis_gate_report,
    default_hypothesis_profile_registry,
    infer_hypothesis_profile_key,
    load_feature_dictionary,
    load_hypothesis_profile_registry,
    load_method_dictionary,
    load_metric_dictionary,
    resolve_hypothesis_profile,
    validate_hypothesis_evidence_pack,
)
from .state import OrchestrationState
from .closure import (
    build_phase_blockers,
    closure_completion_summary,
    evaluate_phase_closure,
    load_phase_closure_map,
    persist_phase_closure,
)
from .supervisor import PhaseSupervisor, SupervisorContext
from src.api.config import (
    SUPERVISOR_ENABLED,
    SUPERVISOR_WAIT_STRATEGY,
    SUPERVISOR_POLL_INTERVAL,
    SUPERVISOR_MAX_WAIT,
    SUPERVISOR_MAX_RETRIES,
    SUPERVISOR_SEMANTIC_CHECK,
)
from .depth_research import (
    build_depth_delta,
    build_research_digest,
    render_research_digest_markdown,
    select_depth_focus,
)
from .document_manager import DocumentManager
from .hypothesis_engine import (
    _build_auto_analysis_payload,
    _build_coverage_report,
    _build_final_hypothesis_matrix,
    _build_hypothesis_contrast,
    _build_hypothesis_evidence,
    _build_hypothesis_matrix,
    _build_hypothesis_validation_contract,
    _build_visual_binding,
    _evaluate_hypothesis_validation_paths,
    _hypothesis_summary_md,
    _llm_analysis_has_metric_grounding,
    _load_structured_evidence,
    _run_deterministic_hypotheses,
)

# 导入新的 graph_utils 模块
from .graph_utils import (
    extract_json_candidates,
    safe_json_any,
    safe_json_load,
    load_json_if_exists,
    load_analysis_runtime_config,
    is_llm_unavailable_error,
    record_llm_degradation,
    has_llm_unavailable_event,
    strong_fallback_plan_ok,
    strong_fallback_report_ok,
    fallback_followup_hypotheses,
    fallback_report_outline,
    fallback_analysis_code,
)

# 为了保持向后兼容，保留原有的函数别名
_extract_json_candidates = extract_json_candidates
_safe_json_any = safe_json_any
_safe_json_load = safe_json_load
_load_json_if_exists = load_json_if_exists
_load_analysis_runtime_config = load_analysis_runtime_config
_is_llm_unavailable_error = is_llm_unavailable_error
_record_llm_degradation = record_llm_degradation
_has_llm_unavailable_event = has_llm_unavailable_event
_strong_fallback_plan_ok = strong_fallback_plan_ok
_strong_fallback_report_ok = strong_fallback_report_ok
_fallback_followup_hypotheses = fallback_followup_hypotheses
_fallback_report_outline = fallback_report_outline
_fallback_analysis_code = fallback_analysis_code


def _build_file_summary_fallback(file_info: str) -> str:
    raw = str(file_info or "").strip()
    if not raw:
        return "文件摘要（降级生成）：当前工作目录未检测到可读文件。"
    items: list[dict[str, Any]] = []
    for block in re.findall(r"File\s+\d+:\s*(\{[\s\S]*?\})", raw):
        try:
            payload = json.loads(block)
        except Exception:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    if not items:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        preview = "；".join(lines[:4])
        return f"文件摘要（降级生成）：已发现输入文件信息。原始摘要片段：{preview}"
    lines = ["文件摘要（降级生成）："]
    lines.append(f"- 检测到文件数量：{len(items)}")
    for idx, item in enumerate(items, 1):
        name = str(item.get("name", "")).strip() or f"file_{idx}"
        size = str(item.get("size", "")).strip() or "unknown"
        lines.append(f"- 文件 {idx}：{name}（大小：{size}）")
    lines.append("- 说明：当前摘要由系统在 LLM 超时/不可用时自动生成，用于保障流程连续执行。")
    return "\n".join(lines)


def _extract_hypothesis_id_from_label(raw: str) -> str:
    text = str(raw or "").strip().upper()
    match = re.search(r"\b(H\d+)\b", text)
    return match.group(1) if match else ""


def _active_hypothesis_ids_from_plan(plan_json: dict[str, Any]) -> list[str]:
    rows = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        hid = str(row.get("id", "")).strip().upper()
        if re.fullmatch(r"H\d+", hid):
            ids.append(hid)
    return ids


def _filter_hypothesis_results_payload(payload: dict[str, Any], active_ids: set[str]) -> dict[str, Any]:
    rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    filtered: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        hid = _extract_hypothesis_id_from_label(row.get("hypothesis", ""))
        if hid and hid in active_ids:
            filtered.append(row)
    return {"hypotheses": filtered}


def _build_path_execution_status(
    multipath_payload: dict[str, Any],
) -> dict[str, Any]:
    rows = multipath_payload.get("hypotheses", []) if isinstance(multipath_payload, dict) else []
    status_rows: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        paths = row.get("paths", []) if isinstance(row.get("paths"), list) else []
        total = len(paths)
        success = sum(
            1
            for p in paths
            if isinstance(p, dict)
            and str(p.get("status", "")).lower() in {"ok", "success", "validated", "complete"}
        )
        partial = sum(1 for p in paths if isinstance(p, dict) and str(p.get("status", "")).lower() == "partial")
        failed = sum(1 for p in paths if isinstance(p, dict) and str(p.get("status", "")).lower() in {"fail", "failed"})
        missing: list[str] = []
        for p in paths:
            if not isinstance(p, dict):
                continue
            for item in p.get("missing_artifacts", []) if isinstance(p.get("missing_artifacts"), list) else []:
                text = str(item).strip()
                if text and text not in missing:
                    missing.append(text)
        overall = (
            "complete"
            if total >= 2
            and success >= 2
            and failed == 0
            and str(row.get("status", "")).lower() in {"validated", "ok", "success", "complete"}
            else "incomplete"
        )
        status_rows.append(
            {
                "hypothesis_id": row.get("hypothesis_id", ""),
                "overall": overall,
                "path_total": total,
                "path_success": success,
                "path_partial": partial,
                "path_failed": failed,
                "missing_artifacts": missing,
            }
        )
    return {"hypotheses": status_rows}


def _build_expected_artifact_validation_payload(plan_json: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for hyp in plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []:
        if not isinstance(hyp, dict):
            continue
        hid = str(hyp.get("id", "")).strip()
        expected = hyp.get("expected_artifacts", []) if isinstance(hyp.get("expected_artifacts"), list) else []
        invalid = hyp.get("invalid_expected_artifacts", []) if isinstance(hyp.get("invalid_expected_artifacts"), list) else []
        rows.append(
            {
                "hypothesis_id": hid,
                "valid_count": len(expected),
                "invalid_count": len(invalid),
                "invalid_items": invalid,
            }
        )
    return {"hypotheses": rows, "valid": all(r["invalid_count"] == 0 for r in rows)}


def _render_plan_markdown_from_json(plan_json: dict[str, Any]) -> str:
    hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    if not hypotheses:
        return "## 分析计划\n\n未生成结构化假设。"
    lines = ["## 分析计划", ""]
    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            continue
        hid = str(hyp.get("id", "")).strip() or "H?"
        title = str(hyp.get("title", "")).strip() or hid
        hypothesis = str(hyp.get("hypothesis", "")).strip() or "未提供"
        steps = hyp.get("validation_plan_steps", []) if isinstance(hyp.get("validation_plan_steps"), list) else []
        expected = hyp.get("expected_artifacts", []) if isinstance(hyp.get("expected_artifacts"), list) else []
        lines.append(f"### {hid} {title}")
        lines.append(f"- 假设：{hypothesis}")
        if steps:
            lines.append("- 分析步骤：")
            for idx, step in enumerate(steps, 1):
                lines.append(f"  {idx}. {step}")
        if expected:
            lines.append("- 预期产物：")
            for item in expected:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).strip()


def _synthesize_plan_from_hypothesis_results(
    session_dir: Path, data_quality: dict[str, Any] | None = None
) -> dict[str, Any]:
    results_payload = _load_json_if_exists(session_dir / "result" / "hypothesis_results.json")
    rows = results_payload.get("hypotheses", []) if isinstance(results_payload, dict) else []
    hypotheses: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        raw = str(row.get("hypothesis", "")).strip()
        hid_match = re.search(r"\b(H\d+)\b", raw.upper())
        hid = hid_match.group(1) if hid_match else f"H{idx+1}"
        title = raw
        if ":" in raw:
            title = raw.split(":", 1)[1].strip() or raw
        step_map = row.get("steps", {}) if isinstance(row.get("steps"), dict) else {}
        step_names = [str(name).strip() for name in step_map.keys() if str(name).strip()]
        expected_raw = row.get("expected_artifacts", []) if isinstance(row.get("expected_artifacts"), list) else []
        artifacts, invalid = _sanitize_expected_artifacts([str(x).strip() for x in expected_raw if str(x).strip()])
        profile = resolve_hypothesis_profile(
            session_dir,
            title=title,
            hypothesis_text=raw,
            explicit_key={
                "H1": "difference",
                "H2": "predictive",
                "H3": "correlation",
                "H4": "embedding",
            }.get(hid, ""),
        )
        hypothesis_text = str(profile.get("hypothesis", "")).strip() or f"{title} 可通过多路径验证获得证据支持。"
        normalized_title = str(profile.get("title", "")).strip() or title
        hypotheses.append(
            {
                "id": hid,
                "title": normalized_title,
                "hypothesis": hypothesis_text,
                "validation_plan_steps": step_names,
                "expected_artifacts": artifacts,
                "minimum_evidence_requirements": {
                    "quant_metrics_min": 2,
                    "require_significance_metric": True,
                    "require_effect_metric": True,
                },
                "assumption_checks": ["data_quality_ready", "feature_schema_valid"],
                "validation_paths": _default_validation_paths(
                    hid,
                    step_names,
                    artifacts,
                    normalized_title,
                    hypothesis_text,
                    session_dir=session_dir,
                ),
                "steps": step_names,
                "artifacts": artifacts,
                "invalid_expected_artifacts": invalid,
                "hypothesis_type": str(profile.get("key", "")).strip(),
            }
        )

    if hypotheses:
        return {"hypotheses": hypotheses}

    datasets = data_quality.get("datasets", []) if isinstance(data_quality, dict) else []
    first = datasets[0] if datasets and isinstance(datasets[0], dict) else {}
    dtypes = first.get("dtypes", {}) if isinstance(first.get("dtypes"), dict) else {}
    columns = set(dtypes.keys())
    numeric_cols = [name for name, dtype in dtypes.items() if any(token in str(dtype).lower() for token in ("int", "float", "double"))]
    has_group = any(col.lower() in {"group", "label", "target", "class"} for col in columns)

    fallback: list[dict[str, Any]] = []
    if has_group and numeric_cols:
        difference_profile = resolve_hypothesis_profile(session_dir, explicit_key="difference")
        fallback.append(
            {
                "id": "H1",
                "title": str(difference_profile.get("title", "")).strip() or "分组差异检验",
                "hypothesis": str(difference_profile.get("hypothesis", "")).strip() or "不同分组在关键数值特征上存在显著差异。",
                "validation_plan_steps": ["stats_tests", "multiple_testing", "stats_summary"],
                "expected_artifacts": ["stats_results.json", "multiple_testing.json", "stats_summary.json"],
                "hypothesis_type": "difference",
            }
        )
    if numeric_cols:
        predictive_profile = resolve_hypothesis_profile(session_dir, explicit_key="predictive")
        fallback.append(
            {
                "id": "H2",
                "title": str(predictive_profile.get("title", "")).strip() or "预测性能验证",
                "hypothesis": str(predictive_profile.get("hypothesis", "")).strip() or "特征组合可达到高于基线的分组识别性能。",
                "validation_plan_steps": ["model_train", "model_eval"],
                "expected_artifacts": ["model_results.json", "model_eval.json", "cv_results.json"],
                "hypothesis_type": "predictive",
            }
        )
    if has_group and numeric_cols:
        correlation_profile = resolve_hypothesis_profile(session_dir, explicit_key="correlation")
        fallback.append(
            {
                "id": "H3",
                "title": str(correlation_profile.get("title", "")).strip() or "相关结构验证",
                "hypothesis": str(correlation_profile.get("hypothesis", "")).strip() or "关键变量之间存在可解释的相关结构。",
                "validation_plan_steps": ["correlation", "viz_heatmap_cluster", "viz_network"],
                "expected_artifacts": ["correlation.json", "heatmap.png", "network.png"],
                "hypothesis_type": "correlation",
            }
        )

    normalized = _normalize_plan_json({"hypotheses": fallback}, "", session_dir=session_dir, depth=1)
    return normalized if normalized.get("hypotheses") else {"hypotheses": []}


def _register_plan_artifact(
    registry: ArtifactRegistry,
    session_dir: str | Path,
    plan_id: str,
    kind: str,
    source_path: str | Path,
    role: str,
    metadata: dict[str, Any] | None = None,
) -> Path:
    src = Path(source_path)
    if ARTIFACT_MIRROR_ENABLED:
        dest_dir = artifact_dir(session_dir, plan_id, role)
        if ARTIFACT_COPY_ENABLED:
            stored = copy_artifact(src, dest_dir)
        else:
            stored = artifact_link(src, dest_dir)
        registry.register(plan_id, kind, stored, metadata or {})
        return stored
    registry.register(plan_id, kind, src, metadata or {})
    return src


def _parse_plan_markdown(plan: str) -> dict[str, Any]:
    hypotheses: list[dict[str, Any]] = []
    if not plan:
        return {"hypotheses": hypotheses}

    lines = plan.splitlines()
    hypothesis_titles: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("*") and "假设" in stripped:
            title = stripped.strip("* ").strip()
            hypothesis_titles.append(title)

    current_title = ""
    current_steps: list[str] = []
    current_artifacts: list[dict[str, str]] = []
    section: str | None = None

    def _flush() -> None:
        nonlocal current_title, current_steps, current_artifacts
        if current_title or current_steps or current_artifacts:
            hypotheses.append(
                {
                    "title": current_title or f"hypothesis_{len(hypotheses)+1}",
                    "steps": current_steps,
                    "artifacts": current_artifacts,
                }
            )
        current_title = ""
        current_steps = []
        current_artifacts = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("####"):
            _flush()
            current_title = stripped.lstrip("#").strip()
            section = None
            continue
        if stripped.startswith("###") and not stripped.startswith("####"):
            _flush()
            section = None
            continue
        if "分析步骤" in stripped or "analysis steps" in stripped.lower():
            section = "steps"
            continue
        if "预期产物" in stripped or "expected artifacts" in stripped.lower():
            section = "artifacts"
            continue
        step_match = re.match(r"^(\d+)[\.、\)]\s*(.+)", stripped)
        if step_match and (section == "steps" or (section is None and current_title)):
            current_steps.append(step_match.group(2).strip())
            continue
        if stripped.startswith("*") and section == "artifacts":
            artifact_text = stripped.strip("* ").strip()
            if artifact_text:
                current_artifacts.append({"description": artifact_text})

    _flush()

    if not hypotheses and hypothesis_titles:
        for title in hypothesis_titles:
            hypotheses.append({"title": title, "steps": [], "artifacts": []})

    return {"hypotheses": hypotheses}


_NON_HYPOTHESIS_TITLE_HINTS = {
    "成功判据",
    "后续行动建议",
    "后续建议",
    "预期产物",
    "验证路径与执行步骤",
}


def _is_path_like_artifact(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if len(text) > 256:
        return False
    if text.startswith("**") or text.startswith("- ") or text.startswith("* "):
        return False
    if any(ch in text for ch in ("：", "。", "；", "\n", "\t")):
        return False
    if " " in text and "/" not in text and "\\" not in text:
        return False
    if re.search(r"[<>|]", text):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_\-./*?]+", text))


def _sanitize_expected_artifacts(values: list[Any]) -> tuple[list[str], list[str]]:
    valid: list[str] = []
    invalid: list[str] = []
    for raw in values:
        item = str(raw).strip()
        if not item:
            continue
        if _is_path_like_artifact(item):
            valid.append(item)
        else:
            invalid.append(item)
    return valid, invalid


def _extract_plan_table_hypotheses(plan: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not plan:
        return mapping
    for raw in plan.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue
        token = re.sub(r"[*` ]", "", parts[0]).upper()
        if not re.fullmatch(r"H\d+", token):
            continue
        hypothesis = parts[2].strip()
        if hypothesis:
            mapping[token] = hypothesis
    return mapping


def _extract_hypothesis_descriptions(plan: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not plan:
        return mapping
    # Match lines like:
    # * **假设 H1（差异性假设）**：Normal...
    # * **假设 1：...**
    pattern = re.compile(r"假设\s*(?:H)?(\d+)[^：:]*[：:]\s*(.+)", re.IGNORECASE)
    for raw in plan.splitlines():
        line = raw.strip().lstrip("*").strip()
        if "假设" not in line:
            continue
        m = pattern.search(line)
        if not m:
            continue
        hid = f"H{m.group(1)}"
        desc = m.group(2).strip()
        if desc:
            mapping[hid] = desc
    return mapping


def _extract_hypothesis_table_steps_artifacts(plan: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    step_map: dict[str, list[str]] = {}
    artifact_map: dict[str, list[str]] = {}
    if not plan:
        return step_map, artifact_map
    for raw in plan.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue
        first = re.sub(r"[*` ]", "", parts[0]).upper()
        m = re.search(r"H(\d+)", first)
        if not m:
            m = re.search(r"假设\s*(\d+)", first)
        if not m:
            continue
        hid = f"H{m.group(1)}"
        steps = [re.sub(r"<[^>]+>", " ", s).strip() for s in parts[1].split("<br>")]
        artifacts = [re.sub(r"<[^>]+>", " ", s).strip() for s in parts[2].split("<br>")]
        step_map[hid] = [s for s in steps if s and s not in {":---", "---"}]
        artifact_map[hid] = [a for a in artifacts if a and a not in {":---", "---"}]
    return step_map, artifact_map


def _normalize_plan_json(
    plan_json: dict[str, Any],
    plan_md: str,
    *,
    session_dir: Path | None = None,
    prior_plan_json: dict[str, Any] | None = None,
    depth: int = 1,
) -> dict[str, Any]:
    fallback = _parse_plan_markdown(plan_md)
    fallback_hypotheses = fallback.get("hypotheses", [])
    table_hypothesis_map = _extract_plan_table_hypotheses(plan_md)
    inline_hypothesis_map = _extract_hypothesis_descriptions(plan_md)
    table_step_map, table_artifact_map = _extract_hypothesis_table_steps_artifacts(plan_md)
    raw_hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    if not isinstance(raw_hypotheses, list):
        raw_hypotheses = []
    if not raw_hypotheses:
        # Markdown is display-only; never infer authoritative hypothesis structure from it.
        return {"hypotheses": []}
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_hypotheses):
        base = item if isinstance(item, dict) else {"title": str(item)}
        hyp_id = str(base.get("id") or "").strip().upper()
        if not re.fullmatch(r"H\d+", hyp_id):
            title = str(base.get("title", ""))
            m = re.search(r"(H\d+)", title.upper())
            hyp_id = m.group(1) if m else f"H{idx + 1}"
        title = str(base.get("title") or f"{hyp_id}: hypothesis_{idx+1}").strip()
        hypothesis_text = str(base.get("hypothesis") or "").strip()
        if hyp_id in inline_hypothesis_map:
            hypothesis_text = inline_hypothesis_map[hyp_id]
        elif not hypothesis_text:
            hypothesis_text = table_hypothesis_map.get(hyp_id, "")
        fallback_steps = []
        fallback_artifacts = []
        if idx < len(fallback_hypotheses):
            fallback_steps = fallback_hypotheses[idx].get("steps", []) or []
            fallback_artifacts = fallback_hypotheses[idx].get("artifacts", []) or []
        steps = base.get("validation_plan_steps")
        if not isinstance(steps, list) or not steps:
            steps = base.get("steps")
        if not isinstance(steps, list) or not steps:
            steps = fallback_steps
        if not steps:
            steps = table_step_map.get(hyp_id, [])
        if fallback_steps:
            step_texts = [str(s) for s in steps]
            if (not step_texts) or all(("图" in s or "plot" in s.lower()) for s in step_texts):
                steps = fallback_steps
        steps = [str(s).strip() for s in steps if str(s).strip()]
        artifacts = base.get("expected_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            artifacts = base.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            artifacts = fallback_artifacts
        if not artifacts:
            artifacts = table_artifact_map.get(hyp_id, [])
        artifact_texts = [str(a) for a in artifacts]
        if any("{'description':" in a for a in artifact_texts):
            artifacts = table_artifact_map.get(hyp_id, fallback_artifacts)
        artifacts, invalid_artifacts = _sanitize_expected_artifacts(artifacts)
        planned_followup_original = {
            "title": title,
            "hypothesis": hypothesis_text,
            "expected_artifacts": [str(a).strip() for a in artifact_texts if str(a).strip()],
            "validation_paths": [],
        }
        existing_paths = base.get("validation_paths")
        if not isinstance(existing_paths, list) or len(existing_paths) < 2:
            existing_paths = _default_validation_paths(hyp_id, steps, artifacts, title, hypothesis_text)
        else:
            normalized_paths: list[dict[str, Any]] = []
            for pidx, p in enumerate(existing_paths):
                if not isinstance(p, dict):
                    continue
                path_id = str(p.get("path_id") or f"path_{chr(97 + pidx)}").strip().lower()
                method_family = str(p.get("method_family") or "").strip().lower()
                if not method_family:
                    method_family = _infer_method_family(hyp_id, title, hypothesis_text, pidx)
                p_steps = p.get("steps") if isinstance(p.get("steps"), list) else steps
                p_artifacts = p.get("expected_artifacts") if isinstance(p.get("expected_artifacts"), list) else artifacts
                normalized_paths.append(
                    {
                        "path_id": path_id,
                        "method_family": method_family,
                        "steps": [str(s).strip() for s in (p_steps or []) if str(s).strip()],
                        "expected_artifacts": _sanitize_expected_artifacts(
                            [str(a).strip() for a in (p_artifacts or []) if str(a).strip()]
                        )[0],
                    }
                )
            existing_paths = normalized_paths if len(normalized_paths) >= 2 else _default_validation_paths(
                hyp_id,
                steps,
                artifacts,
                title,
                hypothesis_text,
            )
        planned_followup_original["validation_paths"] = [
            dict(path) for path in existing_paths if isinstance(path, dict)
        ]
        normalized.append(
            _bind_runtime_realizable_paths(
                {
                "id": hyp_id,
                "title": title,
                "hypothesis": hypothesis_text,
                "hypothesis_type": str(base.get("hypothesis_type", "")).strip(),
                "validation_plan_steps": steps,
                "expected_artifacts": artifacts,
                "minimum_evidence_requirements": {
                    "quant_metrics_min": 2,
                    "require_significance_metric": True,
                    "require_effect_metric": True,
                },
                "assumption_checks": [
                    "data_quality_ready",
                    "group_definition_valid",
                ],
                "validation_paths": existing_paths,
                # Backward-compatible fields
                "steps": steps,
                "artifacts": artifacts,
                "invalid_expected_artifacts": invalid_artifacts,
                "_planned_followup_original": planned_followup_original,
                }
            )
        )
    payload = {"hypotheses": normalized}
    bound_payload, binding_meta = _bind_followup_executable_contracts(
        payload,
        session_dir=session_dir,
        prior_plan_json=prior_plan_json,
        depth=depth,
    )
    if binding_meta.get("bindings"):
        bound_payload["followup_contract_binding"] = binding_meta
    return bound_payload


def _infer_method_family(
    hyp_id: str,
    title: str,
    hypothesis_text: str,
    index: int,
    session_dir: Path | None = None,
) -> str:
    registry = (
        load_hypothesis_profile_registry(session_dir)
        if isinstance(session_dir, Path)
        else load_hypothesis_profile_registry(Path("."))
    )
    profile_key = infer_hypothesis_profile_key(
        title=f"{hyp_id} {title}",
        hypothesis_text=hypothesis_text,
        registry=registry,
    )
    profile = registry.get(profile_key, registry.get("generic", {}))
    primary = str(profile.get("primary_method_family", "primary")).strip().lower() or "primary"
    secondary = str(profile.get("secondary_method_family", "secondary")).strip().lower() or "secondary"
    return primary if index == 0 else secondary


def _runtime_bound_validation_templates(profile_key: str) -> tuple[list[str], list[dict[str, Any]]]:
    key = str(profile_key or "").strip().lower()
    if key == "difference":
        return (
            [
                "stats_results.json",
                "multiple_testing.json",
                "stats_summary.json",
                "top_features.json",
                "differential_features_table.csv",
                "volcano_plot.png",
            ],
            [
                {
                    "path_id": "path_a",
                    "method_family": "nonparametric_or_fdr",
                    "steps": [
                        "执行组间统计检验并进行多重检验校正",
                        "汇总显著特征并绘制火山图",
                    ],
                    "expected_artifacts": ["volcano_plot.png"],
                },
                {
                    "path_id": "path_b",
                    "method_family": "parametric_test",
                    "steps": [
                        "整理显著特征表，汇总 p/q 值与效应量",
                        "输出差异特征明细表以支持后续验证",
                    ],
                    "expected_artifacts": ["differential_features_table.csv"],
                },
            ],
        )
    if key == "predictive":
        return (
            [
                "feature_selection.json",
                "feature_selection_rationale.json",
                "model_results.json",
                "model_eval.json",
                "cv_results.json",
                "roc_curve.png",
                "pr_curve.png",
                "model_performance_comparison.csv",
                "model_results_rf.json",
                "model_eval_rf.json",
                "feature_importance_rf.json",
                "feature_importance_plot_rf.png",
            ],
            [
                {
                    "path_id": "path_a",
                    "method_family": "feature_modeling",
                    "steps": [
                        "训练逻辑回归分类器并输出 holdout 与交叉验证性能",
                        "生成 ROC 与 PR 曲线，评估分类区分能力",
                    ],
                    "expected_artifacts": ["roc_curve.png", "pr_curve.png", "model_performance_comparison.csv"],
                },
                {
                    "path_id": "path_b",
                    "method_family": "cross_validation",
                    "steps": [
                        "训练随机森林分类器并计算特征重要性",
                        "输出特征重要性结果，用于验证不同建模路径下的重要特征是否一致",
                    ],
                    "expected_artifacts": ["feature_importance_rf.json", "feature_importance_plot_rf.png"],
                },
            ],
        )
    if key == "correlation":
        return (
            [
                "correlation.json",
                "network.png",
                "clustermap.png",
                "tsne_umap_plot.png",
            ],
            [
                {
                    "path_id": "path_a",
                    "method_family": "pearson_network",
                    "steps": [
                        "构建相关矩阵并绘制聚类热图",
                        "检查强相关对与聚类结构是否稳定",
                    ],
                    "expected_artifacts": ["clustermap.png"],
                },
                {
                    "path_id": "path_b",
                    "method_family": "tsne_or_umap_cluster",
                    "steps": [
                        "执行低维嵌入并观察样本空间结构",
                        "结合网络结果判断相关结构是否具备群体分离趋势",
                    ],
                    "expected_artifacts": ["tsne_umap_plot.png"],
                },
            ],
        )
    if key == "embedding":
        return (
            [
                "dimensionality.json",
                "dimensionality_tsne.json",
                "clustering.json",
                "scatter.png",
                "embedding_pca.png",
                "embedding_tsne.png",
            ],
            [
                {
                    "path_id": "path_a",
                    "method_family": "pca_cluster",
                    "steps": [
                        "执行 PCA 降维并绘制二维嵌入图",
                        "结合散点分布观察样本是否存在初步分离趋势",
                    ],
                    "expected_artifacts": ["embedding_pca.png", "scatter.png"],
                },
                {
                    "path_id": "path_b",
                    "method_family": "tsne_or_umap_cluster",
                    "steps": [
                        "执行 t-SNE 降维并输出聚类标签",
                        "结合非线性嵌入结果检查潜在亚群结构",
                    ],
                    "expected_artifacts": ["embedding_tsne.png", "clustering.json"],
                },
            ],
        )
    return [], []


def _canonical_hypothesis_identity(profile_key: str) -> tuple[str, str]:
    key = str(profile_key or "").strip().lower()
    mapping = {
        "difference": ("分组差异检验", "验证 Normal 与 EP 组在血清指标上是否存在显著差异。"),
        "predictive": ("预测性能验证", "验证血清特征子集能否构建稳定、可复现的 EP 诊断分类模型。"),
        "correlation": ("相关结构验证", "验证血清指标之间是否存在稳定的相关结构、强相关边与模块。"),
        "embedding": ("低维结构验证", "验证样本在低维嵌入空间中是否表现出稳定分离或聚类结构。"),
    }
    return mapping.get(key, ("假设验证", "验证当前假设是否得到执行与证据支持。"))


def _parse_result_hypothesis_identity(row: dict[str, Any], default_index: int) -> dict[str, Any]:
    raw = str(row.get("hypothesis", "")).strip()
    match = re.search(r"\b(H\d+)\b", raw.upper())
    hid = match.group(1) if match else f"H{default_index}"
    title = raw.split(":", 1)[1].strip() if ":" in raw else raw
    hypothesis_type = str(row.get("hypothesis_type", "")).strip().lower()
    expected_artifacts = (
        [str(x).strip() for x in row.get("expected_artifacts", []) if str(x).strip()]
        if isinstance(row.get("expected_artifacts"), list)
        else []
    )
    return {
        "id": hid,
        "title": title,
        "hypothesis_type": hypothesis_type,
        "expected_artifacts": expected_artifacts,
    }


def _align_plan_json_to_runtime_hypotheses(
    plan_json: dict[str, Any],
    hypothesis_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan_rows = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    result_rows = hypothesis_payload.get("hypotheses", []) if isinstance(hypothesis_payload, dict) else []
    if not isinstance(result_rows, list) or not result_rows:
        return plan_json, {"changed": False, "reason": "missing_hypothesis_results", "changes": []}

    plan_by_id = {
        str(row.get("id", f"H{idx+1}")).strip().upper(): row
        for idx, row in enumerate(plan_rows if isinstance(plan_rows, list) else [])
        if isinstance(row, dict)
    }
    aligned_rows: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for idx, row in enumerate(result_rows, 1):
        if not isinstance(row, dict):
            continue
        identity = _parse_result_hypothesis_identity(row, idx)
        hid = identity["id"]
        profile_key = str(identity.get("hypothesis_type", "")).strip().lower()
        canonical_title, canonical_hypothesis = _canonical_hypothesis_identity(profile_key)
        runtime_contract = _bind_runtime_realizable_paths(
            {
                "id": hid,
                "title": canonical_title,
                "hypothesis": canonical_hypothesis,
                "hypothesis_type": profile_key,
                "expected_artifacts": identity.get("expected_artifacts", []),
                "validation_paths": [],
            }
        )
        prior_row = plan_by_id.get(hid, {})
        if isinstance(prior_row, dict):
            runtime_contract["_original_planner_title"] = str(prior_row.get("title", "")).strip()
            runtime_contract["_original_planner_hypothesis"] = str(prior_row.get("hypothesis", "")).strip()
        aligned_rows.append(runtime_contract)
        before = {
            "title": str(prior_row.get("title", "")).strip() if isinstance(prior_row, dict) else "",
            "hypothesis_type": str(prior_row.get("hypothesis_type", "")).strip() if isinstance(prior_row, dict) else "",
        }
        after = {
            "title": runtime_contract.get("title", ""),
            "hypothesis_type": runtime_contract.get("hypothesis_type", ""),
        }
        if before != after:
            changes.append({"hypothesis_id": hid, "before": before, "after": after})
    aligned_payload = dict(plan_json) if isinstance(plan_json, dict) else {}
    aligned_payload["hypotheses"] = aligned_rows
    return aligned_payload, {
        "changed": bool(changes),
        "reason": "aligned_to_runtime_hypothesis_results" if changes else "already_aligned",
        "changes": changes,
    }


def _runtime_supported_profile_keys() -> set[str]:
    registry = default_hypothesis_profile_registry()
    return {
        key
        for key, meta in registry.items()
        if key != "generic" and isinstance(meta, dict)
    }


def _prior_plan_hypothesis_map(prior_plan_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = prior_plan_json.get("hypotheses", []) if isinstance(prior_plan_json, dict) else []
    payload: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(row, dict):
            continue
        hid = str(row.get("id", f"H{idx+1}")).strip().upper()
        if re.fullmatch(r"H\d+", hid):
            payload[hid] = row
    return payload


def _resolve_followup_profile_key(
    hypothesis: dict[str, Any],
    prior_plan_json: dict[str, Any] | None = None,
    session_dir: Path | None = None,
    prefer_prior_identity: bool = False,
) -> tuple[str, str]:
    item = dict(hypothesis) if isinstance(hypothesis, dict) else {}
    hid = str(item.get("id", "")).strip().upper()
    title = str(item.get("title", "")).strip()
    hypothesis_text = str(item.get("hypothesis", "")).strip()
    supported = _runtime_supported_profile_keys()
    current_key = str(item.get("hypothesis_type", "")).strip().lower()

    prior_map = _prior_plan_hypothesis_map(prior_plan_json or {})
    prior_row = prior_map.get(hid, {})
    prior_key = str(prior_row.get("hypothesis_type", "")).strip().lower() if isinstance(prior_row, dict) else ""
    if prefer_prior_identity and prior_key in supported:
        return prior_key, "prior_plan_hypothesis_type"
    if current_key in supported:
        return current_key, "explicit_hypothesis_type"
    if prior_key in supported:
        return prior_key, "prior_plan_hypothesis_type"

    registry = load_hypothesis_profile_registry(session_dir or Path("."))
    inferred = infer_hypothesis_profile_key(
        title=title,
        hypothesis_text=hypothesis_text,
        explicit_key=current_key,
        registry=registry,
    )
    if inferred in supported:
        return inferred, "inferred_from_alias"

    fallback_by_id = {"H1": "difference", "H2": "predictive", "H3": "correlation", "H4": "embedding"}
    if hid in fallback_by_id:
        return fallback_by_id[hid], "fallback_by_hypothesis_id"
    return "", "unsupported_followup_profile"


def _bind_followup_executable_contracts(
    plan_json: dict[str, Any],
    *,
    session_dir: Path | None = None,
    prior_plan_json: dict[str, Any] | None = None,
    depth: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    normalized_rows: list[dict[str, Any]] = []
    binding_rows: list[dict[str, Any]] = []
    research_only_rows: list[dict[str, Any]] = []
    prior_map = _prior_plan_hypothesis_map(prior_plan_json or {})
    prefer_prior_identity = int(depth or 1) > 1
    for idx, row in enumerate(hypotheses if isinstance(hypotheses, list) else []):
        if not isinstance(row, dict):
            continue
        item = dict(row)
        hid = str(item.get("id", f"H{idx+1}")).strip().upper() or f"H{idx+1}"
        original_followup = item.get("_planned_followup_original", {}) if isinstance(item.get("_planned_followup_original"), dict) else {}
        original_expected_source = (
            original_followup.get("expected_artifacts", [])
            if isinstance(original_followup.get("expected_artifacts"), list)
            else item.get("expected_artifacts", [])
        )
        original_expected = [str(x).strip() for x in original_expected_source if str(x).strip()]
        original_paths = (
            original_followup.get("validation_paths", [])
            if isinstance(original_followup.get("validation_paths"), list)
            else item.get("validation_paths", [])
        )
        original_families = sorted(
            {
                str(path.get("method_family", "")).strip()
                for path in original_paths
                if isinstance(path, dict) and str(path.get("method_family", "")).strip()
            }
        )
        profile_key, binding_source = _resolve_followup_profile_key(
            item,
            prior_plan_json=prior_plan_json,
            session_dir=session_dir,
            prefer_prior_identity=prefer_prior_identity,
        )
        runtime_expected, runtime_paths = _runtime_bound_validation_templates(profile_key)
        if runtime_expected and runtime_paths:
            executable = _bind_runtime_realizable_paths({**item, "hypothesis_type": profile_key})
            executable.pop("_planned_followup_original", None)
            if prefer_prior_identity:
                prior_row = prior_map.get(hid, {})
                prior_title = str(prior_row.get("title", "")).strip() if isinstance(prior_row, dict) else ""
                prior_hypothesis = str(prior_row.get("hypothesis", "")).strip() if isinstance(prior_row, dict) else ""
                if prior_title:
                    executable["title"] = prior_title
                if prior_hypothesis:
                    executable["hypothesis"] = prior_hypothesis
            normalized_rows.append(executable)
            executable_expected = [str(x).strip() for x in executable.get("expected_artifacts", []) if str(x).strip()]
            executable_families = sorted(
                {
                    str(path.get("method_family", "")).strip()
                    for path in executable.get("validation_paths", [])
                    if isinstance(path, dict) and str(path.get("method_family", "")).strip()
                }
            )
            rejected_expected = [x for x in original_expected if x and x not in executable_expected]
            rejected_families = [x for x in original_families if x and x not in executable_families]
            binding_rows.append(
                {
                    "hypothesis_id": hid,
                    "depth": depth,
                    "executable": True,
                    "binding_source": binding_source,
                    "profile_key": profile_key,
                    "planned_followup": {
                        "title": str(original_followup.get("title", item.get("title", ""))).strip(),
                        "hypothesis": str(original_followup.get("hypothesis", item.get("hypothesis", ""))).strip(),
                        "expected_artifacts": original_expected,
                        "validation_paths": original_paths,
                    },
                    "executable_contract": {
                        "title": str(executable.get("title", "")).strip(),
                        "hypothesis": str(executable.get("hypothesis", "")).strip(),
                        "expected_artifacts": executable_expected,
                        "validation_paths": executable.get("validation_paths", []),
                    },
                    "rejected_expected_artifacts": rejected_expected,
                    "rejected_method_families": rejected_families,
                    "rewrite_reason": (
                        "normalized_to_runtime_supported_contract"
                        if rejected_expected or rejected_families or binding_source != "explicit_hypothesis_type"
                        else ""
                    ),
                }
            )
            continue
        research_row = {
            "hypothesis_id": hid,
            "depth": depth,
            "executable": False,
            "binding_source": binding_source,
            "profile_key": profile_key,
            "planned_followup": {
                "title": str(original_followup.get("title", item.get("title", ""))).strip(),
                "hypothesis": str(original_followup.get("hypothesis", item.get("hypothesis", ""))).strip(),
                "expected_artifacts": original_expected,
                "validation_paths": original_paths,
            },
            "executable_contract": {},
            "rejected_expected_artifacts": original_expected,
            "rejected_method_families": original_families,
            "rewrite_reason": "no_runtime_supported_equivalent",
        }
        binding_rows.append(research_row)
        research_only_rows.append(research_row)
    normalized_payload = dict(plan_json) if isinstance(plan_json, dict) else {}
    normalized_payload["hypotheses"] = normalized_rows
    if research_only_rows:
        normalized_payload["research_only_followups"] = research_only_rows
    return normalized_payload, {
        "depth": depth,
        "bindings": binding_rows,
        "research_only_followups": research_only_rows,
        "binding_summary": {
            "total": len(binding_rows),
            "executable": sum(1 for row in binding_rows if row.get("executable")),
            "research_only": sum(1 for row in binding_rows if not row.get("executable")),
        },
    }


def _bind_runtime_realizable_paths(hypothesis: dict[str, Any]) -> dict[str, Any]:
    item = dict(hypothesis) if isinstance(hypothesis, dict) else {}
    title = str(item.get("title", "")).strip()
    hypothesis_text = str(item.get("hypothesis", "")).strip()
    profile_key = str(item.get("hypothesis_type", "")).strip()
    if not profile_key:
        profile = resolve_hypothesis_profile(Path("."), title=title, hypothesis_text=hypothesis_text)
        profile_key = str(profile.get("key", "")).strip()
    expected, paths = _runtime_bound_validation_templates(profile_key)
    if not expected or not paths:
        return item
    item["hypothesis_type"] = profile_key
    item["expected_artifacts"], invalid = _sanitize_expected_artifacts(expected)
    item["invalid_expected_artifacts"] = invalid
    item["validation_paths"] = paths
    item["validation_plan_steps"] = [
        str(step).strip()
        for path in paths
        for step in path.get("steps", [])
        if str(step).strip()
    ]
    item["steps"] = list(item["validation_plan_steps"])
    item["artifacts"] = list(item["expected_artifacts"])
    return item


def _default_validation_paths(
    hyp_id: str,
    steps: list[str],
    artifacts: list[str],
    title: str,
    hypothesis_text: str,
    session_dir: Path | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "path_id": "path_a",
            "method_family": _infer_method_family(hyp_id, title, hypothesis_text, 0, session_dir=session_dir),
            "steps": steps,
            "expected_artifacts": artifacts,
        },
        {
            "path_id": "path_b",
            "method_family": _infer_method_family(hyp_id, title, hypothesis_text, 1, session_dir=session_dir),
            "steps": list(reversed(steps)) if len(steps) > 1 else steps,
            "expected_artifacts": artifacts,
        },
    ]


def _strict_markdown_hypothesis_fallback(
    plan_md: str,
    *,
    session_dir: Path | None = None,
    prior_plan_json: dict[str, Any] | None = None,
    depth: int = 1,
) -> dict[str, Any]:
    hypothesis_map = _extract_hypothesis_descriptions(plan_md)
    table_map = _extract_plan_table_hypotheses(plan_md)
    step_map, artifact_map = _extract_hypothesis_table_steps_artifacts(plan_md)
    ids = sorted(set([*hypothesis_map.keys(), *table_map.keys()]), key=lambda x: int(x[1:]) if x[1:].isdigit() else 999)
    hypotheses: list[dict[str, Any]] = []
    for hid in ids:
        hypothesis_text = hypothesis_map.get(hid) or table_map.get(hid) or ""
        hypothesis_text = re.sub(r"[*`_]+", "", hypothesis_text).strip()
        if not hypothesis_text.strip():
            continue
        profile = resolve_hypothesis_profile(Path("."), title=hypothesis_text, hypothesis_text=hypothesis_text)
        title = str(profile.get("title", "")).strip() or f"{hid}: hypothesis"
        steps = [str(x).strip() for x in step_map.get(hid, []) if str(x).strip()]
        artifacts, invalid = _sanitize_expected_artifacts(artifact_map.get(hid, []))
        hypotheses.append(
            _bind_runtime_realizable_paths(
                {
                "id": hid,
                "title": title,
                "hypothesis": hypothesis_text.strip(),
                "hypothesis_type": str(profile.get("key", "")).strip(),
                "validation_plan_steps": steps,
                "expected_artifacts": artifacts,
                "invalid_expected_artifacts": invalid,
                "minimum_evidence_requirements": {
                    "quant_metrics_min": 2,
                    "require_significance_metric": True,
                    "require_effect_metric": True,
                },
                "assumption_checks": ["data_quality_ready", "group_definition_valid"],
                "validation_paths": _default_validation_paths(
                    hid,
                    steps,
                    artifacts,
                    title,
                    hypothesis_text.strip(),
                    session_dir=Path("."),
                ),
                "steps": steps,
                "artifacts": artifacts,
                }
            )
        )
    payload = {"hypotheses": hypotheses}
    bound_payload, binding_meta = _bind_followup_executable_contracts(
        payload,
        session_dir=session_dir,
        prior_plan_json=prior_plan_json,
        depth=depth,
    )
    if binding_meta.get("bindings"):
        bound_payload["followup_contract_binding"] = binding_meta
    return bound_payload


def _needs_validation_path_repair(plan_json: dict[str, Any]) -> bool:
    hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    if not hypotheses:
        return True
    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            return True
        paths = hyp.get("validation_paths")
        if not isinstance(paths, list) or len(paths) < 2:
            return True
        families = [str(p.get("method_family", "")).strip().lower() for p in paths if isinstance(p, dict)]
        if len(set([f for f in families if f])) < 2:
            return True
    return False


def _merge_validation_paths(
    plan_json: dict[str, Any],
    repair_payload: dict[str, Any],
) -> dict[str, Any]:
    repaired = dict(plan_json) if isinstance(plan_json, dict) else {"hypotheses": []}
    hypotheses = repaired.get("hypotheses", []) if isinstance(repaired.get("hypotheses"), list) else []
    repair_map: dict[str, list[dict[str, Any]]] = {}
    for item in repair_payload.get("hypotheses", []) if isinstance(repair_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        hid = str(item.get("id", "")).strip().upper()
        paths = item.get("validation_paths")
        if hid and isinstance(paths, list):
            repair_map[hid] = [p for p in paths if isinstance(p, dict)]
    merged_hypotheses: list[dict[str, Any]] = []
    for idx, hyp in enumerate(hypotheses):
        if not isinstance(hyp, dict):
            continue
        hid = str(hyp.get("id", f"H{idx+1}")).strip().upper()
        base_steps = [str(x).strip() for x in hyp.get("validation_plan_steps", []) if str(x).strip()]
        base_artifacts = [str(x).strip() for x in hyp.get("expected_artifacts", []) if str(x).strip()]
        candidate_paths = repair_map.get(hid, hyp.get("validation_paths", []))
        normalized_paths: list[dict[str, Any]] = []
        if isinstance(candidate_paths, list):
            for pidx, path in enumerate(candidate_paths):
                if not isinstance(path, dict):
                    continue
                normalized_paths.append(
                    {
                        "path_id": str(path.get("path_id") or f"path_{chr(97 + pidx)}").strip().lower(),
                        "method_family": str(path.get("method_family") or "").strip().lower()
                        or _infer_method_family(
                            hid,
                            str(hyp.get("title", "")),
                            str(hyp.get("hypothesis", "")),
                            pidx,
                        ),
                        "steps": [str(x).strip() for x in (path.get("steps") or base_steps) if str(x).strip()],
                        "expected_artifacts": [
                            str(x).strip()
                            for x in (path.get("expected_artifacts") or base_artifacts)
                            if str(x).strip()
                        ],
                    }
                )
        if len(normalized_paths) < 2 or len(set(p["method_family"] for p in normalized_paths if p["method_family"])) < 2:
            normalized_paths = _default_validation_paths(
                hid,
                base_steps,
                base_artifacts,
                str(hyp.get("title", "")),
                str(hyp.get("hypothesis", "")),
            )
        merged_hypotheses.append({**hyp, "validation_paths": normalized_paths})
    repaired["hypotheses"] = merged_hypotheses
    return repaired


def _collect_result_evidence(session_dir: Path) -> list[str]:
    evidence: list[str] = []
    summary_path = session_dir / "result" / "summary.json"
    if summary_path.exists():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            rows = payload.get("rows")
            cols = payload.get("columns")
            missing = payload.get("missing_total")
            evidence.append(f"数据汇总：rows={rows}, columns={cols}, missing_total={missing}")
        except Exception:
            pass
    group_means = session_dir / "result" / "group_means.csv"
    if group_means.exists():
        evidence.append("分组均值已生成：result/group_means.csv")
    numeric_summary = session_dir / "result" / "numeric_summary.csv"
    if numeric_summary.exists():
        evidence.append("数值统计摘要已生成：result/numeric_summary.csv")
    correlation = session_dir / "result" / "correlation.csv"
    if correlation.exists():
        evidence.append("相关性矩阵已生成：result/correlation.csv")
    return evidence


def _find_first_dataset(session_dir: Path) -> Path | None:
    preferred = [".xlsx", ".xls", ".csv", ".tsv", ".json"]
    files = [p for p in session_dir.iterdir() if p.is_file()]
    # Prefer tabular datasets first; keep JSON as fallback but skip manifest-like metadata files.
    for suffix in preferred:
        for path in files:
            if path.suffix.lower() != suffix:
                continue
            if suffix == ".json" and path.name.lower() in {"manifest.json", "run_state.json", "run_summary.json"}:
                continue
            return path
    return None


def _maybe_run_pipeline_variants(
    session_dir: Path,
    data_profile: dict[str, Any],
    llm: LLMClient,
    summary: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    variants = select_pipeline_variants(data_profile, goals=[], top_k=4)
    custom_records: list[dict[str, Any]] = []
    if not variants:
        dataset_path = _find_first_dataset(session_dir)
        if dataset_path is None:
            return [], [], []
        line_def = _generate_custom_line(llm, summary)
        line_def = register_line(session_dir, line_def)
        line_id = line_def.get("line_id", "unknown")
        if in_cooldown(session_dir, line_id):
            return [], [], []
        success = True
        for step in line_def.get("steps", []):
            name = step.get("name")
            if not name:
                continue
            result = run_step(name, dataset_path, session_dir, method=step.get("method"))
            if result.get("status") == "skipped":
                success = False
        if not success:
            record_failure(session_dir, line_id, CUSTOM_LINE_COOLDOWN_SEC)
        record_usage(session_dir, line_id, success, None if success else "step_failed")
        custom_records.append(
            {
                "line_id": line_id,
                "source": "autogen",
                "success": success,
            }
        )
        return [], [], custom_records
    dataset_path = _find_first_dataset(session_dir)
    if dataset_path is None:
        return [], [], []
    executed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for scored in variants:
        variant = scored.variant
        for step in variant.steps:
            run_step(step.name, dataset_path, session_dir, method=step.method)
        contract = _evaluate_pipeline_variant_contract(
            Path(session_dir),
            variant,
            execution_context={
                "executed_steps": [{"name": step.name, "method": step.method} for step in variant.steps],
                "custom_line_records": custom_records,
            },
        )
        executed.append(
            {
                "pipeline_id": scored.pipeline_id,
                "variant_id": variant.variant_id,
                "required_artifacts": list(variant.required_artifacts),
                "quality_gates": list(variant.quality_gates),
                "missing_artifacts": list(contract.get("missing", [])),
                "gate_status": contract.get("status", "fail"),
                "gate_waivers": list(contract.get("waivers", [])),
                "artifact_checks": list(contract.get("artifact_checks", [])),
                "gate_checks": list(contract.get("gate_checks", [])),
                "fallback_variant": variant.fallback_variant,
            }
        )
        if contract.get("status") == "fail":
            failures.append(
                {
                    "pipeline_id": scored.pipeline_id,
                    "variant_id": variant.variant_id,
                    "missing": list(contract.get("missing", [])),
                    "gate_status": contract.get("status", "fail"),
                    "waivers": list(contract.get("waivers", [])),
                    "fallback_variant": variant.fallback_variant,
                }
            )
    return executed, failures, custom_records


def _variant_method_family(variant: Any) -> str:
    steps = getattr(variant, "steps", []) or []
    if not steps:
        return "generic"
    first = steps[0]
    name = str(getattr(first, "name", "") or "").strip().lower()
    method = str(getattr(first, "method", "") or "").strip().lower()
    if name in {"stats_tests", "multiple_testing", "feature_selection"}:
        return "statistical"
    if name in {"correlation", "viz_network", "viz_heatmap_cluster"}:
        return "correlation"
    if name in {"model_train", "model_eval", "regression", "dimensionality", "clustering"}:
        return "predictive"
    if name in {"robust_stats", "bootstrap", "monte_carlo"}:
        return "robustness"
    if name:
        return f"{name}:{method or 'default'}"
    return "generic"


def _pick_path_c_variant(data_profile: dict[str, Any], excluded_families: set[str]) -> tuple[str, Any] | tuple[None, None]:
    variants = select_pipeline_variants(data_profile, goals=[], top_k=12)
    for scored in variants:
        family = _variant_method_family(scored.variant)
        if family in excluded_families:
            continue
        return scored.pipeline_id, scored.variant
    return None, None


def _status_vote(value: str) -> bool | None:
    low = str(value or "").strip().lower()
    if low == "validated":
        return True
    if low in {"failed", "rejected"}:
        return False
    return None


def _run_path_c_adjudication(
    session_dir: Path,
    data_profile: dict[str, Any],
    multipath_payload: dict[str, Any],
    conflict_threshold: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dataset_path = _find_first_dataset(session_dir)
    if dataset_path is None:
        return multipath_payload, {"enabled": False, "reason": "dataset_not_found", "hypotheses": []}

    from src.core.analytics.toolkit.pipelines import pipeline_registry

    registry = pipeline_registry()
    hypotheses = multipath_payload.get("hypotheses", []) if isinstance(multipath_payload, dict) else []
    if not isinstance(hypotheses, list):
        hypotheses = []
    conflict_rate = float((multipath_payload.get("stats", {}) if isinstance(multipath_payload, dict) else {}).get("conflict_rate", 0.0) or 0.0)
    if conflict_rate < float(conflict_threshold):
        return multipath_payload, {
            "enabled": False,
            "reason": "conflict_rate_below_threshold",
            "conflict_rate": conflict_rate,
            "threshold": float(conflict_threshold),
            "hypotheses": [],
        }

    adjudications: list[dict[str, Any]] = []
    for row in hypotheses:
        if not isinstance(row, dict):
            continue
        if str(row.get("consistency", "")).strip().lower() != "conflict":
            continue
        path_rows = row.get("paths", []) if isinstance(row.get("paths"), list) else []
        existing_families = {
            str(p.get("method_family", "")).strip().lower()
            for p in path_rows
            if isinstance(p, dict) and str(p.get("method_family", "")).strip()
        }
        pipeline_id, candidate = _pick_path_c_variant(data_profile, existing_families)
        if candidate is None:
            adjudications.append(
                {
                    "hypothesis_id": row.get("hypothesis_id", "UNKNOWN"),
                    "status": "skipped",
                    "reason": "no_compatible_variant",
                    "existing_families": sorted(existing_families),
                }
            )
            continue

        for step in candidate.steps:
            run_step(step.name, dataset_path, session_dir, method=step.method)
        contract = _evaluate_pipeline_variant_contract(
            session_dir,
            candidate,
            execution_context={
                "executed_steps": [{"name": step.name, "method": step.method} for step in candidate.steps],
            },
        )
        missing = list(contract.get("missing", []))
        fallback_used = ""
        path_c_status = "validated" if contract.get("status") in {"pass", "waived_by_equivalent_execution"} else "partial"
        if contract.get("status") == "fail":
            path_c_status = "partial"
            fallback_id = getattr(candidate, "fallback_variant", None)
            if fallback_id and pipeline_id in registry:
                for variant in registry[pipeline_id].variants:
                    if variant.variant_id != fallback_id:
                        continue
                    for step in variant.steps:
                        run_step(step.name, dataset_path, session_dir, method=step.method)
                    fallback_used = fallback_id
                    fallback_contract = _evaluate_pipeline_variant_contract(
                        session_dir,
                        variant,
                        execution_context={
                            "executed_steps": [{"name": step.name, "method": step.method} for step in variant.steps],
                        },
                    )
                    missing = list(fallback_contract.get("missing", []))
                    path_c_status = (
                        "validated"
                        if fallback_contract.get("status") in {"pass", "waived_by_equivalent_execution"}
                        else "partial"
                    )
                    break

        path_c_row = {
            "path_id": "path_c",
            "method_family": _variant_method_family(candidate),
            "variant_id": candidate.variant_id,
            "pipeline_id": pipeline_id,
            "status": path_c_status,
            "missing_artifacts": missing,
            "fallback_variant": fallback_used,
        }
        path_rows.append(path_c_row)
        row["paths"] = path_rows

        votes = [_status_vote(p.get("status", "")) for p in path_rows if isinstance(p, dict)]
        support = sum(1 for v in votes if v is True)
        reject = sum(1 for v in votes if v is False)
        if support >= 2:
            verdict = "validated"
        elif reject >= 2:
            verdict = "rejected"
        else:
            verdict = "inconclusive"

        row["adjudication"] = {
            "enabled": True,
            "verdict": verdict,
            "path_count": len(path_rows),
            "support_votes": support,
            "reject_votes": reject,
            "missing_votes": len([v for v in votes if v is None]),
        }
        if verdict == "validated":
            row["status"] = "validated"
            row["consistency"] = "adjudicated"
        elif verdict == "rejected":
            row["status"] = "failed"
            row["consistency"] = "adjudicated"
            row["conflict_reason"] = "path_c_majority_reject"
        else:
            row["status"] = "inconclusive"
            row["consistency"] = "conflict"
            row["conflict_reason"] = row.get("conflict_reason", "") or "path_c_no_majority"

        adjudications.append(
            {
                "hypothesis_id": row.get("hypothesis_id", "UNKNOWN"),
                "variant_id": candidate.variant_id,
                "pipeline_id": pipeline_id,
                "path_c_status": path_c_status,
                "fallback_variant": fallback_used,
                "verdict": verdict,
                "missing_artifacts": missing,
            }
        )

    if adjudications:
        total = len(hypotheses)
        conflict_count = sum(1 for item in hypotheses if isinstance(item, dict) and str(item.get("consistency", "")).lower() == "conflict")
        stats = multipath_payload.get("stats", {}) if isinstance(multipath_payload, dict) else {}
        if isinstance(stats, dict):
            stats["conflict_rate"] = round((conflict_count / total), 4) if total else 0.0
            stats["adjudicated_count"] = sum(
                1 for item in hypotheses if isinstance(item, dict) and str(item.get("consistency", "")).lower() == "adjudicated"
            )
            multipath_payload["stats"] = stats

    return multipath_payload, {
        "enabled": True,
        "threshold": float(conflict_threshold),
        "conflict_rate": conflict_rate,
        "hypotheses": adjudications,
    }


def _sanitize_outline(outline: str, session_dir: Path) -> str:
    if not outline:
        return outline
    artifact_names: list[str] = []
    for folder in ("result", "plots"):
        path = session_dir / folder
        if path.exists():
            artifact_names.extend([p.name.lower() for p in path.glob("*") if p.is_file()])
    joined = " ".join(artifact_names)
    disallowed = [
        ("lasso", "lasso"),
        ("random forest", "random_forest"),
        ("roc", "roc"),
        ("auc", "auc"),
        ("umap", "umap"),
    ]
    filtered: list[str] = []
    for line in outline.splitlines():
        lower = line.lower()
        drop = False
        for keyword, token in disallowed:
            if keyword in lower and token not in joined:
                drop = True
                break
        if not drop:
            filtered.append(line)
    return "\n".join(filtered)


def _generate_custom_line(llm: LLMClient, summary: str) -> dict[str, Any]:
    prompt = (
        "Generate a JSON line definition with keys: "
        "line_id, steps[{name, method, params}], required_inputs, required_artifacts, "
        "quality_gates, compatible_visuals. Use known module names only."
    )
    messages = [
        {"role": "system", "content": get_system("en")},
        {"role": "user", "content": f"{prompt}\n\nSummary:\n{summary}"},
    ]
    raw = llm.chat(messages, max_tokens=1024)
    payload = _safe_json_any(raw)
    if isinstance(payload, dict) and payload.get("steps"):
        return payload
    return {
        "line_id": f"autogen_{int(time.time())}",
        "steps": [
            {"name": "stats_tests", "method": "t_test", "params": {}},
            {"name": "correlation", "method": "pearson", "params": {}},
            {"name": "feature_selection", "method": "variance", "params": {}},
        ],
        "required_inputs": ["numeric_columns"],
        "required_artifacts": ["stats_results.json", "correlation.json"],
        "quality_gates": ["result:stats_results.json", "result:correlation.json"],
        "compatible_visuals": [],
    }


def _has_advanced_artifacts(session_dir: Path) -> bool:
    allowed = {
        "summary.json",
        "numeric_summary.csv",
        "group_means.csv",
        "correlation.csv",
        "data_quality.json",
        "exec_results.json",
        "analysis_step_output.txt",
        "analysis_results.md",
        "expected_artifact_validation.json",
    }
    result_dir = session_dir / "result"
    if not result_dir.exists():
        return False
    for item in result_dir.iterdir():
        if item.is_file() and item.name not in allowed:
            return True
    return False


def _extract_hypotheses(plan_text: str) -> list[str]:
    hypotheses: list[str] = []
    raw = str(plan_text or "").strip()
    if not raw:
        return hypotheses

    # Prefer structured extraction when LLM returns JSON/fenced JSON.
    parsed = _safe_json_any(raw)
    candidates: list[str] = []
    if isinstance(parsed, dict):
        for key in ("followup_hypotheses", "next_hypotheses", "hypotheses"):
            payload = parsed.get(key, [])
            if not isinstance(payload, list):
                continue
            for item in payload:
                if isinstance(item, str):
                    candidates.append(item.strip())
                elif isinstance(item, dict):
                    text = (
                        str(item.get("hypothesis", "")).strip()
                        or str(item.get("title", "")).strip()
                        or str(item.get("text", "")).strip()
                    )
                    if text:
                        candidates.append(text)
    elif isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str):
                candidates.append(item.strip())
            elif isinstance(item, dict):
                text = (
                    str(item.get("hypothesis", "")).strip()
                    or str(item.get("title", "")).strip()
                    or str(item.get("text", "")).strip()
                )
                if text:
                    candidates.append(text)

    # Text fallback: support English/Chinese hypothesis headings.
    for line in raw.splitlines():
        stripped = re.sub(r"^\s*[-*]\s*", "", line.strip())
        stripped = re.sub(r"^\s*\d+[\.)、]\s*", "", stripped)
        if not stripped:
            continue
        low = stripped.lower()
        if low.startswith("hypothesis"):
            candidates.append(stripped)
            continue
        if re.match(r"^h\d+\b", stripped, flags=re.IGNORECASE):
            candidates.append(stripped)
            continue
        if re.match(r"^假设\s*\d+", stripped):
            candidates.append(stripped)
            continue
        if "新增假设" in stripped or "follow-up hypothesis" in low:
            candidates.append(stripped)

    seen: set[str] = set()
    for item in candidates:
        text = str(item).strip()
        if not text:
            continue
        norm = re.sub(r"\s+", " ", text)
        if norm in seen:
            continue
        seen.add(norm)
        hypotheses.append(norm)
        if len(hypotheses) >= 10:
            break
    return hypotheses


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


def _run_audit(session_dir: Path) -> dict[str, Any]:
    runtime_config = _load_analysis_runtime_config(session_dir)
    required_result_artifacts = [
        str(x).strip()
        for x in runtime_config.get("required_result_artifacts", [])
        if str(x).strip()
    ]
    required = [f"result/{name}" for name in required_result_artifacts] + ["report/report_v1.html"]
    missing = []
    for rel in required:
        if not (session_dir / rel).exists():
            missing.append(rel)
    visuals_dir = session_dir / "plots"
    visuals_present = visuals_dir.exists() and any(visuals_dir.rglob("*"))
    quality_gates = [f"result:{Path(rel).name}" for rel in required if rel.startswith("result/")]
    gate_missing = _check_quality_gates(session_dir, quality_gates)
    multipath_stats: dict[str, Any] = {}
    multipath_path = session_dir / "result" / "hypothesis_multipath.json"
    if multipath_path.exists():
        try:
            multipath_payload = json.loads(multipath_path.read_text(encoding="utf-8"))
            if isinstance(multipath_payload, dict):
                multipath_stats = multipath_payload.get("stats", {}) or {}
        except Exception:
            multipath_stats = {}
    gate_stats: dict[str, Any] = {}
    gate_path = session_dir / "result" / "hypothesis_gate_report.json"
    if gate_path.exists():
        try:
            gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
            rows = gate_payload.get("hypotheses", []) if isinstance(gate_payload, dict) else []
            if isinstance(rows, list) and rows:
                gate_stats = {
                    "total": len(rows),
                    "pass": sum(1 for r in rows if str(r.get("gate_status", "")) == "pass"),
                    "partial": sum(1 for r in rows if str(r.get("gate_status", "")) == "partial"),
                    "fail": sum(1 for r in rows if str(r.get("gate_status", "")) == "fail"),
                }
        except Exception:
            gate_stats = {}
    return {
        "missing_required": missing,
        "visuals_present": bool(visuals_present),
        "quality_gates": quality_gates,
        "quality_gate_missing": gate_missing,
        "hypothesis_validation_stats": multipath_stats,
        "hypothesis_gate_stats": gate_stats,
    }


def _build_evidence_trace(session_dir: Path) -> dict[str, Any]:
    payload = _load_structured_evidence(session_dir)
    rows: list[dict[str, Any]] = []
    for hyp in payload.get("hypotheses", []) if isinstance(payload, dict) else []:
        if not isinstance(hyp, dict):
            continue
        quant_metrics = hyp.get("quant_metrics", {})
        metric_names: list[str] = []
        if isinstance(quant_metrics, dict):
            metric_names = list(quant_metrics.keys())
        elif isinstance(quant_metrics, list):
            for item in quant_metrics:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip()
                    if name:
                        metric_names.append(name)
        rows.append(
            {
                "hypothesis_id": hyp.get("hypothesis_id", ""),
                "metrics": metric_names,
                "sources": hyp.get("evidence_sources", []),
            }
        )
    return {"hypotheses": rows}


def _build_reason_code_summary(session_dir: Path) -> dict[str, Any]:
    multipath_path = session_dir / "result" / "hypothesis_multipath.json"
    rows: list[dict[str, Any]] = []
    if multipath_path.exists():
        try:
            payload = json.loads(multipath_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        for hyp in payload.get("hypotheses", []) if isinstance(payload, dict) else []:
            if not isinstance(hyp, dict):
                continue
            reason_code = ""
            recovery_action = ""
            status = str(hyp.get("status", ""))
            if status == "inconclusive":
                reason_code = "method_conflict"
                recovery_action = "run_third_path_and_compare_stability"
            elif status == "failed":
                reason_code = "missing_artifact"
                recovery_action = "rerun_missing_step_and_verify_outputs"
            elif status == "partial":
                reason_code = "execution_error"
                recovery_action = "invoke_code_repair_then_rerun"
            rows.append(
                {
                    "hypothesis_id": hyp.get("hypothesis_id", ""),
                    "status": status,
                    "reason_code": reason_code,
                    "recovery_action": recovery_action,
                }
            )
    return {"hypotheses": rows}


def _build_analysis_quality_score(session_dir: Path) -> dict[str, Any]:
    evidence = _load_structured_evidence(session_dir)
    hypotheses = evidence.get("hypotheses", []) if isinstance(evidence, dict) else []
    total = len(hypotheses)
    with_quant = 0
    quant_ge_2 = 0
    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            continue
        metrics = hyp.get("quant_metrics", {})
        metric_count = 0
        if isinstance(metrics, dict):
            metric_count = len([k for k in metrics.keys() if str(k).strip()])
        elif isinstance(metrics, list):
            metric_count = len(
                [m for m in metrics if isinstance(m, dict) and str(m.get("name", "")).strip()]
            )
        if metric_count > 0:
            with_quant += 1
            if metric_count >= 2:
                quant_ge_2 += 1
    contract_path = session_dir / "result" / "hypothesis_validation_contract.json"
    gate_path = session_dir / "result" / "hypothesis_gate_report.json"
    contract_rate: float | None = None
    gate_rate: float | None = None
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            rows = contract.get("hypotheses", []) if isinstance(contract, dict) else []
            if rows:
                closed = sum(
                    1
                    for row in rows
                    if str(row.get("executed_status", "")).strip().lower() in {"validated", "inconclusive"}
                )
                contract_rate = round(closed / len(rows), 4)
        except Exception:
            contract_rate = None
    if gate_path.exists():
        try:
            gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
            gate_rows = gate_payload.get("hypotheses", []) if isinstance(gate_payload, dict) else []
            if gate_rows:
                passed = sum(
                    1
                    for row in gate_rows
                    if str(row.get("gate_status", "")).strip().lower() in {"pass"}
                )
                gate_rate = round(passed / len(gate_rows), 4)
        except Exception:
            gate_rate = None
    closure_source = "none"
    if contract_rate is not None and gate_rate is not None:
        closure_rate = min(contract_rate, gate_rate)
        closure_source = "min(contract,gate)"
    elif gate_rate is not None:
        closure_rate = gate_rate
        closure_source = "gate"
    elif contract_rate is not None:
        closure_rate = contract_rate
        closure_source = "contract"
    else:
        closure_rate = 0.0
    contrast_path = session_dir / "result" / "hypothesis_contrast.json"
    conflict_explain_rate = 0.0
    if contrast_path.exists():
        try:
            contrast = json.loads(contrast_path.read_text(encoding="utf-8"))
            rows = contrast.get("hypotheses", []) if isinstance(contrast, dict) else []
            conflicts = [row for row in rows if str(row.get("consistency", "")) == "conflict"]
            if conflicts:
                explained = sum(1 for row in conflicts if str(row.get("conflict_reason", "")).strip())
                conflict_explain_rate = round(explained / len(conflicts), 4)
            elif rows:
                conflict_explain_rate = 1.0
        except Exception:
            conflict_explain_rate = 0.0
    analysis_md_path = session_dir / "result" / "analysis_results.md"
    fluff_sentence_rate = 0.0
    if analysis_md_path.exists():
        text = analysis_md_path.read_text(encoding="utf-8")
        raw_sentences = [s.strip() for s in re.split(r"[。！？\n]+", text) if s.strip()]
        if raw_sentences:
            no_number = [s for s in raw_sentences if not re.search(r"\d", s)]
            fluff_sentence_rate = round(len(no_number) / len(raw_sentences), 4)
    return {
        "quantitative_coverage": round((with_quant / total), 4) if total else 0.0,
        "quant_metric_ge_2_rate": round((quant_ge_2 / total), 4) if total else 0.0,
        "hypothesis_closure_rate": closure_rate,
        "closure_source": closure_source,
        "conflict_explain_rate": conflict_explain_rate,
        "fluff_sentence_rate": fluff_sentence_rate,
    }


def _quality_consistency_errors(session_dir: Path, quality_score: dict[str, Any]) -> dict[str, Any]:
    evidence = _load_structured_evidence(session_dir)
    hypotheses = evidence.get("hypotheses", []) if isinstance(evidence, dict) else []
    total = len(hypotheses)
    quant_ge_2 = 0
    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            continue
        metrics = hyp.get("quant_metrics", {})
        if isinstance(metrics, list):
            count = len([m for m in metrics if isinstance(m, dict) and str(m.get("name", "")).strip()])
        elif isinstance(metrics, dict):
            count = len([k for k in metrics.keys() if str(k).strip()])
        else:
            count = 0
        if count >= 2:
            quant_ge_2 += 1
    expected = round((quant_ge_2 / total), 4) if total else 0.0
    actual = float(quality_score.get("quant_metric_ge_2_rate", 0.0) or 0.0)
    errors: list[str] = []
    if abs(expected - actual) > 1e-6:
        errors.append(f"quant_metric_ge_2_rate_mismatch: expected={expected}, actual={actual}")
    return {"valid": not errors, "errors": errors, "expected_quant_metric_ge_2_rate": expected, "actual_quant_metric_ge_2_rate": actual}


def _build_completion_validation(
    session_dir: Path,
    gate_payload: dict[str, Any] | None = None,
    pack_validation: dict[str, Any] | None = None,
    artifact_validation: dict[str, Any] | None = None,
    pipeline_gate_failures: list[dict[str, Any]] | None = None,
    pipeline_gate_waivers: list[dict[str, Any]] | None = None,
    closure_status: dict[str, Any] | None = None,
    expect_report: bool = False,
) -> dict[str, Any]:
    gate_payload = gate_payload if isinstance(gate_payload, dict) else {}
    pack_validation = pack_validation if isinstance(pack_validation, dict) else {}
    artifact_validation = artifact_validation if isinstance(artifact_validation, dict) else {}
    pipeline_gate_failures = (
        pipeline_gate_failures if isinstance(pipeline_gate_failures, list) else []
    )
    pipeline_gate_waivers = (
        pipeline_gate_waivers if isinstance(pipeline_gate_waivers, list) else []
    )
    closure_status = closure_status if isinstance(closure_status, dict) else load_phase_closure_map(session_dir)

    checks: dict[str, Any] = {}
    blocking_reasons: list[str] = []
    actions: list[str] = []

    essential_files = [
        "result/analysis_results.md",
        "result/expected_artifact_validation.json",
        "result/hypothesis_gate_report.json",
        "result/hypothesis_evidence_pack_validation.json",
    ]
    missing_files = [rel for rel in essential_files if not (session_dir / rel).exists()]
    checks["essential_files_present"] = not missing_files
    checks["missing_essential_files"] = missing_files
    if missing_files:
        blocking_reasons.append("missing_essential_artifacts")
        actions.append("补齐缺失核心产物后重新执行对应步骤。")

    checks["evidence_pack_valid"] = bool(pack_validation.get("valid", False))
    if not checks["evidence_pack_valid"]:
        blocking_reasons.append("invalid_evidence_pack")
        actions.append("修复 evidence pack 结构后重新执行证据装配步骤。")

    gate_rows = gate_payload.get("hypotheses", []) if isinstance(gate_payload, dict) else []
    unresolved: list[str] = []
    if isinstance(gate_rows, list):
        for row in gate_rows:
            if not isinstance(row, dict):
                continue
            status = str(row.get("gate_status", "")).strip().lower()
            if status in {"partial", "fail"}:
                unresolved.append(str(row.get("hypothesis_id", "UNKNOWN")))
    predictive_missing_bundle: list[str] = []
    if isinstance(gate_rows, list):
        for row in gate_rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("gate_rule_type", "")).strip().lower() != "predictive_performance":
                continue
            bundle = row.get("ml_repro_bundle", {}) if isinstance(row.get("ml_repro_bundle"), dict) else {}
            if not bool(bundle.get("complete", False)):
                predictive_missing_bundle.append(str(row.get("hypothesis_id", "UNKNOWN")))
    checks["unresolved_gate_hypotheses"] = unresolved
    checks["gate_resolved"] = len(unresolved) == 0
    if unresolved:
        blocking_reasons.append("unresolved_hypothesis_gate")
        actions.append("对未闭环假设补证据、冲突裁决或最小重跑后再给出最终结论。")
    checks["predictive_repro_bundle_complete"] = len(predictive_missing_bundle) == 0
    checks["predictive_missing_bundle_hypotheses"] = predictive_missing_bundle
    if predictive_missing_bundle:
        blocking_reasons.append("predictive_repro_bundle_missing")
        actions.append("补齐预测类假设的模型复现包（model_spec/data_split/metrics/training_log）。")

    missing_roles = artifact_validation.get("missing_roles", [])
    validation_errors = artifact_validation.get("errors", [])
    checks["artifact_validation_clean"] = not (missing_roles or validation_errors)
    if not checks["artifact_validation_clean"]:
        blocking_reasons.append("artifact_validation_failed")
        actions.append("修复角色产物缺失/错误，确保 artifact validator 通过。")

    checks["pipeline_gate_clean"] = len(pipeline_gate_failures) == 0
    checks["pipeline_gate_failure_count"] = len(pipeline_gate_failures)
    checks["pipeline_gate_waived_count"] = len(pipeline_gate_waivers)
    checks["pipeline_gate_waived_details"] = pipeline_gate_waivers
    if pipeline_gate_failures:
        blocking_reasons.append("pipeline_gate_failures")
        actions.append("按 pipeline gate 失败原因切换 fallback 变体并重跑失败路径。")

    validation_failures_path = session_dir / "result" / "validation_failures.json"
    checks["has_validation_failures"] = validation_failures_path.exists()
    if validation_failures_path.exists():
        blocking_reasons.append("validation_failure_recorded")
        actions.append("处理 validation_failures.json 指定失败阶段并执行最小重跑。")

    checks["phase_closure_available"] = bool(closure_status)
    if closure_status:
        closure_summary = closure_completion_summary(closure_status)
        checks["phase_closure_complete"] = bool(closure_summary.get("complete", False))
        checks["phase_closure_required_missing"] = closure_summary.get("required_missing", [])
        checks["phase_closure_incomplete_required"] = closure_summary.get("incomplete_required", [])
        checks["phase_closure_blocking_required"] = closure_summary.get("blocking_required", [])
        if not checks["phase_closure_complete"]:
            blocking_reasons.append("step_closure_incomplete")
            actions.append("按步骤级闭环状态补跑/修复阻塞阶段后，再进行最终完成态判定。")
    else:
        checks["phase_closure_complete"] = True
        checks["phase_closure_required_missing"] = []
        checks["phase_closure_incomplete_required"] = []
        checks["phase_closure_blocking_required"] = []

    if expect_report:
        report_dir = session_dir / "report"
        report_generated = report_dir.exists() and any(report_dir.glob("report_v*.*"))
        checks["report_generated"] = report_generated
        if not report_generated:
            blocking_reasons.append("report_missing")
            actions.append("补跑报告装配步骤并确认 report/report_v*.html 产出。")

    return {
        "complete": len(blocking_reasons) == 0,
        "status": "complete" if len(blocking_reasons) == 0 else "incomplete",
        "checks": checks,
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "recovery_actions": list(dict.fromkeys(actions)),
    }


def _build_ml_repro_bundle(
    session_dir: Path,
    gate_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate_rows = (
        gate_report.get("hypotheses", [])
        if isinstance(gate_report, dict) and isinstance(gate_report.get("hypotheses"), list)
        else []
    )
    predictive_ids = [
        str(row.get("hypothesis_id", "UNKNOWN")).strip().upper()
        for row in gate_rows
        if isinstance(row, dict) and str(row.get("gate_rule_type", "")).strip().lower() == "predictive_performance"
    ]
    if not predictive_ids:
        return {"enabled": False, "hypotheses": [], "reason": "no_predictive_hypothesis"}

    result_dir = session_dir / "result"
    repro_root = ensure_dir(result_dir / "ml_repro")
    model_results = _load_json_if_exists(result_dir / "model_results.json")
    model_eval = _load_json_if_exists(result_dir / "model_eval.json")
    model_eval_detail = _load_json_if_exists(result_dir / "model_eval_detail.json")
    cv_results = _load_json_if_exists(result_dir / "cv_results.json")
    confusion = _load_json_if_exists(result_dir / "confusion_matrix.json")
    top_features = _load_json_if_exists(result_dir / "top_features.json")

    required_files = [
        "model_spec.json",
        "data_split.json",
        "metrics.json",
        "training_log.txt",
    ]
    index_rows: list[dict[str, Any]] = []
    for hid in predictive_ids:
        bundle_dir = ensure_dir(repro_root / hid.lower())
        model_spec = {
            "hypothesis_id": hid,
            "model_type": str(model_results.get("model", "centroid")),
            "label_col": model_results.get("label_col"),
            "numeric_features": model_results.get("numeric_features", []),
            "random_seed": model_results.get("random_seed", 0),
            "group_info": model_results.get("group_info", {}),
        }
        data_split = {
            "hypothesis_id": hid,
            "strategy": "train_test_split_80_20",
            "train_size": model_results.get("train_size"),
            "test_size": model_results.get("test_size"),
            "n_samples": model_results.get("n_samples"),
        }
        metrics = {
            "hypothesis_id": hid,
            "train_accuracy": model_results.get("train_accuracy"),
            "test_accuracy": model_results.get("test_accuracy"),
            "majority_accuracy": (model_eval.get("metrics", {}) if isinstance(model_eval.get("metrics"), dict) else {}).get("majority_accuracy"),
            "centroid_accuracy": (model_eval.get("metrics", {}) if isinstance(model_eval.get("metrics"), dict) else {}).get("centroid_accuracy"),
            "cv_mean_accuracy": cv_results.get("mean_accuracy"),
            "cv_std_accuracy": cv_results.get("std_accuracy"),
            "cv_status": cv_results.get("status", "unknown"),
        }
        write_json(bundle_dir / "model_spec.json", model_spec)
        write_json(bundle_dir / "data_split.json", data_split)
        write_json(bundle_dir / "metrics.json", metrics)
        log_lines = [
            f"hypothesis_id={hid}",
            f"model_type={model_spec.get('model_type')}",
            f"train_size={data_split.get('train_size')}",
            f"test_size={data_split.get('test_size')}",
            f"cv_status={metrics.get('cv_status')}",
        ]
        validation_failure = model_eval_detail.get("validation_failure", {})
        if isinstance(validation_failure, dict) and validation_failure.get("error"):
            log_lines.append(f"validation_failure={validation_failure.get('error')}")
        write_text(bundle_dir / "training_log.txt", "\n".join(log_lines))

        optional_files: list[str] = []
        if confusion:
            write_json(bundle_dir / "confusion_matrix.json", confusion)
            optional_files.append("confusion_matrix.json")
        if top_features:
            write_json(bundle_dir / "feature_importance.json", top_features)
            optional_files.append("feature_importance.json")

        missing: list[str] = []
        for file_name in required_files:
            if not (bundle_dir / file_name).exists():
                missing.append(file_name)
        index_rows.append(
            {
                "hypothesis_id": hid,
                "bundle_dir": str(bundle_dir.relative_to(session_dir)),
                "required_files": required_files,
                "optional_files": optional_files,
                "missing_required": missing,
                "complete": len(missing) == 0,
            }
        )
    payload = {
        "enabled": True,
        "required_files": required_files,
        "hypotheses": index_rows,
    }
    write_json(result_dir / "ml_repro_bundle_index.json", payload)
    return payload

def _generic_artifact_aliases(target: str) -> list[str]:
    family_aliases = {
        "volcano_plot.png": ["manhattan_plot.png"],
        "manhattan_plot.png": ["volcano_plot.png"],
        "heatmap_cluster.png": ["heatmap.png", "cluster.png"],
        "heatmap.png": ["heatmap_cluster.png", "cluster.png"],
        "cluster.png": ["heatmap_cluster.png", "heatmap.png"],
        "clustermap.png": ["cluster.png", "heatmap_cluster.png", "heatmap.png"],
    }
    return list(family_aliases.get(target, []))


def _resolve_artifact_path(session_dir: Path, location: str, target: str) -> Path | None:
    if not target:
        return None
    if location == "result":
        path = session_dir / "result" / target
        return path if path.exists() else None
    if location == "plots":
        path = session_dir / "plots" / target
        return path if path.exists() else None
    if location == "report":
        path = session_dir / "report" / target
        return path if path.exists() else None
    result_path = session_dir / "result" / target
    if result_path.exists():
        return result_path
    plot_path = session_dir / "plots" / target
    if plot_path.exists():
        return plot_path
    report_path = session_dir / "report" / target
    if report_path.exists():
        return report_path
    return None


def _artifact_capability_tags(location: str, target: str) -> set[str]:
    normalized = str(target or "").strip()
    stem = Path(normalized).name
    tags: set[str] = set()
    if not stem:
        return tags
    if stem in {"volcano_plot.png", "manhattan_plot.png"}:
        tags.update({"plot:differential", "goal:key_feature_screening"})
    if stem in {"heatmap_cluster.png", "heatmap.png", "cluster.png"}:
        tags.update({"plot:cluster_heatmap_family", "goal:correlation_structure"})
    if stem == "clustermap.png":
        tags.update({"plot:cluster_heatmap_family", "goal:correlation_structure"})
    if stem == "stats_results.json":
        tags.update({"result:stats_results", "goal:key_feature_screening"})
    if stem == "feature_selection.json":
        tags.update({"result:feature_selection", "goal:key_feature_screening"})
    if stem == "correlation.json":
        tags.update({"result:correlation", "goal:correlation_structure"})
    if stem == "model_results.json":
        tags.update({"result:model_results", "goal:model_evaluation"})
    if not tags:
        base = f"{location}:{stem}" if location != "any" else stem
        tags.add(base)
    return tags


def _collect_session_capabilities(
    session_dir: Path,
    execution_context: dict[str, Any] | None = None,
) -> set[str]:
    tags: set[str] = set()
    for location in ("result", "plots", "report"):
        base = session_dir / location
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(base)
            tags.update(_artifact_capability_tags(location, rel.name))
    if (session_dir / "result" / "hypothesis_results.json").exists():
        tags.add("execution:deterministic_hypothesis")
    if isinstance(execution_context, dict):
        for step in execution_context.get("executed_steps", []) or []:
            if not isinstance(step, dict):
                continue
            name = str(step.get("name", "")).strip()
            method = str(step.get("method", "")).strip()
            if name:
                tags.add(f"step:{name}")
            if name and method:
                tags.add(f"step:{name}:{method}")
        if any(bool(row.get("success")) for row in execution_context.get("custom_line_records", []) or [] if isinstance(row, dict)):
            tags.add("execution:custom_line_success")
    return tags


def _evaluate_gate_target(
    session_dir: Path,
    gate: str,
    *,
    artifact_aliases: dict[str, list[str]] | None = None,
    equivalence_rules: list[str] | None = None,
    available_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    location = "any"
    target = gate
    if ":" in gate:
        location, target = gate.split(":", 1)
    location = str(location or "any").strip() or "any"
    target = str(target or "").strip()
    report = {
        "gate": gate,
        "location": location,
        "target": target,
        "status": "missing",
    }
    if not target:
        report["status"] = "skipped"
        return report
    resolved = _resolve_artifact_path(session_dir, location, target)
    if resolved is not None:
        report["status"] = "present"
        report["matched_path"] = str(resolved)
        return report
    alias_candidates: list[str] = []
    if isinstance(artifact_aliases, dict):
        alias_candidates.extend([str(x) for x in artifact_aliases.get(target, []) if str(x).strip()])
    alias_candidates.extend(_generic_artifact_aliases(target))
    seen: set[str] = set()
    deduped_aliases: list[str] = []
    for alias in alias_candidates:
        if alias in seen:
            continue
        seen.add(alias)
        deduped_aliases.append(alias)
    for alias in deduped_aliases:
        alias_resolved = _resolve_artifact_path(session_dir, location, alias)
        if alias_resolved is None:
            continue
        report["status"] = "waived_by_equivalent_execution"
        report["waiver_basis"] = "artifact_alias"
        report["matched_target"] = alias
        report["matched_path"] = str(alias_resolved)
        return report
    rules = {str(x).strip() for x in (equivalence_rules or []) if str(x).strip()}
    capabilities = available_capabilities or set()
    if "allow_capability_equivalence" in rules:
        required_caps = {
            tag for tag in _artifact_capability_tags(location, target) if not str(tag).startswith("goal:")
        }
        matched_caps = sorted(required_caps & capabilities)
        if matched_caps:
            report["status"] = "waived_by_equivalent_execution"
            report["waiver_basis"] = "capability_match"
            report["matched_capabilities"] = matched_caps
            return report
    return report


def _check_quality_gates_detailed(
    session_dir: Path,
    gates: list[str],
    *,
    artifact_aliases: dict[str, list[str]] | None = None,
    equivalence_rules: list[str] | None = None,
    execution_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    available_capabilities = _collect_session_capabilities(session_dir, execution_context)
    rows: list[dict[str, Any]] = []
    for gate in gates:
        rows.append(
            _evaluate_gate_target(
                session_dir,
                gate,
                artifact_aliases=artifact_aliases,
                equivalence_rules=equivalence_rules,
                available_capabilities=available_capabilities,
            )
        )
    return rows


def _evaluate_pipeline_variant_contract(
    session_dir: Path,
    variant: Any,
    *,
    execution_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact_aliases = dict(getattr(variant, "artifact_aliases", {}) or {})
    equivalence_rules = list(getattr(variant, "equivalence_rules", []) or [])
    available_capabilities = _collect_session_capabilities(session_dir, execution_context)
    artifact_rows = []
    for artifact in list(getattr(variant, "required_artifacts", []) or []):
        gate = f"plots:{artifact}" if Path(artifact).suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".html"} else f"result:{artifact}"
        artifact_rows.append(
            _evaluate_gate_target(
                session_dir,
                gate,
                artifact_aliases=artifact_aliases,
                equivalence_rules=equivalence_rules,
                available_capabilities=available_capabilities,
            )
        )
    gate_rows = _check_quality_gates_detailed(
        session_dir,
        list(getattr(variant, "quality_gates", []) or []),
        artifact_aliases=artifact_aliases,
        equivalence_rules=equivalence_rules,
        execution_context=execution_context,
    )
    missing_targets: list[str] = []
    for row in [*artifact_rows, *gate_rows]:
        if row.get("status") != "missing":
            continue
        gate = str(row.get("gate", "")).strip()
        if gate and gate not in missing_targets:
            missing_targets.append(gate)
    waivers = [
        row
        for row in [*artifact_rows, *gate_rows]
        if row.get("status") == "waived_by_equivalent_execution"
    ]
    status = "fail" if missing_targets else ("waived_by_equivalent_execution" if waivers else "pass")
    return {
        "status": status,
        "missing": missing_targets,
        "artifact_checks": artifact_rows,
        "gate_checks": gate_rows,
        "waivers": waivers,
        "capabilities": sorted(available_capabilities),
    }


def _resolve_pipeline_gate_failures(
    session_dir: Path,
    failures: list[dict[str, Any]],
    *,
    custom_line_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not failures:
        return {"remaining_failures": [], "fallback_records": [], "waived_records": []}
    from src.core.analytics.toolkit.pipelines import pipeline_registry

    registry = pipeline_registry()
    dataset_path = _find_first_dataset(session_dir)
    fallback_records: list[dict[str, Any]] = []
    waived_records: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    for failure in failures:
        pipeline_id = str(failure.get("pipeline_id", "")).strip()
        variant_id = str(failure.get("variant_id", "")).strip()
        spec = registry.get(pipeline_id)
        variant = None
        if spec:
            for item in spec.variants:
                if item.variant_id == variant_id:
                    variant = item
                    break
        if variant is not None:
            contract = _evaluate_pipeline_variant_contract(
                session_dir,
                variant,
                execution_context={"custom_line_records": custom_line_records or []},
            )
            if contract["status"] in {"pass", "waived_by_equivalent_execution"}:
                waived_records.append(
                    {
                        "pipeline_id": pipeline_id,
                        "variant_id": variant_id,
                        "status": contract["status"],
                        "waivers": contract["waivers"],
                        "source": "existing_equivalent_outputs",
                    }
                )
                continue
        fallback_id = str(failure.get("fallback_variant", "")).strip()
        fallback_variant = None
        if spec and fallback_id:
            for item in spec.variants:
                if item.variant_id == fallback_id:
                    fallback_variant = item
                    break
        if fallback_variant is not None and dataset_path is not None:
            for step in fallback_variant.steps:
                run_step(step.name, dataset_path, session_dir, method=step.method)
            contract = _evaluate_pipeline_variant_contract(
                session_dir,
                fallback_variant,
                execution_context={
                    "custom_line_records": custom_line_records or [],
                    "executed_steps": [
                        {"name": step.name, "method": step.method} for step in fallback_variant.steps
                    ],
                },
            )
            fallback_records.append(
                {
                    "pipeline_id": pipeline_id,
                    "fallback_variant": fallback_id,
                    "status": contract["status"],
                    "reason": failure.get("missing", []),
                }
            )
            if contract["status"] in {"pass", "waived_by_equivalent_execution"}:
                if contract["status"] == "waived_by_equivalent_execution":
                    waived_records.append(
                        {
                            "pipeline_id": pipeline_id,
                            "variant_id": fallback_id,
                            "status": contract["status"],
                            "waivers": contract["waivers"],
                            "source": "fallback_variant",
                        }
                    )
                continue
        unresolved = dict(failure)
        missing_items = failure.get("missing", []) if isinstance(failure.get("missing"), list) else []
        unresolved["reason_summary"] = "；".join([f"仍缺少 {item}" for item in missing_items]) if missing_items else "产物或门槛仍未满足"
        remaining.append(unresolved)
    return {
        "remaining_failures": remaining,
        "fallback_records": fallback_records,
        "waived_records": waived_records,
    }


def _check_quality_gates(session_dir: Path, gates: list[str]) -> list[str]:
    missing: list[str] = []
    for row in _check_quality_gates_detailed(session_dir, gates):
        if row.get("status") == "missing":
            missing.append(row["gate"])
    return missing


def _artifact_validation_report(session_dir: Path) -> dict[str, Any]:
    required_roles = [
        "DataIngest",
        "DataQuality",
        "Hypothesis",
        "CodeGen",
        "Insights",
        "EvidenceCurator",
        "Visualization",
        "RunGuard",
    ]
    manifest_path = Path(session_dir) / "meta" / "role_manifest.json"
    report: dict[str, Any] = {
        "required_roles": required_roles,
        "missing_roles": [],
        "errors": [],
    }
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = []
        latest_by_role: dict[str, dict[str, Any]] = {}
        for entry in manifest:
            if not isinstance(entry, dict):
                continue
            role_id = str(entry.get("role_id", "")).strip()
            if not role_id:
                continue
            latest_by_role[role_id] = entry
        seen_roles = set(latest_by_role.keys())
        report["missing_roles"] = [r for r in required_roles if r not in seen_roles]
        report["errors"] = [
            entry
            for role, entry in latest_by_role.items()
            if str(entry.get("status", "")).strip().lower() == "error"
        ]
    else:
        report["missing_roles"] = required_roles
    return report


def _sync_hypothesis_alignment_artifacts(session_dir: Path, hypothesis_payload: dict[str, Any]) -> None:
    write_json(session_dir / "result" / "hypothesis_results.json", hypothesis_payload)
    write_json(session_dir / "result" / "hypothesis_matrix.json", _build_hypothesis_matrix(hypothesis_payload))
    write_json(session_dir / "result" / "visual_binding.json", _build_visual_binding(session_dir))


def _extract_hypothesis_ids_from_report(report_path: Path) -> list[str]:
    if not report_path.exists():
        return []
    try:
        text = report_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    ids: set[str] = set()
    # Markdown headings: ### H1 ...
    for line in text.splitlines():
        m = re.search(r"^\s*#{2,6}\s*(H\d+)\b", line.strip(), re.IGNORECASE)
        if m:
            ids.add(m.group(1).upper())
    # HTML headings: <h3>H1 ...</h3>
    for m in re.finditer(r"<h[1-6][^>]*>\s*(H\d+)\b", text, flags=re.IGNORECASE):
        ids.add(m.group(1).upper())
    if ids:
        return sorted(ids)
    # Fallback for legacy reports without heading structure
    return sorted(set(x.upper() for x in re.findall(r"\bH\d+\b", text)))


def _hypothesis_title_only(raw: str, fallback: str = "") -> str:
    text = str(raw or "").strip()
    if ":" in text:
        tail = text.split(":", 1)[1].strip()
        if tail:
            return tail
    return text or fallback


def _plan_signature_map(session_dir: Path, payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    result: dict[str, dict[str, str]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        hid = str(item.get("id", "")).strip().upper()
        if not hid:
            continue
        title = _hypothesis_title_only(str(item.get("title", "")).strip(), hid)
        hyp_type = str(item.get("hypothesis_type", "")).strip().lower()
        if not hyp_type:
            hyp_type = infer_hypothesis_profile_key(
                title=title,
                hypothesis_text=str(item.get("hypothesis", "")).strip(),
                registry=load_hypothesis_profile_registry(session_dir),
            )
        result[hid] = {"title": title, "hypothesis_type": hyp_type}
    return result


def _signature_map_from_results(session_dir: Path, payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    result: dict[str, dict[str, str]] = {}
    for idx, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        raw = str(item.get("hypothesis", "")).strip()
        hid_match = re.search(r"\b(H\d+)\b", raw.upper())
        hid = hid_match.group(1) if hid_match else f"H{idx+1}"
        title = _hypothesis_title_only(raw, hid)
        hyp_type = str(item.get("hypothesis_type", "")).strip().lower()
        if not hyp_type:
            hyp_type = infer_hypothesis_profile_key(
                title=title,
                hypothesis_text=raw,
                registry=load_hypothesis_profile_registry(session_dir),
            )
        result[hid] = {"title": title, "hypothesis_type": hyp_type}
    return result


def _signature_map_from_evidence(session_dir: Path, payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    result: dict[str, dict[str, str]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        hid = str(item.get("hypothesis_id", "")).strip().upper()
        if not hid:
            continue
        hyp_type = str(item.get("hypothesis_type", "")).strip().lower()
        profile = resolve_hypothesis_profile(session_dir, explicit_key=hyp_type)
        result[hid] = {
            "title": str(profile.get("title", "")).strip() or hid,
            "hypothesis_type": str(profile.get("key", "")).strip().lower() or hyp_type,
        }
    return result


def _signature_map_from_multipath(session_dir: Path, payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    result: dict[str, dict[str, str]] = {}
    for idx, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        hid = str(item.get("hypothesis_id", "")).strip().upper() or f"H{idx+1}"
        title = _hypothesis_title_only(str(item.get("title", "")).strip(), hid)
        hyp_type = infer_hypothesis_profile_key(
            title=title,
            hypothesis_text=str(item.get("title", "")).strip(),
            registry=load_hypothesis_profile_registry(session_dir),
        )
        result[hid] = {"title": title, "hypothesis_type": hyp_type}
    return result


def _semantic_mismatch_rows(
    baseline: dict[str, dict[str, str]],
    current: dict[str, dict[str, str]],
) -> dict[str, Any]:
    mismatches: dict[str, Any] = {}
    for hid, expected in baseline.items():
        actual = current.get(hid)
        if not actual:
            continue
        title_mismatch = (
            expected.get("title")
            and actual.get("title")
            and str(expected.get("title")).strip() != str(actual.get("title")).strip()
        )
        type_mismatch = (
            expected.get("hypothesis_type")
            and actual.get("hypothesis_type")
            and str(expected.get("hypothesis_type")).strip().lower()
            != str(actual.get("hypothesis_type")).strip().lower()
        )
        if title_mismatch or type_mismatch:
            mismatches[hid] = {
                "expected": expected,
                "current": actual,
            }
    return mismatches


def _build_hypothesis_set_consistency(
    session_dir: Path,
    plan_json: dict[str, Any] | None = None,
    require_report_ids: bool = True,
) -> dict[str, Any]:
    def _ids_from(payload: dict[str, Any], key: str) -> list[str]:
        rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
        ids: list[str] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            raw = str(item.get(key, "")).strip().upper()
            m = re.search(r"\b(H\d+)\b", raw)
            if m:
                ids.append(m.group(1))
        return sorted(set(ids))

    plan_payload = plan_json if isinstance(plan_json, dict) else {}
    if not plan_payload:
        path = session_dir / "plan" / "analysis_plan.json"
        if path.exists():
            try:
                plan_payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                plan_payload = {}
    plan_ids = _ids_from(plan_payload, "id")

    def _load(rel: str) -> dict[str, Any]:
        p = session_dir / rel
        if not p.exists():
            return {}
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    results_ids = _ids_from(_load("result/hypothesis_results.json"), "hypothesis")
    multipath_ids = _ids_from(_load("result/hypothesis_multipath.json"), "hypothesis_id")
    evidence_ids = _ids_from(_load("result/hypothesis_evidence_pack.json"), "hypothesis_id")
    gate_ids = _ids_from(_load("result/hypothesis_gate_report.json"), "hypothesis_id")
    report_ids = _extract_hypothesis_ids_from_report(session_dir / "report" / "report_v1.html")
    results_payload = _load("result/hypothesis_results.json")
    multipath_payload = _load("result/hypothesis_multipath.json")
    evidence_payload = _load("result/hypothesis_evidence_pack.json")

    base = set(plan_ids)
    base_source = "plan"
    if not base:
        for source_name, ids in (
            ("results", results_ids),
            ("evidence_pack", evidence_ids),
            ("gate", gate_ids),
            ("multipath", multipath_ids),
        ):
            if ids:
                base = set(ids)
                base_source = f"inferred:{source_name}"
                break
    checks = {
        "plan_ids": plan_ids,
        "base_ids": sorted(base),
        "base_source": base_source,
        "results_ids": results_ids,
        "multipath_ids": multipath_ids,
        "evidence_pack_ids": evidence_ids,
        "gate_ids": gate_ids,
        "report_ids": report_ids,
    }
    plan_signatures = _plan_signature_map(session_dir, plan_payload)
    semantic_checks = {
        "plan_signatures": plan_signatures,
        "results_signatures": _signature_map_from_results(session_dir, results_payload),
        "multipath_signatures": _signature_map_from_multipath(session_dir, multipath_payload),
        "evidence_pack_signatures": _signature_map_from_evidence(session_dir, evidence_payload),
    }
    mismatches: dict[str, Any] = {}
    for name, ids in checks.items():
        if name in {"plan_ids", "base_ids", "base_source"}:
            continue
        if name == "report_ids" and not require_report_ids:
            continue
        current = set(ids)
        extra = sorted(current - base)
        missing = sorted(base - current)
        if extra or missing:
            mismatches[name] = {"missing_from_current": missing, "extra_in_current": extra}
    semantic_mismatches: dict[str, Any] = {}
    if plan_signatures:
        for name in ("results_signatures", "multipath_signatures", "evidence_pack_signatures"):
            rows = _semantic_mismatch_rows(plan_signatures, semantic_checks.get(name, {}))
            if rows:
                semantic_mismatches[name] = rows
    repair = {
        "deterministic_repair_applied": False,
        "repairable": False,
        "notes": [],
    }
    if mismatches and (set(mismatches.keys()) == {"report_ids"}) and not require_report_ids:
        repair["repairable"] = True
        repair["deterministic_repair_applied"] = True
        repair["notes"].append("pre_report_stage: report_ids check skipped deterministically")
        mismatches = {}
    return {
        "satisfied": not mismatches and not semantic_mismatches and bool(base),
        "checks": checks,
        "semantic_checks": semantic_checks,
        "semantic_mismatches": semantic_mismatches,
        "mismatches": mismatches,
        "repair": repair,
        "reason": "" if (not mismatches and not semantic_mismatches) else "incomplete_hypothesis_set",
    }


def _summarize_set_consistency_mismatches(payload: dict[str, Any]) -> str:
    mismatches = payload.get("mismatches", {}) if isinstance(payload, dict) else {}
    if not isinstance(mismatches, dict) or not mismatches:
        return ""
    parts: list[str] = []
    for key, row in mismatches.items():
        if not isinstance(row, dict):
            continue
        missing = row.get("missing_from_current", []) if isinstance(row.get("missing_from_current"), list) else []
        extra = row.get("extra_in_current", []) if isinstance(row.get("extra_in_current"), list) else []
        parts.append(f"{key}: 缺失{len(missing)}项/额外{len(extra)}项")
    return "；".join(parts)


def _validate_plan_json_contract(plan_json: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    if not isinstance(hypotheses, list) or not hypotheses:
        return False, ["missing_hypotheses"]
    for idx, hyp in enumerate(hypotheses):
        if not isinstance(hyp, dict):
            errors.append(f"hypothesis[{idx}]_not_object")
            continue
        required_fields = {"id", "title", "hypothesis", "validation_paths", "expected_artifacts"}
        missing_fields = sorted([f for f in required_fields if f not in hyp])
        if missing_fields:
            errors.append(f"hypothesis[{idx}]_missing_fields:{','.join(missing_fields)}")
        hid = str(hyp.get("id", "")).strip()
        if not re.fullmatch(r"H\d+", hid):
            errors.append(f"hypothesis[{idx}]_invalid_id:{hid}")
        title = str(hyp.get("title", "")).strip()
        if title in _NON_HYPOTHESIS_TITLE_HINTS or any(k in title for k in _NON_HYPOTHESIS_TITLE_HINTS):
            errors.append(f"hypothesis[{idx}]_invalid_title_non_hypothesis_section:{title}")
        hypothesis_text = str(hyp.get("hypothesis", "")).strip()
        if not hypothesis_text:
            errors.append(f"hypothesis[{idx}]_empty_hypothesis_text")
        paths = hyp.get("validation_paths")
        if not isinstance(paths, list) or len(paths) < 2:
            errors.append(f"hypothesis[{idx}]_missing_dual_validation_paths")
            paths = []
        path_ids: list[str] = []
        for pidx, path in enumerate(paths):
            if not isinstance(path, dict):
                errors.append(f"hypothesis[{idx}]_validation_path[{pidx}]_not_object")
                continue
            path_id = str(path.get("path_id", "")).strip().lower()
            if not path_id:
                errors.append(f"hypothesis[{idx}]_validation_path[{pidx}]_missing_path_id")
            else:
                path_ids.append(path_id)
            p_artifacts = path.get("expected_artifacts", [])
            if isinstance(p_artifacts, list):
                bad = [x for x in p_artifacts if not _is_path_like_artifact(str(x))]
                if bad:
                    errors.append(
                        f"hypothesis[{idx}]_validation_path[{pidx}]_non_path_like_expected_artifacts:{len(bad)}"
                    )
        if path_ids and len(set(path_ids)) != len(path_ids):
            errors.append(f"hypothesis[{idx}]_duplicate_validation_path_id")
        invalid_artifacts = hyp.get("invalid_expected_artifacts", [])
        if isinstance(invalid_artifacts, list) and invalid_artifacts:
            errors.append(f"hypothesis[{idx}]_invalid_expected_artifacts:{len(invalid_artifacts)}")
        expected_artifacts = hyp.get("expected_artifacts", [])
        if isinstance(expected_artifacts, list):
            bad = [x for x in expected_artifacts if not _is_path_like_artifact(str(x))]
            if bad:
                errors.append(f"hypothesis[{idx}]_non_path_like_expected_artifacts:{len(bad)}")
        else:
            errors.append(f"hypothesis[{idx}]_expected_artifacts_not_list")
        requirements = hyp.get("minimum_evidence_requirements")
        if not isinstance(requirements, dict):
            errors.append(f"hypothesis[{idx}]_missing_minimum_evidence_requirements")
        else:
            if int(requirements.get("quant_metrics_min", 0) or 0) < 1:
                errors.append(f"hypothesis[{idx}]_invalid_quant_metrics_min")
    return len(errors) == 0, errors


def _plan_validation_suggestions(errors: list[str]) -> list[str]:
    suggestions: list[str] = []
    for err in errors:
        if "missing_hypotheses" in err:
            suggestions.append("planner 必须输出 JSON，包含 hypotheses 数组，且至少一条假设。")
        elif "missing_fields" in err:
            suggestions.append("每条假设必须包含 id/title/hypothesis/validation_paths/expected_artifacts。")
        elif "empty_hypothesis_text" in err:
            suggestions.append("为每条假设补充可检验的 hypothesis 文本，不允许空字符串。")
        elif "missing_dual_validation_paths" in err:
            suggestions.append("每条假设至少提供两条验证路径（A/B），用于交叉验证。")
        elif "duplicate_validation_path_id" in err:
            suggestions.append("validation_paths 的 path_id 必须唯一（如 path_a/path_b）。")
        elif "non_path_like_expected_artifacts" in err:
            suggestions.append("expected_artifacts 仅允许路径样式字符串，禁止自然语言描述。")
        elif "missing_minimum_evidence_requirements" in err:
            suggestions.append("补充 minimum_evidence_requirements，定义最小证据门槛。")
        elif "invalid_title_non_hypothesis_section" in err:
            suggestions.append("禁止将“成功判据/后续建议”等章节标题作为假设标题。")
    # 保持顺序同时去重
    dedup: list[str] = []
    for item in suggestions:
        if item not in dedup:
            dedup.append(item)
    return dedup


def _upgrade_plan_schema_preview(plan_json: dict[str, Any], plan_md: str) -> dict[str, Any]:
    # 只读升级预览：不覆盖原始 plan 输入，仅生成兼容 v2 的预览结构
    normalized = _normalize_plan_json(
        plan_json if isinstance(plan_json, dict) else {},
        plan_md,
        depth=1,
    )
    return {
        "schema_version": "analysis_plan_schema_v2_preview",
        "generated_at": int(time.time()),
        "hypothesis_count": len(normalized.get("hypotheses", [])) if isinstance(normalized, dict) else 0,
        "preview": normalized,
    }


def _validate_codegen_steps(steps: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(steps, list) or not steps:
        return False, ["missing_codegen_steps"]
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"step[{idx}]_not_object")
            continue
        if not str(step.get("filename", "")).strip():
            errors.append(f"step[{idx}]_missing_filename")
        code = str(step.get("code", "")).strip()
        if not code:
            errors.append(f"step[{idx}]_missing_code")
    return len(errors) == 0, errors


def _run_node(name: str, func, config: dict[str, Any]):
    def _artifact_paths_snapshot(session_dir: str | Path) -> set[str]:
        path = Path(session_dir) / "manifest.json"
        if not path.exists():
            return set()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return set()
        paths: set[str] = set()
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("path"):
                    paths.add(str(item.get("path")))
        return paths

    def wrapper(state: OrchestrationState) -> OrchestrationState:
        monitoring = config.get("graph_monitoring", GRAPH_MONITORING)
        start = time.time()
        error = None
        output: dict[str, Any] = {}
        session_dir = Path(state.get("session_dir", ""))
        before_artifacts = _artifact_paths_snapshot(state.get("session_dir", ""))
        try:
            output = func(state)
        except Exception as exc:
            error = str(exc)
            output = {"errors": [error]}
        after_artifacts = _artifact_paths_snapshot(state.get("session_dir", ""))
        new_artifacts = sorted(list(after_artifacts - before_artifacts))
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
        record_role_output(
            state.get("session_dir", ""),
            role_id_for_node(name),
            "error" if error else "success",
            output=output,
            error=error,
            duration_sec=round(duration, 3),
            inputs=sorted(list(state.keys())),
            artifacts=new_artifacts,
        )
        merged_state = dict(state)
        merged_state.update(output)
        closure = evaluate_phase_closure(name, session_dir, merged_state, error=error or "")
        if closure:
            persist_phase_closure(session_dir, closure)
            closure_map = dict(state.get("closure_status", {}) or {})
            closure_map[name] = closure
            output["closure_status"] = closure_map
            recovery_trace = list(state.get("recovery_trace", []) or [])
            if closure.get("status") in {"recoverable_failed", "failed", "skipped", "recovered"}:
                recovery_trace.append(
                    {
                        "phase": name,
                        "status": closure.get("status"),
                        "failure_type": closure.get("failure_type", ""),
                        "failed_checks": closure.get("failed_checks", []),
                        "recovery_action": closure.get("recovery_action", ""),
                        "blocking": closure.get("blocking", False),
                        "timestamp": closure.get("timestamp", int(start)),
                    }
                )
            output["recovery_trace"] = recovery_trace
            output["phase_blockers"] = build_phase_blockers(closure_map)
            validation_failures = {
                "failures": [
                    {
                        "phase": phase_name,
                        "status": str(payload.get("status", "")),
                        "failure_type": str(payload.get("failure_type", "")),
                        "failed_checks": payload.get("failed_checks", []),
                        "recovery_action": str(payload.get("recovery_action", "")),
                    }
                    for phase_name, payload in closure_map.items()
                    if isinstance(payload, dict)
                    and str(payload.get("status", "")).strip() in {"recoverable_failed", "failed", "skipped"}
                ]
            }
            if validation_failures["failures"]:
                write_json(session_dir / "result" / "validation_failures.json", validation_failures)
            retry_budgets = dict(state.get("retry_budgets", {}) or {})
            retry_budgets[name] = {
                "remaining": closure.get("retry_budget_remaining", 0),
                "recoverable": closure.get("recoverable", False),
                "blocking": closure.get("blocking", False),
            }
            output["retry_budgets"] = retry_budgets
            phase_retry_counts = dict(state.get("phase_retry_counts", {}) or {})
            if closure.get("status") == "recoverable_failed":
                phase_retry_counts[name] = int(phase_retry_counts.get(name, 0) or 0) + 1
            else:
                phase_retry_counts.setdefault(name, int(phase_retry_counts.get(name, 0) or 0))
            output["phase_retry_counts"] = phase_retry_counts
        return output

    return wrapper


def _run_supervisor(
    state: OrchestrationState,
    phase_id: str,
    config: dict[str, Any],
    check_type: str = "output",
) -> dict[str, Any]:
    _supervisor_enabled = config.get("supervisor_enabled", SUPERVISOR_ENABLED)
    if not _supervisor_enabled:
        return {}

    session_dir = Path(state.get("session_dir", ""))

    supervisor_config = {
        "supervisor_wait_strategy": config.get("supervisor_wait_strategy", SUPERVISOR_WAIT_STRATEGY),
        "supervisor_poll_interval": config.get("supervisor_poll_interval", SUPERVISOR_POLL_INTERVAL),
        "supervisor_max_wait": config.get("supervisor_max_wait", SUPERVISOR_MAX_WAIT),
        "supervisor_max_retries": config.get("supervisor_max_retries", SUPERVISOR_MAX_RETRIES),
        "supervisor_semantic_check": config.get("supervisor_semantic_check", SUPERVISOR_SEMANTIC_CHECK),
    }

    def state_getter() -> OrchestrationState:
        return state

    context = SupervisorContext.from_config(
        phase_id=phase_id,
        session_dir=session_dir,
        config=supervisor_config,
        state_getter=state_getter,
    )

    supervisor = PhaseSupervisor(context, state_getter)

    if check_type == "input":
        validation = supervisor.validate_input()
    else:
        validation = supervisor.validate_output()

    if not validation["valid"]:
        validation = supervisor.analyze_mismatch(validation)

    supervisor_context = {
        "phase_id": phase_id,
        "validation": dict(validation),
        "check_type": check_type,
    }
    state["supervisor_context"] = supervisor_context

    return {
        "supervisor_validation": validation,
        "supervisor_context": supervisor_context,
    }


def create_graph(llm: LLMClient, config: dict[str, Any]):
    graph = StateGraph(OrchestrationState)

    def understand_files(state: OrchestrationState) -> OrchestrationState:
        session_dir = Path(state.get("session_dir", ""))
        init_data_sessions_active(session_dir)
        file_info = collect_file_info(str(session_dir))
        language = state.get("config", {}).get("report_language", "zh")
        fallback_note: dict[str, Any] = {}
        llm_events = list(state.get("llm_degradation_events", []) or [])
        try:
            messages = render_role_prompt(
                "file_understanding",
                language,
                prompt_key="file_summary",
                file_info=file_info,
            )
            summary = llm.chat(messages, max_tokens=2048)
        except Exception as exc:
            summary = _build_file_summary_fallback(file_info)
            fallback_note = {
                "fallback_used": True,
                "reason": f"llm_unavailable:{exc}",
                "timestamp": int(time.time()),
            }
            llm_events = _record_llm_degradation(
                state,
                node="understand_files",
                action="fallback",
                reason=str(exc),
                impact="使用文件元信息生成降级摘要，不阻断流程。",
            )
            write_json(
                ensure_dir(session_dir / "meta" / "plan_validation") / "file_summary_fallback.json",
                fallback_note,
            )
        summary_path = session_dir / "plan" / "file_summary.md"
        write_text(summary_path, summary)
        record_artifact(session_dir, summary_path, "plan", "understand_files")
        output = {"file_summary": summary, "iteration_count": int(state.get("iteration_count", 0)) or 1}
        if fallback_note:
            output["file_summary_fallback"] = fallback_note
            output["llm_degradation_events"] = llm_events
        return output

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
        session_dir = Path(state.get("session_dir", ""))
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
        history = list(state.get("docs_analysis_history", []) or [])
        research_digest = state.get("research_digest", {}) if isinstance(state.get("research_digest", {}), dict) else {}
        if int(state.get("depth", 1) or 1) > 1 and research_digest:
            history.append(
                "Research digest for prioritized follow-up:\n"
                + render_research_digest_markdown(research_digest)
            )
        depth_focus_selection = (
            state.get("depth_focus_selection", {})
            if isinstance(state.get("depth_focus_selection", {}), dict)
            else {}
        )
        if int(state.get("depth", 1) or 1) > 1 and depth_focus_selection.get("selected"):
            mode = str(depth_focus_selection.get("mode", "stop")).strip() or "stop"
            lines = [
                f"Second-round planning mode: {mode}",
                "You must explicitly state whether this round is closure_followup or escalated_research.",
                "Each hypothesis/plan item must cite its source from prior round evidence.",
            ]
            for item in depth_focus_selection.get("selected", [])[:4]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- source={item.get('hypothesis_id')} title={item.get('title')} why={item.get('why')} "
                    f"gate={item.get('gate_status')} path={item.get('path_overall')} consistency={item.get('consistency')}"
                )
            history.append("\n".join(lines))
        followups = list(state.get("followup_hypotheses", []) or [])
        if followups:
            history.append("Follow-up hypotheses:\n" + "\n".join(f"- {h}" for h in followups))
        error_dir = ensure_dir(session_dir / "meta" / "plan_validation")
        plan_runtime_errors: list[str] = []
        llm_events = list(state.get("llm_degradation_events", []) or [])
        strict_fallback_mode = bool(state.get("config", {}).get("strict_fallback_mode", True))
        plan = ""
        raw_plan_json: dict[str, Any] = {}
        plan_json: dict[str, Any] = {"hypotheses": []}
        used_deterministic_fallback = False

        try:
            plan = planner.plan(
                summary,
                history,
                plan_id=plan_id_hint,
                artifact_context=artifact_context,
                telemetry_context=telemetry_context,
                goal_hint=goal_hint,
            )
        except Exception as exc:
            plan_runtime_errors.append(f"planner_llm_failed:{exc}")
            if _is_llm_unavailable_error(exc):
                llm_events = _record_llm_degradation(
                    state,
                    node="plan_analysis",
                    action="fallback",
                    reason=str(exc),
                    impact="规划阶段 LLM 不可用，后续将启用结构化/确定性计划兜底。",
                )

        if plan:
            try:
                struct_prompt = get_prompt("planning_struct", language)
                struct_messages = [
                    {"role": "system", "content": get_system(language)},
                    {"role": "user", "content": f"{struct_prompt}\n\nPlan:\n{plan}"},
                ]
                plan_json_raw = llm.chat(struct_messages, max_tokens=2048)
                raw_plan_json = _safe_json_load(plan_json_raw)
                plan_json = _normalize_plan_json(
                    raw_plan_json,
                    plan,
                    session_dir=session_dir,
                    prior_plan_json=state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {},
                    depth=int(state.get("depth", 1) or 1),
                )
                if _needs_validation_path_repair(plan_json):
                    repair_prompt = (
                        "仅提取每条假设的 validation_paths，返回严格 JSON："
                        "{hypotheses:[{id,validation_paths:[{path_id,method_family,steps,expected_artifacts}]}]}。"
                        "必须每条假设至少两条路径，且 method_family 不同。"
                    )
                    repair_messages = [
                        {"role": "system", "content": get_system(language)},
                        {
                            "role": "user",
                            "content": (
                                f"{repair_prompt}\n\n原始计划：\n{plan}\n\n当前结构化 JSON：\n"
                                f"{json.dumps(plan_json, ensure_ascii=False)}"
                            ),
                        },
                    ]
                    repair_raw = llm.chat(repair_messages, max_tokens=1536)
                    repair_payload = _safe_json_load(repair_raw)
                    plan_json = _merge_validation_paths(plan_json, repair_payload)
            except Exception as exc:
                plan_runtime_errors.append(f"plan_struct_llm_failed:{exc}")
                if _is_llm_unavailable_error(exc):
                    llm_events = _record_llm_degradation(
                        {"llm_degradation_events": llm_events},
                        node="plan_analysis_struct",
                        action="fallback",
                        reason=str(exc),
                        impact="结构化计划生成失败，改用 markdown 严格抽取与确定性计划。",
                    )

        valid_plan, plan_errors = _validate_plan_json_contract(plan_json)
        if not valid_plan and plan:
            # strict fallback: extract only explicit H1/H2/... hypothesis statements from markdown
            plan_json = _strict_markdown_hypothesis_fallback(
                plan,
                session_dir=session_dir,
                prior_plan_json=state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {},
                depth=int(state.get("depth", 1) or 1),
            )
            valid_plan, plan_errors = _validate_plan_json_contract(plan_json)
        if not valid_plan:
            deterministic_plan = _synthesize_plan_from_hypothesis_results(
                session_dir,
                state.get("data_quality", {}),
            )
            if deterministic_plan.get("hypotheses"):
                plan_json = deterministic_plan
                valid_plan, plan_errors = _validate_plan_json_contract(plan_json)
                used_deterministic_fallback = True
                if not plan:
                    plan = _render_plan_markdown_from_json(plan_json)
                if plan_runtime_errors:
                    llm_events = _record_llm_degradation(
                        {"llm_degradation_events": llm_events},
                        node="plan_analysis",
                        action="fallback",
                        reason="deterministic_plan_activated",
                        impact="采用确定性假设计划继续执行。",
                    )
        if valid_plan and used_deterministic_fallback and strict_fallback_mode:
            strong_ok, strong_reason = _strong_fallback_plan_ok(plan_json)
            if not strong_ok:
                valid_plan = False
                plan_runtime_errors.append(f"strict_fallback_plan_rejected:{strong_reason}")
                plan_json = {"hypotheses": []}
                plan = ""
                llm_events = _record_llm_degradation(
                    {"llm_degradation_events": llm_events},
                    node="plan_analysis",
                    action="skip_due_to_quality_gate",
                    reason=strong_reason,
                    impact="确定性计划未达到强兜底门槛，已跳过后续基于该计划的弱输出。",
                )
        if not valid_plan:
            write_json(
                error_dir / "plan_contract_invalid.json",
                {
                    "plan_contract_invalid": True,
                    "errors": plan_errors,
                    "suggestions": _plan_validation_suggestions(plan_errors),
                },
            )
            plan_json = {"hypotheses": []}
        if not plan:
            plan = _render_plan_markdown_from_json(plan_json)

        upgrade_preview = _upgrade_plan_schema_preview(raw_plan_json or plan_json, plan)
        write_json(error_dir / "upgrade_preview.json", upgrade_preview)
        if plan_errors or plan_runtime_errors:
            write_json(
                error_dir / "errors.json",
                {
                    "errors": plan_errors,
                    "runtime_errors": plan_runtime_errors,
                    "valid": valid_plan,
                    "suggestions": _plan_validation_suggestions(plan_errors),
                },
            )

        plan_path = session_dir / "plan" / "analysis_plan.md"
        write_text(plan_path, plan)
        record_artifact(state.get("session_dir", ""), plan_path, "plan", "plan_analysis")
        write_json(
            session_dir / "result" / "expected_artifact_validation.json",
            _build_expected_artifact_validation_payload(plan_json),
        )
        plan_json_path = session_dir / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state.get("session_dir", ""), plan_json_path, "plan", "plan_analysis")
        binding_payload = (
            plan_json.get("followup_contract_binding", {})
            if isinstance(plan_json.get("followup_contract_binding"), dict)
            else {}
        )
        if binding_payload:
            binding_path = session_dir / "meta" / "followup_contract_binding.json"
            write_json(binding_path, binding_payload)
            record_artifact(state.get("session_dir", ""), binding_path, "meta", "plan_analysis")
        hypotheses = [
            h.get("title") for h in plan_json.get("hypotheses", []) if h.get("title")
        ]
        cleaned_hypotheses = [str(item) for item in hypotheses if item]
        plan_id, _ = plan_store.save_plan(plan, plan_json, cleaned_hypotheses)
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        _register_plan_artifact(
            artifact_registry,
            state.get("session_dir", ""),
            plan_id,
            "plan",
            plan_path,
            "plan",
            {"phase": "plan_analysis"},
        )
        if plan_json_path.exists():
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "plan",
                plan_json_path,
                "plan",
                {"phase": "plan_analysis"},
            )
        viz_plan_path = Path(state.get("session_dir", "")) / "plan" / "visualization_plan.json"
        if viz_plan_path.exists():
            visual_style = state.get("config", {}).get("visual_style", "academic")
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "visualization_plan",
                viz_plan_path,
                "visualizations",
                {"phase": "visualization_plan", "style": visual_style},
            )
        data_quality_path = state.get("data_quality_path")
        if data_quality_path:
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "data",
                data_quality_path,
                "data",
                {"phase": "data_quality"},
            )
        output: dict[str, Any] = {
            "plan": plan,
            "plan_json": plan_json,
            "hypotheses": cleaned_hypotheses,
            "plan_id": plan_id,
            "plan_blocked": not bool(plan_json.get("hypotheses")),
        }
        if binding_payload:
            output["followup_contract_binding"] = binding_payload
        if llm_events:
            output["llm_degradation_events"] = llm_events
        return output

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
        errors: list[str] = []
        llm_events = list(state.get("llm_degradation_events", []) or [])
        strict_fallback_mode = bool(state.get("config", {}).get("strict_fallback_mode", True))
        llm_unavailable_during_codegen = False
        hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
        if strict_fallback_mode and (state.get("plan_blocked") or not hypotheses):
            skip_payload = {
                "skipped": True,
                "reason": "plan_blocked_or_empty",
                "plan_blocked": bool(state.get("plan_blocked")),
            }
            skip_path = ensure_dir(session_dir / "meta" / "plan_validation") / "codegen_skipped.json"
            write_json(skip_path, skip_payload)
            record_artifact(session_dir, skip_path, "meta", "parallel_generation")
            return {
                "code_steps": [],
                "exec_results": [],
                "execution_entries": [],
                "errors": list(state.get("errors", [])) + ["codegen_skipped:plan_blocked_or_empty"],
                "llm_degradation_events": llm_events,
                "codegen_skipped": True,
            }

        steps: list[dict[str, Any]] = []
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
            try:
                code_json = llm.chat(messages, max_tokens=4096)
            except Exception as exc:
                if _is_llm_unavailable_error(exc):
                    nonlocal llm_events
                    nonlocal llm_unavailable_during_codegen
                    llm_unavailable_during_codegen = True
                    llm_events = _record_llm_degradation(
                        {"llm_degradation_events": llm_events},
                        node="parallel_generation",
                        action="fallback",
                        reason=str(exc),
                        impact=f"代码生成不可用，步骤 {step['name']} 改用内置模板脚本。",
                    )
                    if strict_fallback_mode:
                        raise RuntimeError(f"strict_codegen_skip:{exc}") from exc
                return {
                    "name": step["name"],
                    "filename": f"{step['name']}.py",
                    "code": _fallback_analysis_code(),
                }
            payload = _safe_json_any(code_json)
            entry: dict[str, Any] | None = None
            if isinstance(payload, dict):
                steps_payload = payload.get("steps")
                if isinstance(steps_payload, list) and steps_payload:
                    entry = steps_payload[0]
                elif payload.get("code"):
                    entry = payload
            elif isinstance(payload, list) and payload:
                if isinstance(payload[0], dict):
                    entry = payload[0]
            if not entry or not entry.get("code"):
                entry = {
                    "name": step["name"],
                    "filename": f"{step['name']}.py",
                    "code": _fallback_analysis_code(),
                }
            entry.setdefault("name", step["name"])
            entry.setdefault("filename", f"{step['name']}.py")
            return entry

        orchestrator = CodeExecutionOrchestrator(llm, config, session_dir, plan_id)
        recorded: list[dict[str, Any]] = []
        try:
            recorded = orchestrator.generate(steps, _generate)
        except Exception as exc:
            errors.append(f"parallel_generation generate failed: {exc}")
            if _is_llm_unavailable_error(exc):
                llm_events = _record_llm_degradation(
                    {"llm_degradation_events": llm_events},
                    node="parallel_generation",
                    action="fallback",
                    reason=str(exc),
                    impact="代码生成整体失败，转为单脚本模板兜底。",
                )
        codegen_skipped = bool(strict_fallback_mode and llm_unavailable_during_codegen and not recorded)
        if codegen_skipped:
            skip_payload = {
                "skipped": True,
                "reason": "llm_unavailable_and_strict_fallback_mode",
                "steps": [str(step.get("name", "")) for step in steps],
            }
            skip_path = ensure_dir(session_dir / "meta" / "plan_validation") / "codegen_skipped.json"
            write_json(skip_path, skip_payload)
            record_artifact(session_dir, skip_path, "meta", "parallel_generation")
            llm_events = _record_llm_degradation(
                {"llm_degradation_events": llm_events},
                node="parallel_generation",
                action="skip_due_to_quality_gate",
                reason="llm_unavailable_and_strict_fallback_mode",
                impact="为避免低质量模板代码污染验证结果，本轮跳过代码生成与执行。",
            )
        if not recorded:
            if not codegen_skipped:
                fallback_entry = {
                    "name": "analysis_step",
                    "filename": "analysis_step.py",
                    "code": _fallback_analysis_code(),
                }
                recorded = [orchestrator._write_code(fallback_entry)]
        valid_codegen, code_errors = _validate_codegen_steps(recorded)
        if not valid_codegen and not codegen_skipped:
            errors.extend([f"codegen_contract:{err}" for err in code_errors])
            fallback_entry = {
                "name": "analysis_step",
                "filename": "analysis_step.py",
                "code": _fallback_analysis_code(),
            }
            recorded = [orchestrator._write_code(fallback_entry)]
        legacy_code_dir = ensure_dir(session_dir / "code")
        write_json(legacy_code_dir / "steps.json", recorded)
        record_artifact(session_dir, legacy_code_dir / "steps.json", "code", "parallel_generation")
        if plan_id:
            steps_path = artifact_dir(session_dir, plan_id, "code") / "steps.json"
            write_json(steps_path, recorded)
            artifact_registry.register(plan_id, "code", steps_path, {"phase": "parallel_generation"})

        monitor = ExecutionMonitor(session_dir, plan_id)
        if codegen_skipped:
            exec_results = []
        else:
            try:
                exec_results = orchestrator.execute(
                    recorded,
                    int(config.get("code_execution_timeout", CODE_EXECUTION_TIMEOUT)),
                    monitor,
                    retries,
                )
            except Exception as exc:
                errors.append(f"parallel_generation execute failed: {exc}")
                monitor.log_attempt("execution", "error", str(exc))
                exec_results = [
                    {
                        "step": "execution",
                        "output": str(exc),
                        "path": "",
                        "statuses": ["error"],
                    }
                ]
        execution_entries = list(monitor.entries)
        legacy_results_dir = ensure_dir(session_dir / "result")
        write_json(legacy_results_dir / "exec_results.json", exec_results)
        record_artifact(session_dir, legacy_results_dir / "exec_results.json", "result", "parallel_generation")
        if plan_id:
            exec_path = artifact_dir(session_dir, plan_id, "result") / "exec_results.json"
            write_json(exec_path, exec_results)
            artifact_registry.register(plan_id, "result", exec_path, {"phase": "parallel_generation"})
        existing_errors = list(state.get("errors", []))
        existing_errors.extend(errors)
        return {
            "code_steps": recorded,
            "exec_results": exec_results,
            "execution_entries": execution_entries,
            "errors": existing_errors,
            "llm_degradation_events": llm_events,
            "codegen_skipped": codegen_skipped,
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
            error_payload = {
                "errors": failures,
                "retry_requested": requested,
                "retry_exhausted": exhausted,
            }
            error_dir = artifact_dir(session_dir, plan_id or "run", "execution_guard")
            write_json(error_dir / "error.json", error_payload)
            write_text(error_dir / "trace.txt", "\n".join([f.get("output", "") for f in failures]))
        supervisor_result = _run_supervisor(state, "execution_guard", config, "output")
        result = {
            "execution_retry_requested": requested,
            "execution_retry_count": next_retry,
            "execution_retry_exhausted": exhausted,
            "execution_errors": failures,
            "rollback_performed": requested,
        }
        result.update(supervisor_result)
        return result

    def code_repair(state: OrchestrationState) -> OrchestrationState:
        if not state.get("config", {}).get("role_guard_enabled", ROLE_GUARD_ENABLED):
            return {}
        strict_fallback_mode = bool(state.get("config", {}).get("strict_fallback_mode", True))
        llm_events = list(state.get("llm_degradation_events", []) or [])
        if strict_fallback_mode and _has_llm_unavailable_event(llm_events):
            session_dir = Path(state.get("session_dir", ""))
            skip_path = ensure_dir(session_dir / "meta" / "plan_validation") / "code_repair_skipped.json"
            write_json(
                skip_path,
                {
                    "skipped": True,
                    "reason": "llm_unavailable_and_strict_fallback_mode",
                },
            )
            record_artifact(session_dir, skip_path, "meta", "code_repair")
            llm_events = _record_llm_degradation(
                {"llm_degradation_events": llm_events},
                node="code_repair",
                action="skip_due_to_quality_gate",
                reason="llm_unavailable_and_strict_fallback_mode",
                impact="调试修复依赖模型能力，当前直接跳过，避免输出不可靠修复代码。",
            )
            return {"code_repair_skipped": True, "llm_degradation_events": llm_events}
        failures = state.get("execution_errors", []) or []
        if not failures:
            return {}
        code_steps = state.get("code_steps", []) or []
        session_dir = Path(state.get("session_dir", ""))
        plan_id = state.get("plan_id", "")
        if not code_steps:
            return {}
        repairer = CodeGenerator(llm, language=state.get("config", {}).get("report_language", "zh"))
        repaired_steps: list[dict[str, Any]] = []
        for step in code_steps:
            name = step.get("name") or step.get("filename")
            failure = next((f for f in failures if f.get("step") == name), None)
            if not failure or not step.get("code"):
                repaired_steps.append(step)
                continue
            repaired_code = repairer.repair_code(step["code"], failure.get("output", ""))
            repaired_steps.append({**step, "code": repaired_code})
        repair_dir = artifact_dir(session_dir, plan_id or "run", "code_repair")
        write_json(repair_dir / "repaired_steps.json", repaired_steps)
        record_artifact(session_dir, repair_dir / "repaired_steps.json", "code", "code_repair")
        orchestrator = CodeExecutionOrchestrator(llm, config, session_dir, plan_id)
        monitor = ExecutionMonitor(session_dir, plan_id)
        try:
            exec_results = orchestrator.execute(
                repaired_steps,
                int(config.get("code_execution_timeout", CODE_EXECUTION_TIMEOUT)),
                monitor,
                retries=0,
            )
        except Exception as exc:
            exec_results = [
                {"step": "code_repair", "output": str(exc), "path": "", "statuses": ["error"]}
            ]
        legacy_results_dir = ensure_dir(session_dir / "result")
        write_json(legacy_results_dir / "exec_results_repair.json", exec_results)
        record_artifact(session_dir, legacy_results_dir / "exec_results_repair.json", "result", "code_repair")
        if plan_id:
            exec_path = artifact_dir(session_dir, plan_id, "result") / "exec_results_repair.json"
            write_json(exec_path, exec_results)
        return {"exec_results": exec_results, "code_repair_ran": True}

    def analyze_results(state: OrchestrationState) -> OrchestrationState:
        outputs = state.get("exec_results", [])
        summary = "\n".join([o.get("output", "") for o in outputs])
        visual_style = state.get("config", {}).get("visual_style", "academic")
        visual_interactive = state.get("config", {}).get("visual_interactive", False)
        language = state.get("config", {}).get("report_language", "zh")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        prompt = get_prompt("analysis_structured", language)
        session_dir = Path(state.get("session_dir", ""))
        auto_evidence = _collect_result_evidence(session_dir)
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        if not _has_advanced_artifacts(session_dir):
            dataset_path = _find_first_dataset(session_dir)
            if dataset_path is not None:
                try:
                    pipeline_output = run_analysis_toolkit(dataset_path, session_dir)
                    profile_entries = [
                        s for s in pipeline_output.get("steps", []) if s.get("module") == "data_profile"
                    ]
                    data_profile: dict[str, Any] = {}
                    if profile_entries:
                        profile_path = profile_entries[0].get("output", "")
                        if profile_path:
                            try:
                                data_profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
                            except Exception:
                                data_profile = {}
                    if data_profile:
                        executed, failures, custom_records = _maybe_run_pipeline_variants(
                            session_dir, data_profile, llm, summary
                        )
                    hypothesis_payload = _run_deterministic_hypotheses(session_dir, dataset_path)
                    plan_ids = []
                    for hyp in state.get("plan_json", {}).get("hypotheses", []) if isinstance(state.get("plan_json", {}), dict) else []:
                        if isinstance(hyp, dict) and re.fullmatch(r"H\d+", str(hyp.get("id", "")).strip().upper()):
                            plan_ids.append(str(hyp.get("id", "")).strip().upper())
                    if plan_ids and isinstance(hypothesis_payload.get("hypotheses"), list):
                        filtered_rows: list[dict[str, Any]] = []
                        for row in hypothesis_payload.get("hypotheses", []):
                            if not isinstance(row, dict):
                                continue
                            raw = str(row.get("hypothesis", "")).upper()
                            m = re.search(r"\b(H\d+)\b", raw)
                            hid = m.group(1) if m else ""
                            if hid in plan_ids:
                                filtered_rows.append(row)
                        if filtered_rows:
                            hypothesis_payload["hypotheses"] = filtered_rows
                    _sync_hypothesis_alignment_artifacts(session_dir, hypothesis_payload)
                    evidence_payload = _build_hypothesis_evidence(
                        session_dir,
                        hypothesis_payload,
                        set(plan_ids) if plan_ids else None,
                    )
                    write_json(session_dir / "result" / "hypothesis_evidence.json", evidence_payload)
                    contrast_payload = _build_hypothesis_contrast(evidence_payload, session_dir)
                    write_json(session_dir / "result" / "hypothesis_contrast.json", contrast_payload)
                    effective_plan_json = (
                        state.get("plan_json", {})
                        if isinstance(state.get("plan_json", {}), dict)
                        else {}
                    )
                    if not effective_plan_json.get("hypotheses"):
                        effective_plan_json = _load_json_if_exists(session_dir / "plan" / "analysis_plan.json")
                    if not effective_plan_json.get("hypotheses"):
                        effective_plan_json = _synthesize_plan_from_hypothesis_results(
                            session_dir,
                            state.get("data_quality", {}),
                        )
                        write_json(session_dir / "plan" / "analysis_plan.json", effective_plan_json)
                        write_text(
                            session_dir / "plan" / "analysis_plan.md",
                            _render_plan_markdown_from_json(effective_plan_json),
                        )
                    aligned_plan_json, alignment_meta = _align_plan_json_to_runtime_hypotheses(
                        effective_plan_json,
                        hypothesis_payload,
                    )
                    if alignment_meta.get("changed"):
                        write_json(
                            session_dir / "meta" / "plan_identity_original.json",
                            {"plan_json": effective_plan_json},
                        )
                    effective_plan_json = aligned_plan_json
                    write_json(session_dir / "meta" / "plan_identity_alignment.json", alignment_meta)
                    write_json(session_dir / "plan" / "analysis_plan.json", effective_plan_json)
                    write_text(
                        session_dir / "plan" / "analysis_plan.md",
                        _render_plan_markdown_from_json(effective_plan_json),
                    )
                    write_json(
                        session_dir / "result" / "expected_artifact_validation.json",
                        _build_expected_artifact_validation_payload(effective_plan_json),
                    )
                    multipath_payload = _evaluate_hypothesis_validation_paths(
                        session_dir,
                        effective_plan_json,
                        evidence_payload,
                        contrast_payload,
                    )
                    path_adjudication_payload: dict[str, Any] = {}
                    multipath_payload, path_adjudication_payload = _run_path_c_adjudication(
                        session_dir,
                        data_profile if isinstance(data_profile, dict) else {},
                        multipath_payload,
                        float(state.get("config", {}).get("pathc_conflict_threshold", PATHC_CONFLICT_THRESHOLD)),
                    )
                    write_json(session_dir / "result" / "hypothesis_multipath.json", multipath_payload)
                    write_json(session_dir / "result" / "path_adjudication.json", path_adjudication_payload)
                    contract_payload = _build_hypothesis_validation_contract(
                        effective_plan_json,
                        contrast_payload,
                        multipath_payload,
                    )
                    write_json(session_dir / "result" / "hypothesis_validation_contract.json", contract_payload)
                    if plan_id:
                        for row in multipath_payload.get("hypotheses", []):
                            if not isinstance(row, dict):
                                continue
                            for path_row in row.get("paths", []):
                                if not isinstance(path_row, dict):
                                    continue
                                artifact_registry.register(
                                    plan_id,
                                    "validation_path",
                                    session_dir / "result" / "hypothesis_multipath.json",
                                    {
                                        "hypothesis_id": row.get("hypothesis_id"),
                                        "hypothesis_status": row.get("status"),
                                        "path_id": path_row.get("path_id"),
                                        "method_family": path_row.get("method_family"),
                                        "status": path_row.get("status"),
                                        "missing_artifacts": path_row.get("missing_artifacts", []),
                                    },
                                )
                    if path_adjudication_payload:
                        artifact_registry.register(
                            plan_id,
                            "result",
                            session_dir / "result" / "path_adjudication.json",
                            {"phase": "analyze_results"},
                        )
                    hypothesis_md = _hypothesis_summary_md(hypothesis_payload, session_dir)
                    auto_evidence = _collect_result_evidence(session_dir)
                except Exception:
                    pass
        if "multipath_payload" not in locals():
            multipath_path = session_dir / "result" / "hypothesis_multipath.json"
            if multipath_path.exists():
                try:
                    multipath_payload = json.loads(multipath_path.read_text(encoding="utf-8"))
                except Exception:
                    multipath_payload = {}
        if "path_adjudication_payload" not in locals() and isinstance(locals().get("multipath_payload", {}), dict):
            stats = locals().get("multipath_payload", {}).get("stats", {}) if isinstance(locals().get("multipath_payload", {}), dict) else {}
            conflict_rate = float((stats or {}).get("conflict_rate", 0.0) or 0.0) if isinstance(stats, dict) else 0.0
            if conflict_rate > 0:
                data_profile_fallback = _load_json_if_exists(session_dir / "profile" / "data_profile.json")
                multipath_payload, path_adjudication_payload = _run_path_c_adjudication(
                    session_dir,
                    data_profile_fallback,
                    multipath_payload,
                    float(state.get("config", {}).get("pathc_conflict_threshold", PATHC_CONFLICT_THRESHOLD)),
                )
                write_json(session_dir / "result" / "hypothesis_multipath.json", multipath_payload)
                write_json(session_dir / "result" / "path_adjudication.json", path_adjudication_payload)
        # Enforce active hypothesis IDs (from current plan) on all downstream hypothesis artifacts
        effective_plan_json = (
            state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {}
        )
        if not effective_plan_json.get("hypotheses"):
            effective_plan_json = _load_json_if_exists(session_dir / "plan" / "analysis_plan.json")
        active_ids = set(_active_hypothesis_ids_from_plan(effective_plan_json))
        if active_ids:
            current_results = _load_json_if_exists(session_dir / "result" / "hypothesis_results.json")
            filtered_payload = _filter_hypothesis_results_payload(current_results, active_ids)
            write_json(session_dir / "result" / "hypothesis_results.json", filtered_payload)
            _sync_hypothesis_alignment_artifacts(session_dir, filtered_payload)
            evidence_payload = _build_hypothesis_evidence(
                session_dir,
                filtered_payload,
                active_ids,
            )
            write_json(session_dir / "result" / "hypothesis_evidence.json", evidence_payload)
            contrast_payload = _build_hypothesis_contrast(evidence_payload, session_dir)
            write_json(session_dir / "result" / "hypothesis_contrast.json", contrast_payload)
            multipath_payload = _evaluate_hypothesis_validation_paths(
                session_dir,
                effective_plan_json,
                evidence_payload,
                contrast_payload,
            )
            path_adjudication_payload = {}
            multipath_payload, path_adjudication_payload = _run_path_c_adjudication(
                session_dir,
                _load_json_if_exists(session_dir / "profile" / "data_profile.json"),
                multipath_payload,
                float(state.get("config", {}).get("pathc_conflict_threshold", PATHC_CONFLICT_THRESHOLD)),
            )
            write_json(session_dir / "result" / "hypothesis_multipath.json", multipath_payload)
            write_json(session_dir / "result" / "path_adjudication.json", path_adjudication_payload)
            contract_payload = _build_hypothesis_validation_contract(
                effective_plan_json,
                contrast_payload,
                multipath_payload,
            )
            write_json(session_dir / "result" / "hypothesis_validation_contract.json", contract_payload)
            write_json(
                session_dir / "result" / "expected_artifact_validation.json",
                _build_expected_artifact_validation_payload(effective_plan_json),
            )
            path_execution_status = _build_path_execution_status(multipath_payload)
            write_json(session_dir / "result" / "path_execution_status.json", path_execution_status)
        execution_warning = ""
        if not outputs:
            execution_warning = "执行告警：未检测到可执行脚本输出，分析结果可能缺少编程验证。"
        else:
            failed = 0
            for item in outputs:
                statuses = item.get("statuses", [])
                if statuses and statuses[-1] == "error":
                    failed += 1
            if failed == len(outputs):
                execution_warning = "执行告警：所有代码步骤执行失败，分析结果仅基于规划信息生成。"
        warning_block = f"{execution_warning}\n" if execution_warning else ""
        structured_evidence = _load_structured_evidence(session_dir)
        structured_evidence_block = ""
        if structured_evidence:
            structured_evidence_block = (
                "\nStructured hypothesis evidence (JSON):\n"
                + json.dumps(structured_evidence, ensure_ascii=False, indent=2)
            )
        messages = render_role_prompt(
            "analysis",
            language,
            prompt_key="analysis_structured",
            outputs=(
                f"{warning_block}Visual style: {visual_style}\nInteractive: {visual_interactive}\n\n"
                f"Auto evidence:\n- " + "\n- ".join(auto_evidence) + f"\n\n{summary}{structured_evidence_block}"
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
                        f"{prompt}\n\n{warning_block}Visual style: {visual_style}\n"
                        f"Interactive: {visual_interactive}\n\nAuto evidence:\n- "
                        + "\n- ".join(auto_evidence)
                        + f"\n\nOutputs:\n{summary}{structured_evidence_block}"
                    ),
                },
            ]
        errors = list(state.get("errors", []))
        llm_events = list(state.get("llm_degradation_events", []) or [])
        use_llm = bool(state.get("config", {}).get("analysis_use_llm", ANALYSIS_USE_LLM))
        if use_llm:
            use_llm = _has_advanced_artifacts(Path(state.get("session_dir", "")))
        if use_llm and not structured_evidence:
            use_llm = False
            errors.append("analysis_llm_disabled_no_structured_evidence")
        analysis_payload: dict[str, Any]
        if use_llm:
            try:
                analysis_raw = llm.chat(messages, max_tokens=4096)
                analysis_payload = normalize_analysis_payload(parse_structured_payload(analysis_raw))
                if not _llm_analysis_has_metric_grounding(analysis_payload, structured_evidence, min_metric_refs=2):
                    errors.append("analysis_llm_not_metric_grounded_fallback_to_auto")
                    analysis_payload = _build_auto_analysis_payload(session_dir, auto_evidence)
            except Exception as exc:
                errors.append(f"analysis_structured_failed: {exc}")
                if _is_llm_unavailable_error(exc):
                    llm_events = _record_llm_degradation(
                        {"llm_degradation_events": llm_events},
                        node="analyze_results",
                        action="fallback",
                        reason=str(exc),
                        impact="分析解释改用自动化证据摘要与定量结果。",
                    )
                analysis_payload = {
                    "summary": "LLM 分析失败，已改为使用自动化证据摘要。",
                    "key_findings": [],
                    "evidence": [],
                    "limitations": [
                        "LLM 分析阶段失败，报告内容基于自动化统计与产物清单。",
                    ],
                    "next_steps": [
                        "确认模型服务可用后重试分析节点。",
                    ],
                }
        else:
            analysis_payload = _build_auto_analysis_payload(session_dir, auto_evidence)
        if auto_evidence:
            analysis_payload["evidence"] = list(auto_evidence) + list(analysis_payload.get("evidence", []))
        auto_payload = _build_auto_analysis_payload(session_dir, auto_evidence)
        stats_exists = (session_dir / "result" / "stats_results.json").exists()
        if auto_payload.get("summary"):
            summary_text = analysis_payload.get("summary", "")
            if stats_exists or "未检测到高级分析产物" in summary_text or "LLM 分析失败" in summary_text or not summary_text:
                analysis_payload["summary"] = auto_payload["summary"]
        if auto_payload.get("key_findings"):
            existing = {str(x) for x in analysis_payload.get("key_findings", [])}
            for item in auto_payload["key_findings"]:
                item_text = str(item)
                if item_text not in existing:
                    analysis_payload.setdefault("key_findings", []).append(item_text)
                    existing.add(item_text)
        if stats_exists:
            analysis_payload["limitations"] = auto_payload.get("limitations", [])
        elif auto_payload.get("limitations") and _has_advanced_artifacts(session_dir):
            analysis_payload["limitations"] = [
                item
                for item in analysis_payload.get("limitations", [])
                if "仅生成描述性统计" not in item and "未执行推断性统计" not in item
            ]
        if not analysis_payload.get("next_steps"):
            analysis_payload["next_steps"] = auto_payload.get("next_steps", [])
        analysis_text = analysis_payload_to_markdown(analysis_payload, execution_warning)
        if "hypothesis_md" in locals() and hypothesis_md:
            analysis_text = f"{analysis_text}\n\n{hypothesis_md}"
        analysis_path = Path(state.get("session_dir", "")) / "result" / "analysis_results.md"
        write_text(analysis_path, analysis_text)
        record_artifact(state.get("session_dir", ""), analysis_path, "result", "analyze_results")
        if plan_id:
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "result",
                analysis_path,
                "result",
                {"phase": "analysis_results"},
            )
        history = list(state.get("docs_analysis_history", []))
        history.append(analysis_text)
        summary_payload = maybe_summarize(
            session_dir,
            CUSTOM_LINE_SUMMARY_DAYS,
            CUSTOM_LINE_PROMO_MIN_RUNS,
            CUSTOM_LINE_PROMO_MIN_SUCCESS,
        )
        supervisor_result = _run_supervisor(state, "analyze_results", config, "output")
        result = {
            "docs_analysis_results": analysis_text,
            "docs_analysis_history": history,
            "errors": errors,
            "pipeline_variants": executed if "executed" in locals() else [],
            "pipeline_gate_failures": failures if "failures" in locals() else [],
            "pipeline_gate_waivers": [
                row
                for row in (executed if "executed" in locals() else [])
                if isinstance(row, dict) and row.get("gate_status") == "waived_by_equivalent_execution"
            ],
            "custom_line_records": custom_records if "custom_records" in locals() else [],
            "custom_line_summary": summary_payload,
            "hypothesis_multipath": multipath_payload if "multipath_payload" in locals() else {},
            "path_adjudication": path_adjudication_payload if "path_adjudication_payload" in locals() else {},
            "plan_json": effective_plan_json if "effective_plan_json" in locals() else state.get("plan_json", {}),
            "llm_degradation_events": llm_events,
        }
        result.update(supervisor_result)
        return result

    def evidence_curation(state: OrchestrationState) -> OrchestrationState:
        session_dir = Path(state.get("session_dir", ""))
        evidence_payload: dict[str, Any] = {}
        raw_evidence_path = session_dir / "result" / "hypothesis_evidence.json"
        if raw_evidence_path.exists():
            try:
                evidence_payload = json.loads(raw_evidence_path.read_text(encoding="utf-8"))
            except Exception:
                evidence_payload = {}
        contrast_payload = {}
        multipath_payload = {}
        contrast_path = session_dir / "result" / "hypothesis_contrast.json"
        if contrast_path.exists():
            try:
                contrast_payload = json.loads(contrast_path.read_text(encoding="utf-8"))
            except Exception:
                contrast_payload = {}
        multipath_path = session_dir / "result" / "hypothesis_multipath.json"
        if multipath_path.exists():
            try:
                multipath_payload = json.loads(multipath_path.read_text(encoding="utf-8"))
            except Exception:
                multipath_payload = {}
        metric_dict = load_metric_dictionary(session_dir)
        feature_dict = load_feature_dictionary(session_dir)
        method_dict = load_method_dictionary(session_dir)
        gate_profile = str(state.get("config", {}).get("gate_calibration_profile", "standard") or "standard")
        gate_overrides = state.get("config", {}).get("gate_calibration_overrides", {})
        dynamic_overrides: dict[str, Any] = {}
        calibration_context: dict[str, Any] = {"profile": gate_profile}
        summary_path = session_dir / "result" / "summary.json"
        if summary_path.exists():
            try:
                summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
                rows = int(summary_payload.get("rows", 0) or 0)
                calibration_context["rows"] = rows
                if rows and rows < 50:
                    dynamic_overrides.update(
                        {
                            "primary_performance_min": 0.55,
                            "secondary_performance_min": 0.5,
                            "corr_strength_min": 0.45,
                        }
                    )
                    calibration_context["small_sample_adjustment"] = True
            except Exception:
                calibration_context["rows"] = None
        try:
            conflict_rate = float((multipath_payload.get("stats", {}) if isinstance(multipath_payload, dict) else {}).get("conflict_rate", 0.0) or 0.0)
        except Exception:
            conflict_rate = 0.0
        calibration_context["conflict_rate"] = conflict_rate
        conflict_threshold = float(
            state.get("config", {}).get("pathc_conflict_threshold", PATHC_CONFLICT_THRESHOLD)
        )
        high_conflict_defaults = {
            "significance_count_min": 2.0,
            "primary_performance_min": 0.65,
            "secondary_performance_min": 0.62,
        }
        configured_high_conflict = state.get("config", {}).get("gate_high_conflict_overrides", {})
        if isinstance(configured_high_conflict, dict):
            high_conflict_defaults.update(configured_high_conflict)
        if conflict_rate > conflict_threshold:
            dynamic_overrides.update(high_conflict_defaults)
            calibration_context["high_conflict_adjustment"] = True
        calibration_context["conflict_threshold"] = conflict_threshold
        merged_overrides: dict[str, Any] = {}
        if isinstance(gate_overrides, dict):
            merged_overrides.update(gate_overrides)
        merged_overrides.update(dynamic_overrides)
        evidence_pack = build_hypothesis_evidence_pack(
            evidence_payload,
            contrast_payload,
            multipath_payload,
            metric_dict,
            feature_dict,
            method_dict,
        )
        validation = validate_hypothesis_evidence_pack(evidence_pack)
        gate_report = build_hypothesis_gate_report(
            evidence_pack,
            calibration_profile=gate_profile,
            calibration_overrides=merged_overrides,
        )
        if isinstance(gate_report, dict):
            gate_report["calibration_context"] = calibration_context
            gate_rows = gate_report.get("hypotheses", []) if isinstance(gate_report.get("hypotheses"), list) else []
            if gate_rows:
                partial_count = sum(1 for row in gate_rows if isinstance(row, dict) and str(row.get("gate_status", "")) == "partial")
                if partial_count == len(gate_rows):
                    gate_report["escalation_hint"] = "all_partial: add third_path or use exploratory profile for discovery stage"
        if not validation.get("valid", False):
            for row in gate_report.get("hypotheses", []) if isinstance(gate_report, dict) else []:
                if not isinstance(row, dict):
                    continue
                row["gate_status"] = "fail"
                row["reason_code"] = "invalid_evidence_pack"
                row["recovery_action"] = "repair_evidence_pack_schema_and_rerun"
            if not gate_report.get("hypotheses"):
                gate_report["hypotheses"] = [
                    {
                        "hypothesis_id": "UNKNOWN",
                        "gate_status": "fail",
                        "checks": {"schema_valid": False},
                        "reason_code": "invalid_evidence_pack",
                        "recovery_action": "repair_evidence_pack_schema_and_rerun",
                    }
                ]
        ml_repro_bundle = _build_ml_repro_bundle(session_dir, gate_report)
        if ml_repro_bundle.get("enabled", False):
            bundle_map = {
                str(item.get("hypothesis_id", "")).strip().upper(): item
                for item in ml_repro_bundle.get("hypotheses", [])
                if isinstance(item, dict)
            }
            for row in gate_report.get("hypotheses", []) if isinstance(gate_report, dict) else []:
                if not isinstance(row, dict):
                    continue
                if str(row.get("gate_rule_type", "")).strip().lower() != "predictive_performance":
                    continue
                hid = str(row.get("hypothesis_id", "")).strip().upper()
                bundle_item = bundle_map.get(hid, {})
                missing_required = (
                    bundle_item.get("missing_required", [])
                    if isinstance(bundle_item, dict) and isinstance(bundle_item.get("missing_required"), list)
                    else []
                )
                row["ml_repro_bundle"] = {
                    "bundle_dir": bundle_item.get("bundle_dir", "") if isinstance(bundle_item, dict) else "",
                    "complete": bool(bundle_item.get("complete", False)) if isinstance(bundle_item, dict) else False,
                    "missing_required": missing_required,
                }
                if missing_required:
                    row["gate_status"] = "partial" if row.get("gate_status") == "pass" else row.get("gate_status")
                    row["reason_code"] = "ml_repro_bundle_missing"
                    row["recovery_action"] = "build_ml_repro_bundle_and_rerun"
        write_json(session_dir / "result" / "hypothesis_evidence_pack.json", evidence_pack)
        write_json(session_dir / "result" / "hypothesis_gate_report.json", gate_report)
        write_json(session_dir / "result" / "hypothesis_evidence_pack_validation.json", validation)
        if ml_repro_bundle:
            write_json(session_dir / "result" / "ml_repro_bundle_index.json", ml_repro_bundle)
        current_plan_json = state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {}
        if not current_plan_json.get("hypotheses"):
            current_plan_json = _load_json_if_exists(session_dir / "plan" / "analysis_plan.json")
        current_hypothesis_payload = _load_json_if_exists(session_dir / "result" / "hypothesis_results.json")
        current_multipath_payload = _load_json_if_exists(session_dir / "result" / "hypothesis_multipath.json")
        current_path_execution_payload = _load_json_if_exists(session_dir / "result" / "path_execution_status.json")
        final_matrix = _build_final_hypothesis_matrix(
            current_plan_json,
            current_hypothesis_payload,
            current_multipath_payload,
            current_path_execution_payload,
            gate_report,
        )
        write_json(session_dir / "result" / "hypothesis_matrix.json", final_matrix)
        plan_id = state.get("plan_id", "")
        if plan_id:
            registry = ArtifactRegistry(session_dir)
            registry.register(
                plan_id,
                "result",
                session_dir / "result" / "hypothesis_evidence_pack.json",
                {"phase": "evidence_curation"},
            )
            registry.register(
                plan_id,
                "result",
                session_dir / "result" / "hypothesis_gate_report.json",
                {"phase": "evidence_curation"},
            )
            registry.register(
                plan_id,
                "result",
                session_dir / "result" / "hypothesis_evidence_pack_validation.json",
                {"phase": "evidence_curation"},
            )
            registry.register(
                plan_id,
                "result",
                session_dir / "result" / "hypothesis_matrix.json",
                {"phase": "evidence_curation", "source": "final_unified_status"},
            )
            if ml_repro_bundle:
                registry.register(
                    plan_id,
                    "result",
                    session_dir / "result" / "ml_repro_bundle_index.json",
                    {"phase": "evidence_curation"},
                )
        return {
            "hypothesis_evidence_pack": evidence_pack,
            "hypothesis_gate_report": gate_report,
            "hypothesis_evidence_pack_validation": validation,
            "ml_repro_bundle": ml_repro_bundle,
        }

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
                data_sessions_active_dir=session_dir,
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

    def pipeline_guard(state: OrchestrationState) -> OrchestrationState:
        failures = state.get("pipeline_gate_failures", []) or []
        existing_waivers = list(state.get("pipeline_gate_waivers", []) or [])
        if not failures:
            return {"pipeline_guard_ran": True, "pipeline_gate_waivers": existing_waivers}
        session_dir = Path(state.get("session_dir", ""))
        resolution = _resolve_pipeline_gate_failures(
            session_dir,
            failures,
            custom_line_records=list(state.get("custom_line_records", []) or []),
        )
        return {
            "pipeline_guard_ran": True,
            "pipeline_fallbacks": resolution["fallback_records"],
            "pipeline_gate_failures": resolution["remaining_failures"],
            "pipeline_gate_waivers": existing_waivers + resolution["waived_records"],
        }

    def artifact_validator(state: OrchestrationState) -> OrchestrationState:
        if not state.get("config", {}).get("role_guard_enabled", ROLE_GUARD_ENABLED):
            return {}
        session_dir = Path(state.get("session_dir", ""))
        report = _artifact_validation_report(session_dir)
        meta_dir = ensure_dir(session_dir / "meta")
        write_json(meta_dir / "artifact_validation.json", report)
        if report.get("missing_roles") or report.get("errors"):
            error_dir = ensure_dir(meta_dir / "artifact_validation")
            write_json(error_dir / "error.json", report)
            trace_lines = []
            for missing in report.get("missing_roles", []):
                trace_lines.append(f"missing_role: {missing}")
            for err in report.get("errors", []):
                trace_lines.append(f"error_role: {err.get('role_id')} {err.get('error')}")
            write_text(error_dir / "trace.txt", "\n".join(trace_lines))
        return {"artifact_validation": report}

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
        llm_events = list(state.get("llm_degradation_events", []) or [])
        raw = ""
        followups: list[str] = []
        try:
            raw = llm.chat(messages, max_tokens=1024)
            followups = _extract_hypotheses(raw)
        except Exception as exc:
            llm_events = _record_llm_degradation(
                state,
                node="refine_hypotheses",
                action="skip_optional_llm",
                reason=str(exc),
                impact="跳过 LLM 假设扩展，改用门槛未通过项生成后续假设建议。",
            )
            followups = _fallback_followup_hypotheses(Path(state.get("session_dir", "")))
            if followups:
                raw = "LLM 不可用，自动生成后续假设建议：\n" + "\n".join(f"- {x}" for x in followups)
            else:
                raw = "LLM 不可用，且未发现可自动扩展的后续假设。"
        followup_path = Path(state.get("session_dir", "")) / "plan" / "followup_hypotheses.md"
        write_text(followup_path, raw)
        record_artifact(state.get("session_dir", ""), followup_path, "plan", "refine_hypotheses")
        output: dict[str, Any] = {"followup_hypotheses": followups}
        if llm_events:
            output["llm_degradation_events"] = llm_events
        return output

    def decide_recurse(state: OrchestrationState) -> OrchestrationState:
        session_dir = Path(state.get("session_dir", ""))
        digest = build_research_digest(session_dir, state)
        digest_md = render_research_digest_markdown(digest)
        write_json(session_dir / "meta" / "research_digest.json", digest)
        write_text(session_dir / "meta" / "research_digest.md", digest_md)
        depth = int(state.get("depth", 1))
        write_json(session_dir / "meta" / f"research_digest_depth{depth}.json", digest)
        focus = select_depth_focus(
            digest,
            max_candidates=int(state.get("config", {}).get("depth_focus_max_candidates", 3) or 3),
        )
        write_json(session_dir / "meta" / "depth_focus_selection.json", focus)
        max_depth = int(state.get("max_depth", 0))
        depth_decision = str(state.get("depth_decision", "")).strip().lower()
        iteration_count = int(state.get("iteration_count", 1))
        max_iterations = int(state.get("config", {}).get("max_iterations", MAX_ITERATIONS))
        if iteration_count >= max_iterations:
            return {
                "should_recurse": False,
                "continuation_required": False,
                "depth_prompt": "已达到最大迭代次数，停止递归以避免死循环。",
                "research_digest": digest,
                "depth_focus_selection": focus,
            }
        gate_payload = state.get("hypothesis_gate_report", {})
        gate_rows = gate_payload.get("hypotheses", []) if isinstance(gate_payload, dict) else []
        has_incomplete_hypothesis = any(
            str(row.get("gate_status", "")).strip().lower() in {"partial", "fail"}
            for row in gate_rows
            if isinstance(row, dict)
        )
        multipath_payload = state.get("hypothesis_multipath", {})
        multipath_stats = multipath_payload.get("stats", {}) if isinstance(multipath_payload, dict) else {}
        has_conflict = float(multipath_stats.get("conflict_rate", 0.0) or 0.0) > 0.0
        has_pipeline_failures = bool(state.get("pipeline_gate_failures", []) or [])
        has_artifact_validation_errors = bool(
            (
                (state.get("artifact_validation", {}) or {}).get("missing_roles", [])
                if isinstance(state.get("artifact_validation", {}), dict)
                else []
            )
            or (
                (state.get("artifact_validation", {}) or {}).get("errors", [])
                if isinstance(state.get("artifact_validation", {}), dict)
                else []
            )
        )
        unresolved_pending = (
            has_incomplete_hypothesis
            or has_conflict
            or has_pipeline_failures
            or has_artifact_validation_errors
        )
        prioritized_followups = [
            f"{item.get('hypothesis_id')}: {item.get('title')} [{item.get('mode')}]"
            for item in focus.get("selected", [])
            if isinstance(item, dict)
        ]
        if not prioritized_followups:
            prioritized_followups = list(state.get("followup_hypotheses", []))

        controller = DepthRecursionController(
            max_depth,
            retry_limit=int(config.get("execution_failure_max_retries", EXECUTION_MAX_RETRIES)),
            force_rounds=int(state.get("config", {}).get("force_rounds", 1) or 1),
        )
        decision = controller.evaluate(
            depth,
            prioritized_followups,
            state.get("execution_retry_requested", False),
            state.get("execution_retry_exhausted", False),
            depth_decision,
            int(state.get("execution_retry_count", 0)),
            unresolved_pending=unresolved_pending and bool(focus.get("selected")),
        )
        if decision.get("forced_round") and not prioritized_followups:
            prioritized_followups = [
                f"FORCED_ROUND_{depth + 1}: 基于首轮已落盘证据执行受控的第 {depth + 1} 轮复核与补充计划。"
            ]
        if decision.get("forced_round"):
            focus = {
                **focus,
                "mode": "forced_round",
                "forced_round": True,
                "selected": focus.get("selected", []),
                "reason": "forced_rounds_requirement",
            }
            write_json(session_dir / "meta" / "depth_focus_selection.json", focus)
        decision["recursion_context"] = {
            "depth": depth,
            "iteration_count": iteration_count,
            "has_incomplete_hypothesis": has_incomplete_hypothesis,
            "has_conflict": has_conflict,
            "has_pipeline_failures": has_pipeline_failures,
            "has_artifact_validation_errors": has_artifact_validation_errors,
            "unresolved_pending": unresolved_pending,
            "followups": prioritized_followups,
            "focus_mode": focus.get("mode", "stop"),
            "focus_selection": focus,
            "forced_round": bool(decision.get("forced_round", False)),
        }
        decision["followup_hypotheses"] = prioritized_followups
        decision["research_digest"] = digest
        decision["depth_focus_selection"] = focus
        return decision

    def advance_depth(state: OrchestrationState) -> OrchestrationState:
        depth = int(state.get("depth", 1))
        iteration_count = int(state.get("iteration_count", 1))
        lineage = list(state.get("iteration_lineage", []))
        ctx = state.get("recursion_context", {})
        focus_selection = state.get("depth_focus_selection", {}) if isinstance(state.get("depth_focus_selection", {}), dict) else {}
        selected_followups = (
            [f"{item.get('hypothesis_id')}: {item.get('title')}" for item in focus_selection.get("selected", []) if isinstance(item, dict)]
            if focus_selection.get("selected")
            else (ctx.get("followups", []) if isinstance(ctx, dict) else [])
        )
        lineage.append(
            {
                "depth": depth,
                "iteration": iteration_count,
                "followups": selected_followups,
                "unresolved_pending": bool((ctx or {}).get("unresolved_pending", False)) if isinstance(ctx, dict) else False,
                "signals": {
                    "incomplete_hypothesis": bool((ctx or {}).get("has_incomplete_hypothesis", False)) if isinstance(ctx, dict) else False,
                    "conflict": bool((ctx or {}).get("has_conflict", False)) if isinstance(ctx, dict) else False,
                    "pipeline_failures": bool((ctx or {}).get("has_pipeline_failures", False)) if isinstance(ctx, dict) else False,
            "artifact_errors": bool((ctx or {}).get("has_artifact_validation_errors", False)) if isinstance(ctx, dict) else False,
                },
                "mode": (ctx.get("focus_mode", "") if isinstance(ctx, dict) else "") or focus_selection.get("mode", "stop"),
                "forced_round": bool((ctx or {}).get("forced_round", False)) if isinstance(ctx, dict) else False,
                "decision": "recurse",
            }
        )
        return {
            "depth": depth + 1,
            "iteration_count": iteration_count + 1,
            "iteration_lineage": lineage,
            "followup_hypotheses": selected_followups,
        }

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
        llm_events = list(state.get("llm_degradation_events", []) or [])
        try:
            outline = llm.chat(messages, max_tokens=2048)
        except Exception as exc:
            llm_events = _record_llm_degradation(
                state,
                node="report_outline",
                action="fallback",
                reason=str(exc),
                impact="报告大纲改用确定性结构模板，保持章节可追踪。",
            )
            outline = _fallback_report_outline(state)
        outline_path = Path(state.get("session_dir", "")) / "report" / "report_outline.md"
        write_text(outline_path, outline)
        record_artifact(state.get("session_dir", ""), outline_path, "report", "report_outline")
        if plan_id:
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "report",
                outline_path,
                "report",
                {"phase": "report_outline"},
            )
        output: dict[str, Any] = {"report_outline": outline}
        if llm_events:
            output["llm_degradation_events"] = llm_events
        return output

    def generate_report(state: OrchestrationState) -> OrchestrationState:
        outline = state.get("report_outline", "")
        analysis_text = state.get("docs_analysis_results", "")
        exec_results = state.get("exec_results", [])
        language = state.get("config", {}).get("report_language", "zh")
        report_format = state.get("config", {}).get("report_format", "html")
        export_mode = state.get("config", {}).get("report_export_mode", "html_convert")
        prompt = get_prompt("report_structured", language)
        previous_report = state.get("report", "")
        plan_id = state.get("plan_id", "")
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_context = _artifact_context(artifact_registry, plan_id) if plan_id else ""
        telemetry_context = _telemetry_context(state, artifact_registry, plan_id)
        execution_warning = ""
        if not exec_results:
            execution_warning = "执行告警：未检测到可执行脚本输出，报告可能缺少编程验证内容。"
        else:
            failed = 0
            for item in exec_results:
                statuses = item.get("statuses", [])
                if statuses and statuses[-1] == "error":
                    failed += 1
            if failed == len(exec_results):
                execution_warning = "执行告警：所有代码步骤执行失败，报告仅基于规划信息生成。"
        warning_block = f"{execution_warning}\n\n" if execution_warning else ""
        session_dir = Path(state.get("session_dir", ""))
        gate_path = session_dir / "result" / "hypothesis_gate_report.json"
        pack_validation_path = session_dir / "result" / "hypothesis_evidence_pack_validation.json"
        gate_payload: dict[str, Any] = {}
        pack_validation: dict[str, Any] = {}
        if gate_path.exists():
            try:
                gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
            except Exception:
                gate_payload = {}
        if pack_validation_path.exists():
            try:
                pack_validation = json.loads(pack_validation_path.read_text(encoding="utf-8"))
            except Exception:
                pack_validation = {}
        if not gate_payload or not pack_validation.get("valid", False):
            fail_reason = "missing_or_invalid_evidence_pack_or_gate"
            if execution_warning:
                execution_warning = execution_warning + f"\n执行门槛告警：{fail_reason}。"
            else:
                execution_warning = f"执行门槛告警：{fail_reason}。"
            warning_block = f"{execution_warning}\n\n"
        set_consistency = _build_hypothesis_set_consistency(
            session_dir,
            state.get("plan_json", {}),
            require_report_ids=False,
        )
        write_json(session_dir / "meta" / "hypothesis_set_consistency.json", set_consistency)
        if not set_consistency.get("satisfied", False):
            fail_reason = "incomplete_hypothesis_set"
            detail = _summarize_set_consistency_mismatches(set_consistency)
            if execution_warning:
                execution_warning = execution_warning + f"\n执行门槛告警：{fail_reason}。{detail}"
            else:
                execution_warning = f"执行门槛告警：{fail_reason}。{detail}"
            warning_block = f"{execution_warning}\n\n"
        completion_validation = _build_completion_validation(
            session_dir,
            gate_payload=gate_payload,
            pack_validation=pack_validation,
            artifact_validation=state.get("artifact_validation", {}),
            pipeline_gate_failures=state.get("pipeline_gate_failures", []),
            pipeline_gate_waivers=state.get("pipeline_gate_waivers", []),
            closure_status=state.get("closure_status", {}),
        )
        write_json(session_dir / "meta" / "completion_validation.json", completion_validation)
        if not completion_validation.get("complete", False):
            reason_text = ",".join(completion_validation.get("blocking_reasons", [])[:4])
            if execution_warning:
                execution_warning = execution_warning + f"\n完成态校验未通过：{reason_text}。"
            else:
                execution_warning = f"完成态校验未通过：{reason_text}。"
            warning_block = f"{execution_warning}\n\n"
        report_generation_waiver: dict[str, Any] = {}
        messages = render_role_prompt(
            "report",
            language,
            prompt_key="report_structured",
            format=report_format,
            mode=export_mode,
            outline=outline,
            analysis=f"{warning_block}{analysis_text}\n\nPrevious report:\n{previous_report}",
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
                        f"Outline:\n{outline}\n\nAnalysis:\n{warning_block}{analysis_text}\n\n"
                        f"Previous report (if any):\n{previous_report}"
                    ),
                },
            ]
        report_payload: dict[str, Any]
        llm_events = list(state.get("llm_degradation_events", []) or [])
        strict_fallback_mode = bool(state.get("config", {}).get("strict_fallback_mode", True))
        use_report_llm = bool(state.get("config", {}).get("report_use_llm", REPORT_USE_LLM))
        if (not gate_payload or not pack_validation.get("valid", False)) or not set_consistency.get("satisfied", False):
            use_report_llm = False
        if not completion_validation.get("complete", False):
            use_report_llm = False
        report_gate_ok, report_gate_reasons = _strong_fallback_report_ok(
            completion_validation,
            set_consistency,
            pack_validation,
        )
        if use_report_llm:
            try:
                report_raw = llm.chat(messages, max_tokens=4096)
                report_payload = normalize_report_payload(parse_structured_payload(report_raw))
            except Exception as exc:
                raw_reason = str(exc)
                short_reason = "report_llm_unavailable"
                low_reason = raw_reason.lower()
                if "429" in low_reason or "model_not_found" in low_reason or "rate" in low_reason:
                    short_reason = "report_model_unavailable_or_rate_limited"
                report_payload = normalize_report_payload(
                    {
                        "outline_mode": "structure_only",
                        "summary": (
                            "报告模型在装配阶段不可用，已自动切换为结构化兜底装配。"
                            "结论基于现有执行产物与证据，不使用自由文本推断。"
                        ),
                    }
                )
                execution_warning = (
                    f"{execution_warning}\n报告装配降级：{short_reason}。".strip()
                    if execution_warning
                    else f"报告装配降级：{short_reason}。"
                )
                llm_events = _record_llm_degradation(
                    {"llm_degradation_events": llm_events},
                    node="generate_report",
                    action="fallback",
                    reason=raw_reason,
                    impact="最终报告改为结构化装配，避免自由文本推断。",
                )
                write_json(
                    ensure_dir(Path(state.get("session_dir", "")) / "meta" / "plan_validation")
                    / "report_llm_fallback.json",
                    {
                        "fallback_used": True,
                        "reason": short_reason,
                        "raw_error": raw_reason,
                        "timestamp": int(time.time()),
                    },
                )
                outline = _sanitize_outline(outline, Path(state.get("session_dir", "")))
        else:
            report_payload = normalize_report_payload(
                {
                    "outline_mode": "structure_only",
                    "summary": (
                        "假设集合、证据门槛或完成态校验未通过，已中止最终结论生成，"
                        "仅保留可追溯结构化装配结果。"
                    ),
                }
            )
            outline = _sanitize_outline(outline, Path(state.get("session_dir", "")))
        if report_payload.get("outline_mode") == "structure_only" and not completion_validation.get("complete", False):
            report_generation_waiver = {
                "allow": True,
                "reason": "structured_intermediate_report_allowed",
                "derived_from": [str(x) for x in completion_validation.get("blocking_reasons", [])[:6]],
            }
        if strict_fallback_mode and _has_llm_unavailable_event(llm_events) and not report_gate_ok:
            llm_events = _record_llm_degradation(
                {"llm_degradation_events": llm_events},
                node="generate_report",
                action="skip_due_to_quality_gate",
                reason=";".join(report_gate_reasons) if report_gate_reasons else "report_gate_not_passed",
                impact="LLM 不可用且质量门槛未通过，跳过正文报告装配，仅输出跳过说明。",
            )
            report = (
                "<h1>报告已跳过生成</h1>"
                "<p>原因：当前运行处于 LLM 不可用状态，且强兜底质量门槛未通过。</p>"
                f"<p>阻塞项：{', '.join(report_gate_reasons) if report_gate_reasons else 'unknown'}。</p>"
                "<p>建议：修复阻塞项后重跑，或恢复可用模型服务后再生成完整报告。</p>"
            )
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
            write_json(
                ensure_dir(Path(state.get("session_dir", "")) / "meta" / "plan_validation")
                / "report_skipped_due_to_quality_gate.json",
                {
                    "skipped": True,
                    "reasons": report_gate_reasons,
                    "llm_unavailable": True,
                },
            )
            llm_event_summary = {
                "count": len(llm_events),
                "fallback_count": sum(1 for e in llm_events if str(e.get("action", "")).startswith("fallback")),
                "skip_count": sum(1 for e in llm_events if str(e.get("action", "")).startswith("skip")),
                "nodes": sorted(
                    list(
                        {
                            str(e.get("node", "")).strip()
                            for e in llm_events
                            if isinstance(e, dict) and str(e.get("node", "")).strip()
                        }
                    )
                ),
            }
            write_json(
                ensure_dir(Path(state.get("session_dir", "")) / "meta") / "llm_degradation_events.json",
                {"events": llm_events, "summary": llm_event_summary},
            )
            return {
                "report": report,
                "report_versions": versions,
                "completion_validation": completion_validation,
                "report_generation_waiver": {},
                "llm_degradation_events": llm_events,
            }
        llm_event_summary = {
            "count": len(llm_events),
            "fallback_count": sum(1 for e in llm_events if str(e.get("action", "")).startswith("fallback")),
            "skip_count": sum(1 for e in llm_events if str(e.get("action", "")).startswith("skip")),
            "nodes": sorted(
                list(
                    {
                        str(e.get("node", "")).strip()
                        for e in llm_events
                        if isinstance(e, dict) and str(e.get("node", "")).strip()
                    }
                )
            ),
        }
        write_json(
            ensure_dir(Path(state.get("session_dir", "")) / "meta") / "llm_degradation_events.json",
            {"events": llm_events, "summary": llm_event_summary},
        )
        current_digest = build_research_digest(session_dir, state)
        write_json(session_dir / "meta" / "research_digest.json", current_digest)
        write_text(session_dir / "meta" / "research_digest.md", render_research_digest_markdown(current_digest))
        write_json(session_dir / "meta" / f"research_digest_depth{int(state.get('depth', 1) or 1)}.json", current_digest)
        previous_digest = (
            _load_json_if_exists(session_dir / "meta" / f"research_digest_depth{int(state.get('depth', 1) or 1) - 1}.json")
            if int(state.get("depth", 1) or 1) > 1
            else {}
        )
        if previous_digest:
            depth_delta = build_depth_delta(previous_digest, current_digest, state.get("depth_focus_selection", {}))
            write_json(session_dir / "meta" / "depth_delta.json", depth_delta)
        doc_manager = DocumentManager(Path(state.get("session_dir", "")))
        document_manifest = doc_manager.manifest()
        assembler = ReportAssembler(language=language)
        report = assembler.assemble(
            outline=outline,
            analysis_md=analysis_text,
            document_manifest=document_manifest,
            report_payload=report_payload,
            execution_warning=execution_warning,
        )
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
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "report",
                report_path,
                "report",
                {"phase": "generate_report"},
            )
        return {
            "report": report,
            "report_versions": versions,
            "completion_validation": completion_validation,
            "report_generation_waiver": report_generation_waiver,
            "report_payload": report_payload,
            "report_execution_warning": execution_warning,
            "llm_degradation_events": llm_events,
        }

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
        audit = _run_audit(session_dir)
        audit["pipeline_fallbacks"] = state.get("pipeline_fallbacks", [])
        audit["pipeline_gate_waivers"] = state.get("pipeline_gate_waivers", [])
        pipeline_variants = state.get("pipeline_variants", []) if isinstance(state.get("pipeline_variants", []), list) else []
        audit["pipeline_gate_summary"] = {
            "total": len(pipeline_variants),
            "passed": sum(
                1 for row in pipeline_variants if isinstance(row, dict) and row.get("gate_status") == "pass"
            ),
            "waived": sum(
                1
                for row in pipeline_variants
                if isinstance(row, dict) and row.get("gate_status") == "waived_by_equivalent_execution"
            ),
            "failed": len(state.get("pipeline_gate_failures", []) or []),
        }
        if state.get("hypothesis_multipath"):
            audit["hypothesis_multipath"] = state.get("hypothesis_multipath", {})
        if state.get("path_adjudication"):
            audit["path_adjudication"] = state.get("path_adjudication", {})
        if state.get("ml_repro_bundle"):
            audit["ml_repro_bundle"] = state.get("ml_repro_bundle", {})
        audit["custom_lines"] = state.get("custom_line_records", [])
        audit["custom_line_summary"] = state.get("custom_line_summary", {})
        current_digest = build_research_digest(session_dir, state)
        write_json(session_dir / "meta" / "research_digest.json", current_digest)
        write_text(session_dir / "meta" / "research_digest.md", render_research_digest_markdown(current_digest))
        write_json(session_dir / "meta" / f"research_digest_depth{int(state.get('depth', 1) or 1)}.json", current_digest)
        prev_depth = int(state.get("depth", 1) or 1) - 1
        previous_digest = _load_json_if_exists(session_dir / "meta" / f"research_digest_depth{prev_depth}.json") if prev_depth >= 1 else {}
        depth_delta = (
            build_depth_delta(previous_digest, current_digest, state.get("depth_focus_selection", {}))
            if previous_digest
            else {
                "previous_depth": None,
                "current_depth": int(state.get("depth", 1) or 1),
                "material_gain": False,
                "summary": "当前为首轮分析，无上一轮可比较。",
                "selected_mode": (state.get("depth_focus_selection", {}) or {}).get("mode", ""),
                "selected_targets": [
                    row.get("hypothesis_id")
                    for row in ((state.get("depth_focus_selection", {}) or {}).get("selected", []) if isinstance(state.get("depth_focus_selection", {}), dict) else [])
                    if isinstance(row, dict)
                ],
            }
        )
        write_json(session_dir / "meta" / "depth_delta.json", depth_delta)
        summary["run_audit"] = audit
        summary["pipeline_fallbacks"] = audit["pipeline_fallbacks"]
        summary["pipeline_gate_waivers"] = audit["pipeline_gate_waivers"]
        summary["pipeline_gate_summary"] = audit["pipeline_gate_summary"]
        summary["custom_lines"] = audit["custom_lines"]
        summary["custom_line_summary"] = audit["custom_line_summary"]
        summary["path_adjudication"] = state.get("path_adjudication", {})
        summary["ml_repro_bundle"] = state.get("ml_repro_bundle", {})
        summary["research_digest"] = current_digest
        summary["depth_focus_selection"] = state.get("depth_focus_selection", {})
        summary["depth_delta"] = depth_delta
        iteration_lineage = list(state.get("iteration_lineage", []))
        if not iteration_lineage:
            iteration_lineage.append(
                {
                    "depth": int(state.get("depth", 1)),
                    "iteration": int(state.get("iteration_count", 1)),
                    "followups": state.get("followup_hypotheses", []),
                    "unresolved_pending": False,
                    "signals": {},
                    "decision": "stop",
                }
            )
        write_json(session_dir / "meta" / "iteration_lineage.json", {"iterations": iteration_lineage})
        audit["iteration_lineage"] = iteration_lineage
        quality_score = _build_analysis_quality_score(session_dir)
        quality_consistency = _quality_consistency_errors(session_dir, quality_score)
        evidence_trace = _build_evidence_trace(session_dir)
        reason_code_summary = _build_reason_code_summary(session_dir)
        hypothesis_set_consistency = _build_hypothesis_set_consistency(session_dir, state.get("plan_json", {}))
        closure_map = load_phase_closure_map(session_dir)
        completion_validation = _build_completion_validation(
            session_dir,
            gate_payload=state.get("hypothesis_gate_report", {}),
            pack_validation=state.get("hypothesis_evidence_pack_validation", {}),
            artifact_validation=state.get("artifact_validation", {}),
            pipeline_gate_failures=state.get("pipeline_gate_failures", []),
            pipeline_gate_waivers=state.get("pipeline_gate_waivers", []),
            closure_status=closure_map,
            expect_report=True,
        )
        generate_report_closure = (
            closure_map.get("generate_report", {})
            if isinstance(closure_map.get("generate_report", {}), dict)
            else {}
        )
        if completion_validation.get("complete", False) and generate_report_closure:
            notes = (
                [
                    str(item).strip()
                    for item in generate_report_closure.get("notes", [])
                    if str(item).strip() and str(item).strip() != "report_generated_with_explicit_waiver"
                ]
                if isinstance(generate_report_closure.get("notes", []), list)
                else []
            )
            normalized_report_closure = dict(generate_report_closure)
            normalized_report_closure["notes"] = notes
            normalized_report_closure["waiver_reason"] = ""
            normalized_report_closure["derived_from"] = []
            closure_map["generate_report"] = normalized_report_closure
            write_json(session_dir / "meta" / "closure_status" / "generate_report.json", normalized_report_closure)
        audit["analysis_quality_score"] = quality_score
        audit["quality_consistency"] = quality_consistency
        audit["hypothesis_set_consistency"] = hypothesis_set_consistency
        audit["closure_status"] = closure_map
        audit["phase_blockers"] = state.get("phase_blockers", {}) or build_phase_blockers(audit["closure_status"])
        audit["recovery_trace"] = state.get("recovery_trace", [])
        audit["research_digest"] = current_digest
        audit["depth_focus_selection"] = state.get("depth_focus_selection", {})
        audit["depth_delta"] = depth_delta
        audit["completion_validation"] = completion_validation
        write_json(session_dir / "meta" / "run_audit.json", audit)
        write_json(session_dir / "meta" / "analysis_quality_score.json", quality_score)
        write_json(session_dir / "meta" / "quality_consistency_errors.json", quality_consistency)
        write_json(session_dir / "meta" / "hypothesis_set_consistency.json", hypothesis_set_consistency)
        write_json(session_dir / "meta" / "completion_validation.json", completion_validation)
        write_json(session_dir / "meta" / "evidence_trace.json", evidence_trace)
        write_json(session_dir / "meta" / "reason_code_summary.json", reason_code_summary)
        llm_events = list(state.get("llm_degradation_events", []) or [])
        llm_event_summary = {
            "count": len(llm_events),
            "fallback_count": sum(1 for e in llm_events if str(e.get("action", "")).startswith("fallback")),
            "skip_count": sum(1 for e in llm_events if str(e.get("action", "")).startswith("skip")),
            "nodes": sorted(
                list(
                    {
                        str(e.get("node", "")).strip()
                        for e in llm_events
                        if isinstance(e, dict) and str(e.get("node", "")).strip()
                    }
                )
            ),
        }
        audit["llm_degradation"] = llm_event_summary
        audit["llm_degradation_events"] = llm_events
        write_json(
            session_dir / "meta" / "llm_degradation_events.json",
            {"events": llm_events, "summary": llm_event_summary},
        )
        write_json(session_dir / "meta" / "run_audit.json", audit)
        summary["analysis_quality_score"] = quality_score
        summary["quality_consistency"] = quality_consistency
        summary["hypothesis_set_consistency"] = hypothesis_set_consistency
        summary["closure_status"] = audit["closure_status"]
        summary["phase_blockers"] = audit["phase_blockers"]
        summary["recovery_trace"] = audit["recovery_trace"]
        summary["research_digest"] = audit["research_digest"]
        summary["depth_focus_selection"] = audit["depth_focus_selection"]
        summary["depth_delta"] = audit["depth_delta"]
        summary["completion_validation"] = completion_validation
        summary["iteration_lineage"] = iteration_lineage
        summary["evidence_trace"] = evidence_trace
        summary["reason_code_summary"] = reason_code_summary
        summary["llm_degradation"] = llm_event_summary
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
        latest_report_path = ""
        report_versions = state.get("report_versions", [])
        if isinstance(report_versions, list) and report_versions:
            latest_report_path = str(report_versions[-1]).strip()
        report_payload = state.get("report_payload", {}) if isinstance(state.get("report_payload", {}), dict) else {}
        if latest_report_path and report_payload:
            report_path = Path(latest_report_path)
            if report_path.exists():
                try:
                    assembler = ReportAssembler(language=config.get("language", "zh"))
                    regenerated_report = assembler.assemble(
                        outline=str(state.get("report_outline", "") or ""),
                        analysis_md=str(state.get("docs_analysis_results", "") or ""),
                        document_manifest=document_manifest,
                        report_payload=report_payload,
                        execution_warning=str(state.get("report_execution_warning", "") or ""),
                    )
                    write_text(report_path, regenerated_report)
                except Exception:
                    pass
        return {"run_summary": summary, "document_manifest": document_manifest}

    graph.add_node("understand_files", _run_node("understand_files", understand_files, config))
    graph.add_node("data_quality", _run_node("data_quality", data_quality, config))
    graph.add_node("plan_visualizations", _run_node("plan_visualizations", plan_visualizations, config))
    graph.add_node("plan_analysis", _run_node("plan_analysis", plan_analysis, config))
    graph.add_node("parallel_generation", _run_node("parallel_generation", parallel_generation, config))
    graph.add_node("execution_guard", _run_node("execution_guard", execution_guard, config))
    graph.add_node("code_repair", _run_node("code_repair", code_repair, config))
    graph.add_node("analyze_results", _run_node("analyze_results", analyze_results, config))
    graph.add_node("evidence_curation", _run_node("evidence_curation", evidence_curation, config))
    graph.add_node("pipeline_guard", _run_node("pipeline_guard", pipeline_guard, config))
    graph.add_node("artifact_validator", _run_node("artifact_validator", artifact_validator, config))
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
    def _exec_next(s: OrchestrationState) -> str:
        if s.get("execution_retry_requested"):
            if not s.get("config", {}).get("role_guard_enabled", ROLE_GUARD_ENABLED):
                return "plan"
            return "repair"
        return "continue"

    graph.add_conditional_edges(
        "execution_guard",
        _exec_next,
        {"repair": "code_repair", "plan": "plan_analysis", "continue": "analyze_results"},
    )
    graph.add_edge("code_repair", "analyze_results")
    graph.add_edge("analyze_results", "evidence_curation")

    def _evidence_next(s: OrchestrationState) -> str:
        closure = (
            (s.get("closure_status", {}) or {}).get("evidence_curation", {})
            if isinstance(s.get("closure_status", {}), dict)
            else {}
        )
        status = str((closure or {}).get("status", "")).strip().lower()
        retry_count = int(((s.get("phase_retry_counts", {}) or {}).get("evidence_curation", 0)) or 0)
        if status == "recoverable_failed" and retry_count <= 1:
            return "repair"
        return "continue"

    graph.add_conditional_edges(
        "evidence_curation",
        _evidence_next,
        {"repair": "analyze_results", "continue": "pipeline_guard"},
    )
    graph.add_edge("pipeline_guard", "generate_visualizations")
    def _visual_next(s: OrchestrationState) -> str:
        closure = (
            (s.get("closure_status", {}) or {}).get("generate_visualizations", {})
            if isinstance(s.get("closure_status", {}), dict)
            else {}
        )
        status = str((closure or {}).get("status", "")).strip().lower()
        retry_count = int(((s.get("phase_retry_counts", {}) or {}).get("generate_visualizations", 0)) or 0)
        if status == "recoverable_failed" and retry_count <= 1:
            return "repair"
        return "continue"

    graph.add_conditional_edges(
        "generate_visualizations",
        _visual_next,
        {"repair": "generate_visualizations", "continue": "artifact_validator"},
    )
    graph.add_edge("artifact_validator", "refine_hypotheses")
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


def build_graph(llm: LLMClient, config: dict[str, Any]):
    return create_graph(llm, config)


__all__ = ["create_graph", "build_graph"]
