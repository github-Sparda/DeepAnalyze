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
from .state import OrchestrationState
from .document_manager import DocumentManager


def _extract_json_candidates(raw: str) -> list[str]:
    if not raw:
        return []
    candidates: list[str] = []
    fence = re.compile(r"```(?:json)?\\s*([\\s\\S]*?)```", re.IGNORECASE)
    for match in fence.findall(raw):
        candidates.append(match.strip())
    obj_match = re.search(r"(\\{[\\s\\S]*\\})", raw)
    if obj_match:
        candidates.append(obj_match.group(1))
    arr_match = re.search(r"(\\[[\\s\\S]*\\])", raw)
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
        if "分析步骤" in stripped or "analysis steps" in stripped.lower():
            section = "steps"
            continue
        if "预期产物" in stripped or "expected artifacts" in stripped.lower():
            section = "artifacts"
            continue
        step_match = re.match(r"^(\\d+)[\\.、\\)]\\s*(.+)", stripped)
        if step_match and section == "steps":
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
    for path in session_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in {".csv", ".tsv", ".xlsx", ".xls", ".json"}:
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


def _run_deterministic_hypotheses(session_dir: Path, dataset_path: Path) -> dict[str, Any]:
    def _record_tool_role(role_id: str, step_name: str, result: dict[str, Any], artifacts: list[str]) -> None:
        status = result.get("status", "ok")
        record_role_output(
            session_dir,
            role_id,
            status,
            output={step_name: result},
            artifacts=artifacts,
        )
    def _run_step_with_retry(module_name: str, input_path: Path, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(EXECUTION_MAX_RETRIES + 1):
            try:
                return run_step(module_name, input_path, session_dir, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive
                last_error = exc
                if attempt >= EXECUTION_MAX_RETRIES:
                    break
                time.sleep(0.1)
        error_dir = ensure_dir(session_dir / "result" / "errors")
        write_json(
            error_dir / f"{module_name}.json",
            {"module": module_name, "error": str(last_error) if last_error else "unknown"},
        )
        return {"module": module_name, "status": "error", "message": str(last_error) if last_error else "unknown"}

    def _build_stats_summary(top_k: int = 10) -> dict[str, Any]:
        stats_path = session_dir / "result" / "stats_results.json"
        if not stats_path.exists():
            return {"module": "stats_summary", "status": "skipped", "message": "stats_results.json missing"}
        try:
            stats_df = pd.read_json(stats_path)
        except Exception as exc:
            return {"module": "stats_summary", "status": "error", "message": str(exc)}
        mt_path = session_dir / "result" / "multiple_testing.json"
        if mt_path.exists():
            try:
                mt_df = pd.read_json(mt_path)
                if "q_value" in mt_df.columns:
                    stats_df = stats_df.merge(mt_df[["feature", "q_value"]], on="feature", how="left")
            except Exception:
                pass
        out_dir = ensure_dir(session_dir / "result")
        stats_df.to_json(out_dir / "stats_summary.json", orient="records", force_ascii=False)
        stats_df.to_csv(out_dir / "stats_summary.csv", index=False)
        sort_col = "q_value" if "q_value" in stats_df.columns else "p_value"
        top_df = stats_df.sort_values(sort_col).head(top_k)
        top_df.to_json(out_dir / "top_features.json", orient="records", force_ascii=False)
        top_df.to_csv(out_dir / "top_features.csv", index=False)
        return {"module": "stats_summary", "status": "ok", "output": str(out_dir / "stats_summary.json")}

    results: list[dict[str, Any]] = []
    def _check_artifacts(expected: list[str]) -> list[str]:
        missing: list[str] = []
        for artifact in expected:
            if not (session_dir / "result" / artifact).exists() and not (
                session_dir / "plots" / artifact
            ).exists():
                missing.append(artifact)
        return missing

    # H1: differential testing
    h1_steps: dict[str, dict[str, Any]] = {}
    h1_steps["stats_tests"] = _run_step_with_retry("stats_tests", dataset_path, method="t_test")
    _record_tool_role("StatsTesting", "stats_tests", h1_steps["stats_tests"], ["result/stats_results.json"])
    stats_path = session_dir / "result" / "stats_results.json"
    h1_steps["multiple_testing"] = _run_step_with_retry(
        "multiple_testing", stats_path if stats_path.exists() else dataset_path, pval_field="p_value"
    )
    _record_tool_role("StatsTesting", "multiple_testing", h1_steps["multiple_testing"], ["result/multiple_testing.json"])
    h1_steps["stats_summary"] = _build_stats_summary()
    _record_tool_role(
        "StatsTesting",
        "stats_summary",
        h1_steps["stats_summary"],
        ["result/stats_summary.json", "result/top_features.json"],
    )
    h1_steps["viz_volcano"] = _run_step_with_retry("viz_manhattan_volcano", stats_path, mode="volcano")
    _record_tool_role("Visualization", "viz_volcano", h1_steps["viz_volcano"], ["plots/volcano_plot.png"])
    top_features_path = session_dir / "result" / "top_features.json"
    if top_features_path.exists():
        h1_steps["viz_top_features"] = _run_step_with_retry("viz_top_features", top_features_path)
        _record_tool_role(
            "Visualization",
            "viz_top_features",
            h1_steps["viz_top_features"],
            ["plots/top_features_bar.png"],
        )
    h1_expected = ["stats_results.json", "multiple_testing.json", "stats_summary.json", "top_features.json"]
    results.append(
        {
            "hypothesis": "H1: 差异检验",
            "expected_artifacts": h1_expected,
            "missing": _check_artifacts(h1_expected),
            "steps": h1_steps,
        }
    )

    # H2: feature selection with rationale
    h2_steps: dict[str, dict[str, Any]] = {}
    h2_steps["feature_selection"] = _run_step_with_retry("feature_selection", dataset_path, method="p_value")
    _record_tool_role(
        "FeatureEngineering",
        "feature_selection",
        h2_steps["feature_selection"],
        ["result/feature_selection.json", "result/feature_selection_rationale.json"],
    )
    h2_expected = ["feature_selection.json", "feature_selection_rationale.json"]
    results.append(
        {
            "hypothesis": "H2: 关键特征筛选",
            "expected_artifacts": h2_expected,
            "missing": _check_artifacts(h2_expected),
            "steps": h2_steps,
        }
    )

    # H3: correlation + network
    h3_steps: dict[str, dict[str, Any]] = {}
    h3_steps["correlation"] = _run_step_with_retry("correlation", dataset_path, method="pearson")
    _record_tool_role("StatsTesting", "correlation", h3_steps["correlation"], ["result/correlation.json"])
    corr_path = session_dir / "result" / "correlation.csv"
    if corr_path.exists():
        h3_steps["viz_heatmap"] = _run_step_with_retry("viz_heatmap_cluster", corr_path, mode="heatmap")
        _record_tool_role("Visualization", "viz_heatmap", h3_steps["viz_heatmap"], ["plots/heatmap.png"])
    h3_steps["viz_network"] = _run_step_with_retry("viz_network", dataset_path, mode="network")
    _record_tool_role("Visualization", "viz_network", h3_steps["viz_network"], ["plots/network.png"])
    h3_expected = ["correlation.json", "network.png"]
    results.append(
        {
            "hypothesis": "H3: 相关性结构",
            "expected_artifacts": h3_expected,
            "missing": _check_artifacts(h3_expected),
            "steps": h3_steps,
        }
    )

    # H4: dimensionality + clustering + scatter
    h4_steps: dict[str, dict[str, Any]] = {}
    h4_steps["dimensionality"] = _run_step_with_retry("dimensionality", dataset_path, method="pca")
    _record_tool_role("Modeling", "dimensionality", h4_steps["dimensionality"], ["result/dimensionality.json"])
    h4_steps["dimensionality_tsne"] = _run_step_with_retry("dimensionality", dataset_path, method="tsne")
    _record_tool_role("Modeling", "dimensionality_tsne", h4_steps["dimensionality_tsne"], ["result/dimensionality_tsne.json"])
    h4_steps["clustering"] = _run_step_with_retry("clustering", dataset_path, method="kmeans")
    _record_tool_role("Modeling", "clustering", h4_steps["clustering"], ["result/clustering.json"])
    h4_steps["model_train"] = _run_step_with_retry("model_train", dataset_path, method="centroid")
    _record_tool_role("Modeling", "model_train", h4_steps["model_train"], ["result/model_results.json"])
    model_results_path = session_dir / "result" / "model_results.json"
    h4_steps["model_eval"] = _run_step_with_retry(
        "model_eval",
        dataset_path,
        method="baseline",
        model_path=model_results_path if model_results_path.exists() else None,
    )
    _record_tool_role("Modeling", "model_eval", h4_steps["model_eval"], ["result/model_eval.json"])
    h4_steps["viz_multivariate"] = _run_step_with_retry("viz_multivariate", dataset_path, mode="scatter")
    _record_tool_role("Visualization", "viz_multivariate", h4_steps["viz_multivariate"], ["plots/scatter.png"])
    embedding_path = session_dir / "result" / "dimensionality.json"
    cluster_path = session_dir / "result" / "clustering.json"
    if embedding_path.exists():
        h4_steps["viz_embedding"] = _run_step_with_retry(
            "viz_embedding", embedding_path, labels_path=cluster_path if cluster_path.exists() else None, name="embedding_pca"
        )
        _record_tool_role("Visualization", "viz_embedding", h4_steps["viz_embedding"], ["plots/embedding_pca.png"])
    tsne_path = session_dir / "result" / "dimensionality_tsne.json"
    if tsne_path.exists():
        h4_steps["viz_embedding_tsne"] = _run_step_with_retry(
            "viz_embedding", tsne_path, labels_path=cluster_path if cluster_path.exists() else None, name="embedding_tsne"
        )
        _record_tool_role("Visualization", "viz_embedding_tsne", h4_steps["viz_embedding_tsne"], ["plots/embedding_tsne.png"])
    h4_expected = [
        "dimensionality.json",
        "clustering.json",
        "model_results.json",
        "model_eval.json",
        "scatter.png",
        "embedding_pca.png",
    ]
    results.append(
        {
            "hypothesis": "H4: 降维/聚类",
            "expected_artifacts": h4_expected,
            "missing": _check_artifacts(h4_expected),
            "steps": h4_steps,
        }
    )

    payload = {"hypotheses": results}
    write_json(session_dir / "result" / "hypothesis_results.json", payload)
    return payload


def _hypothesis_summary_md(payload: dict[str, Any], session_dir: Path) -> str:
    hypotheses = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    if not hypotheses:
        return ""
    lines = ["## 假设验证摘要"]
    missing_total: list[str] = []
    for item in hypotheses:
        title = item.get("hypothesis", "Hypothesis")
        missing = item.get("missing", [])
        if missing:
            lines.append(f"- {title}: 未完成（缺少 {', '.join(missing)}）")
            missing_total.extend(missing)
        else:
            lines.append(f"- {title}: 完成")
    lines.append("")
    if missing_total:
        lines.append("## 未完成原因与输入快照")
        lines.append(f"- 缺失产物: {', '.join(sorted(set(missing_total)))}")
        profile_path = session_dir / "profile" / "data_profile.json"
        if profile_path.exists():
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
                lines.append(f"- 输入快照: rows={profile.get('rows')}, cols={profile.get('columns')}")
            except Exception:
                pass
        error_dir = session_dir / "result" / "errors"
        if error_dir.exists():
            error_files = [p.name for p in error_dir.glob("*.json")]
            if error_files:
                lines.append(f"- 错误记录: {', '.join(sorted(error_files))}")
        lines.append("")
    group_info_path = session_dir / "result" / "stats_group_info.json"
    if group_info_path.exists():
        try:
            group_info = json.loads(group_info_path.read_text(encoding="utf-8"))
            lines.append("## 分组归一化说明")
            lines.append(f"- 方法: {group_info.get('method')}")
            raw_groups = group_info.get("raw_groups") or []
            raw_count = group_info.get("raw_group_count")
            used_groups = group_info.get("used_groups") or []
            excluded = group_info.get("excluded_groups") or []
            if raw_groups:
                raw_line = ", ".join(raw_groups[:10])
                if raw_count and raw_count > 10:
                    raw_line = f"{raw_line} ... (+{raw_count - 10})"
                lines.append(f"- 原始分组: {raw_line}")
            if used_groups:
                lines.append(f"- 使用分组: {', '.join(used_groups)}")
            if excluded:
                lines.append(f"- 排除分组: {', '.join(excluded[:10])}")
            lines.append("")
        except Exception:
            pass
    rationale_path = session_dir / "result" / "feature_selection_rationale.json"
    features_path = session_dir / "result" / "feature_selection.json"
    if rationale_path.exists():
        try:
            rationale = json.loads(rationale_path.read_text(encoding="utf-8"))
            method = rationale.get("method", "")
            top_k = rationale.get("top_k", "")
            source = rationale.get("source", "")
            lines.append("## 特征筛选依据")
            lines.append(f"- 方法: {method}")
            if top_k:
                lines.append(f"- Top K: {top_k}")
            if source:
                lines.append(f"- 来源: {source}")
            lines.append("")
        except Exception:
            pass
    if features_path.exists():
        try:
            features = json.loads(features_path.read_text(encoding="utf-8"))
            if isinstance(features, list) and features:
                lines.append("## 关键特征结果")
                for item in features[:10]:
                    name = item.get("feature") if isinstance(item, dict) else str(item)
                    if name:
                        lines.append(f"- {name}")
                lines.append("")
        except Exception:
            pass
    top_features_path = session_dir / "result" / "top_features.json"
    if top_features_path.exists():
        try:
            top_features = json.loads(top_features_path.read_text(encoding="utf-8"))
            if isinstance(top_features, list) and top_features:
                lines.append("## 差异检验 Top Features")
                for item in top_features[:10]:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("feature")
                    p_val = item.get("p_value")
                    q_val = item.get("q_value")
                    if name:
                        metric = f"p={p_val}" if p_val is not None else ""
                        if q_val is not None:
                            metric = f"{metric}, q={q_val}" if metric else f"q={q_val}"
                        lines.append(f"- {name} {metric}".strip())
                lines.append("")
        except Exception:
            pass
    return "\n".join(lines)


def _build_auto_analysis_payload(session_dir: Path, auto_evidence: list[str]) -> dict[str, Any]:
    summary_lines: list[str] = []
    key_findings: list[str] = []
    limitations: list[str] = []
    next_steps: list[str] = []
    profile_path = session_dir / "profile" / "data_profile.json"
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            summary_lines.append(
                f"数据集包含 {profile.get('rows')} 行、{profile.get('columns')} 列，缺失值 {profile.get('missing_total')}。"
            )
        except Exception:
            pass
    group_info_path = session_dir / "result" / "stats_group_info.json"
    if group_info_path.exists():
        try:
            group_info = json.loads(group_info_path.read_text(encoding="utf-8"))
            used = group_info.get("used_groups") or []
            method = group_info.get("method") or ""
            if used:
                summary_lines.append(f"统计检验基于分组 {', '.join(used)}（方法: {method}）。")
        except Exception:
            pass
    data_quality_path = session_dir / "result" / "data_quality.json"
    if data_quality_path.exists():
        try:
            quality = json.loads(data_quality_path.read_text(encoding="utf-8"))
            datasets = quality.get("datasets") or []
            if datasets:
                ds = datasets[0]
                rows = ds.get("rows")
                cols = ds.get("cols")
                missing_rate = ds.get("missing_rate") or {}
                missing_cols = [k for k, v in missing_rate.items() if isinstance(v, (int, float)) and v > 0]
                if rows and cols:
                    summary_lines.append(f"数据质量检查：{rows} 行 × {cols} 列。")
                if missing_rate:
                    if missing_cols:
                        summary_lines.append(f"存在缺失值的列数：{len(missing_cols)}。")
                    else:
                        summary_lines.append("缺失值占比为 0。")
        except Exception:
            pass
    stats_results_path = session_dir / "result" / "stats_results.json"
    if stats_results_path.exists():
        try:
            stats_df = pd.read_json(stats_results_path)
            total = len(stats_df)
            if total:
                sig_005 = int((stats_df["p_value"] < 0.05).sum()) if "p_value" in stats_df else 0
                sig_001 = int((stats_df["p_value"] < 0.01).sum()) if "p_value" in stats_df else 0
                summary_lines.append(
                    f"统计检验覆盖 {total} 个特征，其中 p<0.05 的特征 {sig_005} 个，p<0.01 的特征 {sig_001} 个。"
                )
                if "p_value" in stats_df:
                    top = stats_df.sort_values("p_value").head(5)
                    for _, row in top.iterrows():
                        feature = row.get("feature")
                        p_val = row.get("p_value")
                        fc = row.get("log2_fold_change")
                        if feature is None:
                            continue
                        metric = f"p={p_val:.3g}" if isinstance(p_val, (int, float)) else f"p={p_val}"
                        if fc is not None:
                            metric = f"{metric}, log2FC={fc:.3g}" if isinstance(fc, (int, float)) else f"{metric}, log2FC={fc}"
                        key_findings.append(f"{feature}: {metric}")
        except Exception:
            pass
    top_features_path = session_dir / "result" / "top_features.json"
    if top_features_path.exists():
        try:
            top_df = pd.read_json(top_features_path)
            for _, row in top_df.head(10).iterrows():
                feature = row.get("feature")
                p_val = row.get("p_value")
                q_val = row.get("q_value")
                if feature is not None:
                    metric = f"p={p_val:.3g}" if isinstance(p_val, (int, float)) else f"p={p_val}"
                    if q_val is not None:
                        metric = f"{metric}, q={q_val:.3g}" if isinstance(q_val, (int, float)) else f"{metric}, q={q_val}"
                    key_findings.append(f"{feature}: {metric}")
        except Exception:
            pass
    model_eval_path = session_dir / "result" / "model_eval.json"
    if model_eval_path.exists():
        try:
            model_eval = json.loads(model_eval_path.read_text(encoding="utf-8"))
            metrics = model_eval.get("metrics", {})
            if isinstance(metrics, dict):
                majority = metrics.get("majority_accuracy")
                centroid = metrics.get("centroid_accuracy")
                if majority is not None:
                    summary_lines.append(f"多数类基线准确率约 {majority:.3f}。")
                if centroid is not None:
                    summary_lines.append(f"质心分类准确率约 {centroid:.3f}。")
        except Exception:
            pass
    plots_dir = session_dir / "plots"
    if not plots_dir.exists() or not any(plots_dir.glob("*")):
        limitations.append("关键可视化图表尚未生成。")
    if not key_findings:
        limitations.append("未获取到显著特征列表，建议检查统计检验输入分组或运行日志。")
    if not summary_lines:
        summary_lines.append("使用自动化产物生成分析摘要。")
    next_steps.extend(
        [
            "如需更深入的模型性能评估，补充交叉验证与 ROC/AUC 指标。",
            "根据显著特征结果补充生物学解释与外部验证。",
        ]
    )
    return {
        "summary": " ".join(summary_lines),
        "key_findings": key_findings,
        "evidence": list(auto_evidence),
        "limitations": limitations,
        "next_steps": next_steps,
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
        "report/report_v1.html",
    ]
    missing = []
    for rel in required:
        if not (session_dir / rel).exists():
            missing.append(rel)
    visuals_dir = session_dir / "charts"
    visuals_present = visuals_dir.exists() and any(visuals_dir.rglob("*"))
    return {
        "missing_required": missing,
        "visuals_present": bool(visuals_present),
    }


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
        record_role_output(
            state.get("session_dir", ""),
            role_id_for_node(name),
            "error" if error else "success",
            output=output,
            error=error,
            duration_sec=round(duration, 3),
            inputs=sorted(list(state.keys())),
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
        plan_json = _safe_json_load(plan_json_raw)
        fallback_plan = _parse_plan_markdown(plan)
        if not plan_json:
            plan_json = fallback_plan
        if not plan_json.get("hypotheses"):
            plan_json["hypotheses"] = fallback_plan.get("hypotheses", [])
        for idx, hypothesis in enumerate(plan_json.get("hypotheses", [])):
            if not hypothesis.get("steps"):
                fallback_steps = []
                if idx < len(fallback_plan.get("hypotheses", [])):
                    fallback_steps = fallback_plan["hypotheses"][idx].get("steps", [])
                hypothesis["steps"] = fallback_steps
            if not hypothesis.get("artifacts"):
                fallback_artifacts = []
                if idx < len(fallback_plan.get("hypotheses", [])):
                    fallback_artifacts = fallback_plan["hypotheses"][idx].get("artifacts", [])
                hypothesis["artifacts"] = fallback_artifacts
        if not plan_json.get("hypotheses"):
            plan_json = {
                "hypotheses": [
                    {"title": "hypothesis_1", "steps": [], "artifacts": []}
                ]
            }
        plan_json_path = Path(state.get("session_dir", "")) / "plan" / "analysis_plan.json"
        write_json(plan_json_path, plan_json)
        record_artifact(state.get("session_dir", ""), plan_json_path, "plan", "plan_analysis")
        hypotheses = [
            h.get("title") for h in plan_json.get("hypotheses", []) if h.get("title")
        ]
        if not hypotheses:
            hypotheses = _extract_hypotheses(plan)
        cleaned_hypotheses = [str(item) for item in hypotheses if item]
        plan_id, _ = plan_store.save_plan(plan, plan_json, cleaned_hypotheses)
        artifact_registry = ArtifactRegistry(Path(state.get("session_dir", "")))
        artifact_plan_dir = artifact_dir(state.get("session_dir", ""), plan_id, "plan")
        artifact_plan_md = artifact_plan_dir / "analysis_plan.md"
        artifact_plan_json = artifact_plan_dir / "analysis_plan.json"
        artifact_registry.register(plan_id, "plan", artifact_plan_md, {"phase": "plan_analysis"})
        if artifact_plan_json.exists():
            artifact_registry.register(plan_id, "plan", artifact_plan_json, {"phase": "plan_analysis"})
        viz_plan_path = Path(state.get("session_dir", "")) / "plan" / "visualization_plan.json"
        if viz_plan_path.exists():
            visual_style = state.get("config", {}).get("visual_style", "academic")
            viz_artifact_dir = artifact_dir(state.get("session_dir", ""), plan_id, "visualizations") / visual_style
            viz_artifact_dir.mkdir(parents=True, exist_ok=True)
            if ARTIFACT_COPY_ENABLED:
                copied_viz_plan = copy_artifact(viz_plan_path, viz_artifact_dir)
                artifact_registry.register(
                    plan_id,
                    "visualization_plan",
                    copied_viz_plan,
                    {"phase": "visualization_plan", "style": visual_style},
                )
            else:
                linked = artifact_link(viz_plan_path, viz_artifact_dir)
                artifact_registry.register(
                    plan_id,
                    "visualization_plan",
                    linked,
                    {"phase": "visualization_plan", "style": visual_style},
                )
        data_quality_path = state.get("data_quality_path")
        if data_quality_path:
            if ARTIFACT_COPY_ENABLED:
                copied = copy_artifact(data_quality_path, artifact_dir(state.get("session_dir", ""), plan_id, "data"))
                artifact_registry.register(plan_id, "data", copied, {"phase": "data_quality"})
            else:
                linked = artifact_link(data_quality_path, artifact_dir(state.get("session_dir", ""), plan_id, "data"))
                artifact_registry.register(plan_id, "data", linked, {"phase": "data_quality"})
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
        messages = render_role_prompt(
            "analysis",
            language,
            prompt_key="analysis_structured",
            outputs=(
                f"{warning_block}Visual style: {visual_style}\nInteractive: {visual_interactive}\n\n"
                f"Auto evidence:\n- " + "\n- ".join(auto_evidence) + f"\n\n{summary}"
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
                        + f"\n\nOutputs:\n{summary}"
                    ),
                },
            ]
        errors = list(state.get("errors", []))
        use_llm = bool(state.get("config", {}).get("analysis_use_llm", ANALYSIS_USE_LLM))
        if use_llm:
            use_llm = _has_advanced_artifacts(Path(state.get("session_dir", "")))
        analysis_payload: dict[str, Any]
        if use_llm:
            try:
                analysis_raw = llm.chat(messages, max_tokens=4096)
                analysis_payload = normalize_analysis_payload(parse_structured_payload(analysis_raw))
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
            existing = set(analysis_payload.get("key_findings", []))
            for item in auto_payload["key_findings"]:
                if item not in existing:
                    analysis_payload.setdefault("key_findings", []).append(item)
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
            if ARTIFACT_COPY_ENABLED:
                copied = copy_artifact(analysis_path, artifact_dir(state.get("session_dir", ""), plan_id, "result"))
                artifact_registry.register(plan_id, "result", copied, {"phase": "analysis_results"})
            else:
                linked = artifact_link(analysis_path, artifact_dir(state.get("session_dir", ""), plan_id, "result"))
                artifact_registry.register(plan_id, "result", linked, {"phase": "analysis_results"})
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
            if ARTIFACT_COPY_ENABLED:
                copied = copy_artifact(
                    outline_path,
                    artifact_dir(state.get("session_dir", ""), plan_id, "report"),
                )
                artifact_registry.register(plan_id, "report", copied, {"phase": "report_outline"})
            else:
                linked = artifact_link(outline_path, artifact_dir(state.get("session_dir", ""), plan_id, "report"))
                artifact_registry.register(plan_id, "report", linked, {"phase": "report_outline"})
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
        if use_report_llm:
            report_raw = llm.chat(messages, max_tokens=4096)
            report_payload = normalize_report_payload(parse_structured_payload(report_raw))
        else:
            report_payload = normalize_report_payload({})
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
            if ARTIFACT_COPY_ENABLED:
                copied = copy_artifact(
                    report_path,
                    artifact_dir(state.get("session_dir", ""), plan_id, "report"),
                )
                artifact_registry.register(plan_id, "report", copied, {"phase": "generate_report"})
            else:
                linked = artifact_link(report_path, artifact_dir(state.get("session_dir", ""), plan_id, "report"))
                artifact_registry.register(plan_id, "report", linked, {"phase": "generate_report"})
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
        audit["custom_lines"] = state.get("custom_line_records", [])
        audit["custom_line_summary"] = state.get("custom_line_summary", {})
        summary["run_audit"] = audit
        summary["pipeline_fallbacks"] = audit["pipeline_fallbacks"]
        summary["custom_lines"] = audit["custom_lines"]
        summary["custom_line_summary"] = audit["custom_line_summary"]
        write_json(session_dir / "meta" / "run_audit.json", audit)
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
    graph.add_edge("analyze_results", "pipeline_guard")
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
