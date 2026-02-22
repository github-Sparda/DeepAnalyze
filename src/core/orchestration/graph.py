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
    load_feature_dictionary,
    load_method_dictionary,
    load_metric_dictionary,
    validate_hypothesis_evidence_pack,
)
from .state import OrchestrationState
from .document_manager import DocumentManager
from .hypothesis_engine import (
    _build_auto_analysis_payload,
    _build_coverage_report,
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


def _extract_json_candidates(raw: str) -> list[str]:
    if not raw:
        return []
    candidates: list[str] = []
    fence = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    for match in fence.findall(raw):
        candidates.append(match.strip())
    obj_match = re.search(r"(\{[\s\S]*\})", raw)
    if obj_match:
        candidates.append(obj_match.group(1))
    arr_match = re.search(r"(\[[\s\S]*\])", raw)
    if arr_match:
        candidates.append(arr_match.group(1))
    return candidates


def _safe_json_any(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        pass
    for candidate in _extract_json_candidates(raw):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return {}


def _safe_json_load(raw: str) -> dict[str, Any]:
    payload = _safe_json_any(raw)
    return payload if isinstance(payload, dict) else {}


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


def _normalize_plan_json(plan_json: dict[str, Any], plan_md: str) -> dict[str, Any]:
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
        normalized.append(
            {
                "id": hyp_id,
                "title": title,
                "hypothesis": hypothesis_text,
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
            }
        )
    return {"hypotheses": normalized}


def _infer_method_family(hyp_id: str, title: str, hypothesis_text: str, index: int) -> str:
    haystack = f"{hyp_id} {title} {hypothesis_text}".lower()
    path_kind = "primary" if index == 0 else "secondary"
    if any(key in haystack for key in ("差异", "differ", "显著", "p值", "q值")):
        return "parametric_test" if path_kind == "primary" else "nonparametric_or_fdr"
    if any(key in haystack for key in ("特征", "预测", "模型", "auc", "分类")):
        return "feature_modeling" if path_kind == "primary" else "cross_validation"
    if any(key in haystack for key in ("相关", "网络", "协同", "corr")):
        return "pearson_network" if path_kind == "primary" else "rank_or_sparse_network"
    if any(key in haystack for key in ("聚类", "降维", "pca", "tsne", "umap")):
        return "pca_cluster" if path_kind == "primary" else "tsne_or_umap_cluster"
    return "primary" if index == 0 else "secondary"


def _default_validation_paths(
    hyp_id: str,
    steps: list[str],
    artifacts: list[str],
    title: str,
    hypothesis_text: str,
) -> list[dict[str, Any]]:
    return [
        {
            "path_id": "path_a",
            "method_family": _infer_method_family(hyp_id, title, hypothesis_text, 0),
            "steps": steps,
            "expected_artifacts": artifacts,
        },
        {
            "path_id": "path_b",
            "method_family": _infer_method_family(hyp_id, title, hypothesis_text, 1),
            "steps": list(reversed(steps)) if len(steps) > 1 else steps,
            "expected_artifacts": artifacts,
        },
    ]


def _strict_markdown_hypothesis_fallback(plan_md: str) -> dict[str, Any]:
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
        title = f"{hid}: hypothesis"
        steps = [str(x).strip() for x in step_map.get(hid, []) if str(x).strip()]
        artifacts, invalid = _sanitize_expected_artifacts(artifact_map.get(hid, []))
        hypotheses.append(
            {
                "id": hid,
                "title": title,
                "hypothesis": hypothesis_text.strip(),
                "validation_plan_steps": steps,
                "expected_artifacts": artifacts,
                "invalid_expected_artifacts": invalid,
                "minimum_evidence_requirements": {
                    "quant_metrics_min": 2,
                    "require_significance_metric": True,
                    "require_effect_metric": True,
                },
                "assumption_checks": ["data_quality_ready", "group_definition_valid"],
                "validation_paths": _default_validation_paths(hid, steps, artifacts, title, hypothesis_text.strip()),
                "steps": steps,
                "artifacts": artifacts,
            }
        )
    return {"hypotheses": hypotheses}


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
        missing = []
        for artifact in variant.required_artifacts:
            if not (Path(session_dir) / "result" / artifact).exists() and not (
                Path(session_dir) / "plots" / artifact
            ).exists():
                missing.append(artifact)
        gate_missing = _check_quality_gates(Path(session_dir), variant.quality_gates)
        executed.append(
            {
                "pipeline_id": scored.pipeline_id,
                "variant_id": variant.variant_id,
                "required_artifacts": list(variant.required_artifacts),
                "quality_gates": list(variant.quality_gates),
                "missing_artifacts": missing + gate_missing,
                "fallback_variant": variant.fallback_variant,
            }
        )
        if missing or gate_missing:
            failures.append(
                {
                    "pipeline_id": scored.pipeline_id,
                    "variant_id": variant.variant_id,
                    "missing": missing + gate_missing,
                    "fallback_variant": variant.fallback_variant,
                }
            )
    return executed, failures, custom_records


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


def _fallback_analysis_code() -> str:
    return (
        "import json\n"
        "from pathlib import Path\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "\n"
        "workspace = Path.cwd()\n"
        "input_files = list(workspace.glob('*.xlsx')) + list(workspace.glob('*.csv')) + list(workspace.glob('*.tsv'))\n"
        "if not input_files:\n"
        "    raise SystemExit('No input data file found in workspace')\n"
        "data_path = input_files[0]\n"
        "if data_path.suffix.lower() == '.xlsx':\n"
        "    df = pd.read_excel(data_path)\n"
        "elif data_path.suffix.lower() == '.tsv':\n"
        "    df = pd.read_csv(data_path, sep='\\t')\n"
        "else:\n"
        "    df = pd.read_csv(data_path)\n"
        "\n"
        "result_dir = workspace / 'result'\n"
        "charts_dir = workspace / 'charts'\n"
        "result_dir.mkdir(parents=True, exist_ok=True)\n"
        "charts_dir.mkdir(parents=True, exist_ok=True)\n"
        "\n"
        "summary = {\n"
        "    'rows': int(df.shape[0]),\n"
        "    'columns': int(df.shape[1]),\n"
        "    'columns_list': df.columns.tolist(),\n"
        "    'missing_total': int(df.isna().sum().sum()),\n"
        "}\n"
        "(result_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')\n"
        "\n"
        "numeric_cols = df.select_dtypes(include='number').columns\n"
        "if len(numeric_cols) > 0:\n"
        "    desc = df[numeric_cols].describe().T\n"
        "    desc.to_csv(result_dir / 'numeric_summary.csv')\n"
        "    corr = df[numeric_cols].corr()\n"
        "    corr.to_csv(result_dir / 'correlation.csv')\n"
        "\n"
        "group_col = None\n"
        "for candidate in ['Group', 'group', 'label', 'Label']:\n"
        "    if candidate in df.columns:\n"
        "        group_col = candidate\n"
        "        break\n"
        "if group_col and len(numeric_cols) > 0:\n"
        "    grouped = df.groupby(group_col)[numeric_cols].mean()\n"
        "    grouped.to_csv(result_dir / 'group_means.csv')\n"
        "\n"
        "if len(numeric_cols) > 0:\n"
        "    fig, ax = plt.subplots(figsize=(8, 4))\n"
        "    col = numeric_cols[0]\n"
        "    df[col].dropna().hist(ax=ax, bins=30, color='#4C78A8')\n"
        "    ax.set_title(f'Distribution of {col}')\n"
        "    fig.tight_layout()\n"
        "    fig.savefig(charts_dir / 'distribution.png', dpi=200)\n"
        "    plt.close(fig)\n"
    )


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
    required = [
        "result/analysis_results.md",
        "result/stats_results.json",
        "result/correlation.json",
        "result/feature_selection.json",
        "result/hypothesis_evidence.json",
        "result/hypothesis_evidence_pack.json",
        "result/hypothesis_evidence_pack_validation.json",
        "result/hypothesis_contrast.json",
        "result/hypothesis_multipath.json",
        "result/hypothesis_validation_contract.json",
        "result/hypothesis_gate_report.json",
        "result/expected_artifact_validation.json",
        "result/hypothesis_matrix.json",
        "result/coverage_report.json",
        "result/visual_binding.json",
        "result/model_eval.json",
        "result/cv_results.json",
        "report/report_v1.html",
    ]
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
    closure_rate = 0.0
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            rows = contract.get("hypotheses", []) if isinstance(contract, dict) else []
            if rows:
                closed = sum(1 for row in rows if str(row.get("executed_status", "")) in {"validated", "partial", "inconclusive", "failed"})
                closure_rate = round(closed / len(rows), 4)
        except Exception:
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


def _check_quality_gates(session_dir: Path, gates: list[str]) -> list[str]:
    missing: list[str] = []
    for gate in gates:
        target = gate
        location = "any"
        if ":" in gate:
            location, target = gate.split(":", 1)
        target = target.strip()
        if not target:
            continue
        if location == "result":
            if not (session_dir / "result" / target).exists():
                missing.append(gate)
        elif location == "plots":
            if not (session_dir / "plots" / target).exists():
                missing.append(gate)
        elif location == "report":
            if not (session_dir / "report" / target).exists():
                missing.append(gate)
        else:
            if not (session_dir / "result" / target).exists() and not (
                session_dir / "plots" / target
            ).exists():
                missing.append(gate)
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
        "ReportAssembly",
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
        seen_roles = {entry.get("role_id") for entry in manifest if entry.get("role_id")}
        report["missing_roles"] = [r for r in required_roles if r not in seen_roles]
        report["errors"] = [entry for entry in manifest if entry.get("status") == "error"]
    else:
        report["missing_roles"] = required_roles
    return report


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

    base = set(plan_ids)
    checks = {
        "plan_ids": plan_ids,
        "results_ids": results_ids,
        "multipath_ids": multipath_ids,
        "evidence_pack_ids": evidence_ids,
        "gate_ids": gate_ids,
        "report_ids": report_ids,
    }
    mismatches: dict[str, Any] = {}
    for name, ids in checks.items():
        if name == "plan_ids":
            continue
        if name == "report_ids" and not require_report_ids:
            continue
        current = set(ids)
        extra = sorted(current - base)
        missing = sorted(base - current)
        if extra or missing:
            mismatches[name] = {"missing_from_current": missing, "extra_in_current": extra}
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
        "satisfied": not mismatches and bool(plan_ids),
        "checks": checks,
        "mismatches": mismatches,
        "repair": repair,
        "reason": "" if not mismatches else "incomplete_hypothesis_set",
    }


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
    normalized = _normalize_plan_json(plan_json if isinstance(plan_json, dict) else {}, plan_md)
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
        return {"file_summary": summary, "iteration_count": int(state.get("iteration_count", 0)) or 1}

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
        history = list(state.get("docs_analysis_history", []) or [])
        followups = list(state.get("followup_hypotheses", []) or [])
        if followups:
            history.append("Follow-up hypotheses:\n" + "\n".join(f"- {h}" for h in followups))
        plan = planner.plan(
            summary,
            history,
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
        raw_plan_json = _safe_json_load(plan_json_raw)
        plan_json = _normalize_plan_json(raw_plan_json, plan)
        upgrade_preview = _upgrade_plan_schema_preview(raw_plan_json, plan)
        error_dir = ensure_dir(Path(state.get("session_dir", "")) / "meta" / "plan_validation")
        write_json(error_dir / "upgrade_preview.json", upgrade_preview)
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
        valid_plan, plan_errors = _validate_plan_json_contract(plan_json)
        if not valid_plan:
            # strict fallback: extract only explicit H1/H2/... hypothesis statements from markdown
            plan_json = _strict_markdown_hypothesis_fallback(plan)
            valid_plan, plan_errors = _validate_plan_json_contract(plan_json)
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
        if plan_errors:
            write_json(
                error_dir / "errors.json",
                {
                    "errors": plan_errors,
                    "valid": valid_plan,
                    "suggestions": _plan_validation_suggestions(plan_errors),
                },
            )
        expected_validation_rows: list[dict[str, Any]] = []
        for hyp in plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []:
            if not isinstance(hyp, dict):
                continue
            hid = str(hyp.get("id", ""))
            expected = hyp.get("expected_artifacts", []) if isinstance(hyp.get("expected_artifacts"), list) else []
            invalid = hyp.get("invalid_expected_artifacts", []) if isinstance(hyp.get("invalid_expected_artifacts"), list) else []
            expected_validation_rows.append(
                {
                    "hypothesis_id": hid,
                    "valid_count": len(expected),
                    "invalid_count": len(invalid),
                    "invalid_items": invalid,
                }
            )
        write_json(
            Path(state.get("session_dir", "")) / "result" / "expected_artifact_validation.json",
            {"hypotheses": expected_validation_rows, "valid": all(r["invalid_count"] == 0 for r in expected_validation_rows)},
        )
        plan_json_path = Path(state.get("session_dir", "")) / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state.get("session_dir", ""), plan_json_path, "plan", "plan_analysis")
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
        errors: list[str] = []

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
        if not recorded:
            fallback_entry = {
                "name": "analysis_step",
                "filename": "analysis_step.py",
                "code": _fallback_analysis_code(),
            }
            recorded = [orchestrator._write_code(fallback_entry)]
        valid_codegen, code_errors = _validate_codegen_steps(recorded)
        if not valid_codegen:
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
        return {
            "execution_retry_requested": requested,
            "execution_retry_count": next_retry,
            "execution_retry_exhausted": exhausted,
            "execution_errors": failures,
            "rollback_performed": requested,
        }

    def code_repair(state: OrchestrationState) -> OrchestrationState:
        if not state.get("config", {}).get("role_guard_enabled", ROLE_GUARD_ENABLED):
            return {}
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
                            write_json(session_dir / "result" / "hypothesis_results.json", hypothesis_payload)
                    evidence_payload = _build_hypothesis_evidence(
                        session_dir,
                        hypothesis_payload,
                        set(plan_ids) if plan_ids else None,
                    )
                    write_json(session_dir / "result" / "hypothesis_evidence.json", evidence_payload)
                    contrast_payload = _build_hypothesis_contrast(evidence_payload, session_dir)
                    write_json(session_dir / "result" / "hypothesis_contrast.json", contrast_payload)
                    multipath_payload = _evaluate_hypothesis_validation_paths(
                        session_dir,
                        state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {},
                        evidence_payload,
                        contrast_payload,
                    )
                    write_json(session_dir / "result" / "hypothesis_multipath.json", multipath_payload)
                    contract_payload = _build_hypothesis_validation_contract(
                        state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {},
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
                    hypothesis_md = _hypothesis_summary_md(hypothesis_payload, session_dir)
                    auto_evidence = _collect_result_evidence(session_dir)
                except Exception:
                    pass
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
        return {
            "docs_analysis_results": analysis_text,
            "docs_analysis_history": history,
            "errors": errors,
            "pipeline_variants": executed if "executed" in locals() else [],
            "pipeline_gate_failures": failures if "failures" in locals() else [],
            "custom_line_records": custom_records if "custom_records" in locals() else [],
            "custom_line_summary": summary_payload,
            "hypothesis_multipath": multipath_payload if "multipath_payload" in locals() else {},
        }

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
        if conflict_rate > 0.3:
            dynamic_overrides.update(
                {
                    "significance_count_min": 2.0,
                    "primary_performance_min": max(0.65, float(dynamic_overrides.get("primary_performance_min", 0.6))),
                    "secondary_performance_min": max(0.62, float(dynamic_overrides.get("secondary_performance_min", 0.6))),
                }
            )
            calibration_context["high_conflict_adjustment"] = True
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
        write_json(session_dir / "result" / "hypothesis_evidence_pack.json", evidence_pack)
        write_json(session_dir / "result" / "hypothesis_gate_report.json", gate_report)
        write_json(session_dir / "result" / "hypothesis_evidence_pack_validation.json", validation)
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
        return {
            "hypothesis_evidence_pack": evidence_pack,
            "hypothesis_gate_report": gate_report,
            "hypothesis_evidence_pack_validation": validation,
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
        if not failures:
            return {}
        session_dir = Path(state.get("session_dir", ""))
        dataset_path = _find_first_dataset(session_dir)
        if dataset_path is None:
            return {}
        from src.core.analytics.toolkit.pipelines import pipeline_registry

        registry = pipeline_registry()
        fallback_records: list[dict[str, Any]] = []
        for failure in failures:
            pipeline_id = failure.get("pipeline_id")
            fallback_id = failure.get("fallback_variant")
            if not (pipeline_id and fallback_id):
                continue
            spec = registry.get(pipeline_id)
            if not spec:
                continue
            for variant in spec.variants:
                if variant.variant_id == fallback_id:
                    for step in variant.steps:
                        run_step(step.name, dataset_path, session_dir, method=step.method)
                    fallback_records.append(
                        {
                            "pipeline_id": pipeline_id,
                            "fallback_variant": fallback_id,
                            "reason": failure.get("missing", []),
                        }
                    )
                    break
        return {"pipeline_guard_ran": True, "pipeline_fallbacks": fallback_records}

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
        iteration_count = int(state.get("iteration_count", 1))
        max_iterations = int(state.get("config", {}).get("max_iterations", MAX_ITERATIONS))
        if iteration_count >= max_iterations:
            return {
                "should_recurse": False,
                "continuation_required": False,
                "depth_prompt": "已达到最大迭代次数，停止递归以避免死循环。",
            }
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
        iteration_count = int(state.get("iteration_count", 1))
        return {"depth": depth + 1, "iteration_count": iteration_count + 1}

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
            _register_plan_artifact(
                artifact_registry,
                state.get("session_dir", ""),
                plan_id,
                "report",
                outline_path,
                "report",
                {"phase": "report_outline"},
            )
        return {"report_outline": outline}

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
            detail = json.dumps(set_consistency.get("mismatches", {}), ensure_ascii=False)
            if execution_warning:
                execution_warning = execution_warning + f"\n执行门槛告警：{fail_reason}。{detail}"
            else:
                execution_warning = f"执行门槛告警：{fail_reason}。{detail}"
            warning_block = f"{execution_warning}\n\n"
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
        use_report_llm = bool(state.get("config", {}).get("report_use_llm", REPORT_USE_LLM))
        if (not gate_payload or not pack_validation.get("valid", False)) or not set_consistency.get("satisfied", False):
            use_report_llm = False
        if use_report_llm:
            report_raw = llm.chat(messages, max_tokens=4096)
            report_payload = normalize_report_payload(parse_structured_payload(report_raw))
        else:
            report_payload = normalize_report_payload(
                {
                    "outline_mode": "structure_only",
                    "summary": "假设集合或证据门槛未通过校验，已中止最终结论生成，仅保留可追溯结构化装配结果。",
                }
            )
            outline = _sanitize_outline(outline, Path(state.get("session_dir", "")))
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
        audit = _run_audit(session_dir)
        audit["pipeline_fallbacks"] = state.get("pipeline_fallbacks", [])
        if state.get("hypothesis_multipath"):
            audit["hypothesis_multipath"] = state.get("hypothesis_multipath", {})
        audit["custom_lines"] = state.get("custom_line_records", [])
        audit["custom_line_summary"] = state.get("custom_line_summary", {})
        summary["run_audit"] = audit
        summary["pipeline_fallbacks"] = audit["pipeline_fallbacks"]
        summary["custom_lines"] = audit["custom_lines"]
        summary["custom_line_summary"] = audit["custom_line_summary"]
        quality_score = _build_analysis_quality_score(session_dir)
        quality_consistency = _quality_consistency_errors(session_dir, quality_score)
        evidence_trace = _build_evidence_trace(session_dir)
        reason_code_summary = _build_reason_code_summary(session_dir)
        hypothesis_set_consistency = _build_hypothesis_set_consistency(session_dir, state.get("plan_json", {}))
        audit["analysis_quality_score"] = quality_score
        audit["quality_consistency"] = quality_consistency
        audit["hypothesis_set_consistency"] = hypothesis_set_consistency
        write_json(session_dir / "meta" / "run_audit.json", audit)
        write_json(session_dir / "meta" / "analysis_quality_score.json", quality_score)
        write_json(session_dir / "meta" / "quality_consistency_errors.json", quality_consistency)
        write_json(session_dir / "meta" / "hypothesis_set_consistency.json", hypothesis_set_consistency)
        write_json(session_dir / "meta" / "evidence_trace.json", evidence_trace)
        write_json(session_dir / "meta" / "reason_code_summary.json", reason_code_summary)
        summary["analysis_quality_score"] = quality_score
        summary["quality_consistency"] = quality_consistency
        summary["hypothesis_set_consistency"] = hypothesis_set_consistency
        summary["evidence_trace"] = evidence_trace
        summary["reason_code_summary"] = reason_code_summary
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
    graph.add_edge("evidence_curation", "pipeline_guard")
    graph.add_edge("pipeline_guard", "generate_visualizations")
    graph.add_edge("generate_visualizations", "artifact_validator")
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
