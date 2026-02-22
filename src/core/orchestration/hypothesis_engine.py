from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.api.config import EXECUTION_MAX_RETRIES
from src.core.analytics.toolkit.runner import run_step

from .io_utils import ensure_dir, record_role_output, write_json


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
        cv_folds=5,
    )
    _record_tool_role(
        "Modeling",
        "model_eval",
        h4_steps["model_eval"],
        ["result/model_eval.json", "result/model_eval_detail.json", "result/cv_results.json"],
    )
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
        "model_eval_detail.json",
        "cv_results.json",
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
    matrix = _build_hypothesis_matrix(payload)
    write_json(session_dir / "result" / "hypothesis_matrix.json", matrix)
    coverage_report = _build_coverage_report(session_dir)
    write_json(session_dir / "result" / "coverage_report.json", coverage_report)
    visual_binding = _build_visual_binding(session_dir)
    write_json(session_dir / "result" / "visual_binding.json", visual_binding)
    hypothesis_evidence = _build_hypothesis_evidence(session_dir, payload)
    write_json(session_dir / "result" / "hypothesis_evidence.json", hypothesis_evidence)
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


def _build_hypothesis_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    hypotheses = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    matrix: list[dict[str, Any]] = []
    for item in hypotheses:
        title = item.get("hypothesis", "Hypothesis")
        expected = item.get("expected_artifacts", []) or []
        missing = item.get("missing", []) or []
        status = "ok" if not missing else "partial"
        if missing and len(missing) == len(expected):
            status = "failed"
        entry = {
            "hypothesis": title,
            "status": status,
            "expected_artifacts": expected,
            "missing_artifacts": missing,
            "steps": list(item.get("steps", {}).keys()),
            "reason": "missing artifacts" if missing else "",
        }
        matrix.append(entry)
    return {"hypotheses": matrix}


def _build_coverage_report(session_dir: Path) -> dict[str, Any]:
    numeric_cols: list[str] = []
    analyzed_cols: list[str] = []
    data_quality_path = session_dir / "result" / "data_quality.json"
    if data_quality_path.exists():
        try:
            payload = json.loads(data_quality_path.read_text(encoding="utf-8"))
            datasets = payload.get("datasets") or []
            if datasets:
                stats = datasets[0].get("stats") or {}
                for col, stat in stats.items():
                    if isinstance(stat, dict) and stat.get("mean") is not None:
                        numeric_cols.append(col)
        except Exception:
            pass
    stats_path = session_dir / "result" / "stats_results.json"
    if stats_path.exists():
        try:
            stats_df = pd.read_json(stats_path)
            analyzed_cols = stats_df["feature"].astype(str).unique().tolist()
        except Exception:
            pass
    missing = sorted(set(numeric_cols) - set(analyzed_cols))
    mode = "full" if numeric_cols and not missing else "partial"
    rationale_path = session_dir / "result" / "feature_selection_rationale.json"
    filter_info: dict[str, Any] = {}
    if rationale_path.exists():
        try:
            filter_info = json.loads(rationale_path.read_text(encoding="utf-8"))
        except Exception:
            filter_info = {}
    return {
        "mode": mode,
        "numeric_features": numeric_cols,
        "analyzed_features": analyzed_cols,
        "missing_features": missing,
        "filter_info": filter_info,
    }


def _build_visual_binding(session_dir: Path) -> dict[str, Any]:
    bindings: list[dict[str, Any]] = []
    mapping = {
        "H1: 差异检验": [
            "plots/volcano_plot.png",
            "plots/top_features_bar.png",
        ],
        "H2: 关键特征筛选": [
            "result/feature_selection.json",
        ],
        "H3: 相关性结构": [
            "plots/heatmap.png",
            "plots/network.png",
        ],
        "H4: 降维/聚类": [
            "plots/embedding_pca.png",
            "plots/embedding_tsne.png",
            "plots/scatter.png",
        ],
    }
    for hypo, items in mapping.items():
        for rel in items:
            path = session_dir / rel
            bindings.append(
                {
                    "hypothesis": hypo,
                    "artifact": rel,
                    "exists": path.exists(),
                }
            )
    return {"bindings": bindings}


def _build_hypothesis_evidence(
    session_dir: Path,
    hypothesis_payload: dict[str, Any],
    allowed_hypothesis_ids: set[str] | None = None,
) -> dict[str, Any]:
    allowed_ids = {str(x).upper() for x in (allowed_hypothesis_ids or set()) if str(x).strip()}
    evidence_rows: list[dict[str, Any]] = []

    def _status_for(hyp_name: str) -> str:
        for item in hypothesis_payload.get("hypotheses", []) if isinstance(hypothesis_payload, dict) else []:
            title = str(item.get("hypothesis", ""))
            if title.startswith(hyp_name):
                missing = item.get("missing", []) or []
                if missing:
                    return "partial" if len(missing) < len(item.get("expected_artifacts", []) or []) else "failed"
                return "supported"
        return "inconclusive"

    # H1 evidence
    h1_metrics: dict[str, Any] = {}
    stats_path = session_dir / "result" / "stats_results.json"
    top_path = session_dir / "result" / "top_features.json"
    if stats_path.exists():
        try:
            df = pd.read_json(stats_path)
            h1_metrics["tested_features"] = int(len(df))
            if "p_value" in df.columns:
                h1_metrics["significant_p_lt_0_05"] = int((df["p_value"] < 0.05).sum())
        except Exception:
            pass
    if top_path.exists():
        try:
            top = pd.read_json(top_path)
            if "feature" in top.columns:
                h1_metrics["top_features"] = [str(x) for x in top["feature"].head(5).tolist()]
        except Exception:
            pass
    evidence_rows.append(
        {
            "hypothesis_id": "H1",
            "claim": "组间存在显著差异标志物",
            "evidence_sources": [
                p
                for p in [
                    "result/stats_results.json",
                    "result/stats_summary.json",
                    "result/group_means.csv",
                    "result/differential_analysis_output.txt",
                    "result/top_features.json",
                    "plots/volcano_plot.png",
                ]
                if (session_dir / p).exists()
            ],
            "quant_metrics": h1_metrics,
            "status": _status_for("H1"),
        }
    )

    # H2 evidence
    h2_metrics: dict[str, Any] = {}
    eval_path = session_dir / "result" / "model_eval.json"
    cv_path = session_dir / "result" / "cv_results.json"
    if eval_path.exists():
        try:
            payload = json.loads(eval_path.read_text(encoding="utf-8"))
            metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
            for k in ("majority_accuracy", "centroid_accuracy", "auc"):
                if metrics.get(k) is not None:
                    h2_metrics[k] = metrics.get(k)
        except Exception:
            pass
    if cv_path.exists():
        try:
            cv = json.loads(cv_path.read_text(encoding="utf-8"))
            if isinstance(cv, dict):
                if cv.get("mean_accuracy") is not None:
                    h2_metrics["cv_mean_accuracy"] = cv.get("mean_accuracy")
                if isinstance(cv.get("folds"), list):
                    h2_metrics["cv_folds"] = len(cv.get("folds"))
        except Exception:
            pass
    evidence_rows.append(
        {
            "hypothesis_id": "H2",
            "claim": "多特征组合具备诊断预测力",
            "evidence_sources": [p for p in ["result/model_eval.json", "result/cv_results.json", "result/feature_selection.json"] if (session_dir / p).exists()],
            "quant_metrics": h2_metrics,
            "status": _status_for("H2"),
        }
    )

    # H3 evidence
    h3_metrics: dict[str, Any] = {}
    corr_path = session_dir / "result" / "correlation.json"
    if corr_path.exists():
        try:
            corr = pd.read_json(corr_path)
            arr = corr.to_numpy().copy()
            import numpy as np

            np.fill_diagonal(arr, 0)
            idx = divmod(np.abs(arr).argmax(), arr.shape[1])
            h3_metrics["strongest_pair"] = [str(corr.index[idx[0]]), str(corr.columns[idx[1]])]
            h3_metrics["strongest_abs_corr"] = float(abs(arr[idx]))
        except Exception:
            pass
    evidence_rows.append(
        {
            "hypothesis_id": "H3",
            "claim": "变量间存在结构化相关网络",
            "evidence_sources": [p for p in ["result/correlation.json", "plots/heatmap.png", "plots/network.png"] if (session_dir / p).exists()],
            "quant_metrics": h3_metrics,
            "status": _status_for("H3"),
        }
    )

    # H4 evidence
    h4_metrics: dict[str, Any] = {}
    cluster_path = session_dir / "result" / "clustering.json"
    dim_path = session_dir / "result" / "dimensionality.json"
    if dim_path.exists():
        h4_metrics["has_pca_embedding"] = True
    if (session_dir / "result" / "dimensionality_tsne.json").exists():
        h4_metrics["has_tsne_embedding"] = True
    if cluster_path.exists():
        try:
            cluster = json.loads(cluster_path.read_text(encoding="utf-8"))
            labels = cluster.get("labels")
            if isinstance(labels, list):
                h4_metrics["cluster_label_count"] = len(labels)
        except Exception:
            pass
    evidence_rows.append(
        {
            "hypothesis_id": "H4",
            "claim": "样本在降维空间中存在可解释结构",
            "evidence_sources": [p for p in ["result/dimensionality.json", "result/clustering.json", "plots/embedding_pca.png", "plots/embedding_tsne.png"] if (session_dir / p).exists()],
            "quant_metrics": h4_metrics,
            "status": _status_for("H4"),
        }
    )

    if allowed_ids:
        evidence_rows = [row for row in evidence_rows if str(row.get("hypothesis_id", "")).upper() in allowed_ids]
    return {"hypotheses": evidence_rows}


def _build_hypothesis_contrast(evidence_payload: dict[str, Any], session_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in evidence_payload.get("hypotheses", []) if isinstance(evidence_payload, dict) else []:
        hid = str(item.get("hypothesis_id", ""))
        metrics = item.get("quant_metrics", {}) if isinstance(item.get("quant_metrics"), dict) else {}
        primary = {"path_id": "path_a", "metrics": metrics, "status": "ok" if metrics else "partial"}
        secondary_metrics: dict[str, Any] = {}
        secondary_reason = ""
        if hid == "H1":
            mt_path = session_dir / "result" / "multiple_testing.json"
            if mt_path.exists():
                try:
                    mt_df = pd.read_json(mt_path)
                    if "q_value" in mt_df.columns:
                        secondary_metrics["q_lt_0_05"] = int((mt_df["q_value"] < 0.05).sum())
                    secondary_metrics["tested_features"] = int(len(mt_df))
                except Exception as exc:
                    secondary_reason = f"failed_to_parse_multiple_testing: {exc}"
        elif hid == "H2":
            cv_path = session_dir / "result" / "cv_results.json"
            if cv_path.exists():
                try:
                    cv = json.loads(cv_path.read_text(encoding="utf-8"))
                    if cv.get("mean_accuracy") is not None:
                        secondary_metrics["cv_mean_accuracy"] = cv.get("mean_accuracy")
                    if cv.get("std_accuracy") is not None:
                        secondary_metrics["cv_std_accuracy"] = cv.get("std_accuracy")
                except Exception as exc:
                    secondary_reason = f"failed_to_parse_cv: {exc}"
        elif hid == "H3":
            corr_path = session_dir / "result" / "correlation.json"
            if corr_path.exists():
                try:
                    corr = pd.read_json(corr_path)
                    import numpy as np

                    arr = corr.to_numpy().copy()
                    np.fill_diagonal(arr, 0)
                    secondary_metrics["abs_corr_gt_0_7_edges"] = int((np.abs(arr) > 0.7).sum() / 2)
                    secondary_metrics["abs_corr_gt_0_5_edges"] = int((np.abs(arr) > 0.5).sum() / 2)
                except Exception as exc:
                    secondary_reason = f"failed_to_parse_correlation: {exc}"
        elif hid == "H4":
            if (session_dir / "result" / "dimensionality_tsne.json").exists():
                secondary_metrics["has_tsne_embedding"] = True
            cl_path = session_dir / "result" / "clustering.json"
            if cl_path.exists():
                try:
                    cl = json.loads(cl_path.read_text(encoding="utf-8"))
                    labels = cl.get("labels")
                    if isinstance(labels, list):
                        secondary_metrics["cluster_count"] = len(set(labels))
                except Exception as exc:
                    secondary_reason = f"failed_to_parse_clustering: {exc}"
        secondary = {
            "path_id": "path_b",
            "metrics": secondary_metrics,
            "status": "ok" if secondary_metrics else "missing",
            "reason": secondary_reason or ("secondary evidence unavailable" if not secondary_metrics else ""),
        }
        consistency = "unknown"
        conflict_reason = ""
        if hid == "H1":
            a = metrics.get("significant_p_lt_0_05")
            b = secondary_metrics.get("q_lt_0_05")
            if isinstance(a, int) and isinstance(b, int):
                consistency = "consistent" if (a == 0 and b == 0) or (a > 0 and b > 0) else "conflict"
                if consistency == "conflict":
                    conflict_reason = f"p-significant={a}, q-significant={b}"
        elif hid == "H2":
            a = metrics.get("centroid_accuracy")
            b = secondary_metrics.get("cv_mean_accuracy")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                consistency = "consistent" if abs(float(a) - float(b)) <= 0.15 else "conflict"
                if consistency == "conflict":
                    conflict_reason = f"centroid_accuracy={a}, cv_mean_accuracy={b}"
        elif hid == "H3":
            a = metrics.get("strongest_abs_corr")
            b = secondary_metrics.get("abs_corr_gt_0_7_edges")
            if isinstance(a, (int, float)) and isinstance(b, int):
                consistency = "consistent" if (a >= 0.7 and b > 0) or (a < 0.7 and b == 0) else "conflict"
                if consistency == "conflict":
                    conflict_reason = f"strongest_abs_corr={a}, abs_corr_gt_0_7_edges={b}"
        elif hid == "H4":
            a = metrics.get("has_pca_embedding")
            b = secondary_metrics.get("has_tsne_embedding")
            if isinstance(a, bool) and isinstance(b, bool):
                consistency = "consistent" if a and b else "conflict"
                if consistency == "conflict":
                    conflict_reason = f"has_pca_embedding={a}, has_tsne_embedding={b}"

        status = "validated"
        if consistency == "conflict":
            status = "inconclusive"
        elif not secondary_metrics:
            status = "partial"
        conflict_category = ""
        if consistency == "conflict":
            if "failed_to_parse" in conflict_reason:
                conflict_category = "path_failure"
            elif "secondary evidence unavailable" in conflict_reason:
                conflict_category = "data_sparse"
            else:
                conflict_category = "metric_disagreement"
        rows.append(
            {
                "hypothesis_id": hid,
                "path_a": primary,
                "path_b": secondary,
                "consistency": consistency,
                "status": status,
                "conflict_reason": conflict_reason or secondary.get("reason", ""),
                "conflict_category": conflict_category,
            }
        )
    return {"hypotheses": rows}


def _build_hypothesis_validation_contract(
    plan_json: dict[str, Any],
    contrast_payload: dict[str, Any],
    multipath_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required = []
    for h in plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []:
        hid = str(h.get("id", ""))
        paths = h.get("validation_paths", [])
        required.append({"hypothesis_id": hid, "required_paths": len(paths), "has_dual_paths": len(paths) >= 2})
    contrast_map = {
        str(h.get("hypothesis_id", "")): h for h in contrast_payload.get("hypotheses", []) if isinstance(contrast_payload, dict)
    }
    multipath_map = {
        str(h.get("hypothesis_id", "")): h
        for h in (multipath_payload or {}).get("hypotheses", [])
        if isinstance(h, dict)
    }
    rows: list[dict[str, Any]] = []
    for item in required:
        hid = item["hypothesis_id"]
        contrast = contrast_map.get(hid, {})
        multipath = multipath_map.get(hid, {})
        paths = multipath.get("paths", []) if isinstance(multipath, dict) else []
        path_statuses = [str(p.get("status", "")) for p in paths if isinstance(p, dict)]
        dual_paths_executed = len(paths) >= 2 and all(status not in {"skipped", ""} for status in path_statuses[:2])
        rows.append(
            {
                **item,
                "executed_status": multipath.get("status") or contrast.get("status", "missing"),
                "consistency": contrast.get("consistency", "unknown"),
                "conflict_reason": contrast.get("conflict_reason", ""),
                "dual_paths_executed": dual_paths_executed,
                "path_statuses": path_statuses,
            }
        )
    satisfied = all(r.get("has_dual_paths") and r.get("dual_paths_executed") for r in rows)
    return {"satisfied": satisfied, "hypotheses": rows}


def _path_artifacts_status(
    session_dir: Path,
    expected_artifacts: list[str],
    fallback_sources: list[str],
) -> dict[str, Any]:
    expected = [str(x).strip() for x in expected_artifacts if str(x).strip()]
    if not expected and fallback_sources:
        expected = [str(x).strip() for x in fallback_sources if str(x).strip()]
    missing: list[str] = []
    present: list[str] = []
    for rel in expected:
        target = rel.lstrip("./")
        candidates = [
            session_dir / target,
            session_dir / "result" / target,
            session_dir / "plots" / target,
            session_dir / "report" / target,
        ]
        if any(path.exists() for path in candidates):
            present.append(rel)
        else:
            missing.append(rel)
    if not expected:
        status = "skipped"
    elif not missing:
        status = "validated"
    elif len(present) == 0:
        status = "failed"
    else:
        status = "partial"
    return {
        "status": status,
        "expected_artifacts": expected,
        "present_artifacts": present,
        "missing_artifacts": missing,
    }


def _evaluate_hypothesis_validation_paths(
    session_dir: Path,
    plan_json: dict[str, Any],
    evidence_payload: dict[str, Any],
    contrast_payload: dict[str, Any],
) -> dict[str, Any]:
    evidence_map = {
        str(item.get("hypothesis_id", "")).upper(): item
        for item in evidence_payload.get("hypotheses", [])
        if isinstance(item, dict)
    }
    contrast_map = {
        str(item.get("hypothesis_id", "")).upper(): item
        for item in contrast_payload.get("hypotheses", [])
        if isinstance(item, dict)
    }
    rows: list[dict[str, Any]] = []
    total_invalid_expected = 0
    total_missing_expected = 0
    for hyp in plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []:
        if not isinstance(hyp, dict):
            continue
        hid = str(hyp.get("id", "")).upper()
        title = str(hyp.get("title", ""))
        hyp_paths = hyp.get("validation_paths") if isinstance(hyp.get("validation_paths"), list) else []
        if len(hyp_paths) < 2:
            hyp_paths = _default_validation_paths(
                hid or "H1",
                [str(x) for x in hyp.get("validation_plan_steps", []) if str(x).strip()],
                [str(x) for x in hyp.get("expected_artifacts", []) if str(x).strip()],
                title,
                str(hyp.get("hypothesis", "")),
            )
        evidence_entry = evidence_map.get(hid, {})
        evidence_sources = (
            evidence_entry.get("evidence_sources", [])
            if isinstance(evidence_entry.get("evidence_sources"), list)
            else []
        )
        contrast_entry = contrast_map.get(hid, {})
        invalid_expected = hyp.get("invalid_expected_artifacts", []) if isinstance(hyp.get("invalid_expected_artifacts"), list) else []
        path_results: list[dict[str, Any]] = []
        for idx, path in enumerate(hyp_paths):
            if not isinstance(path, dict):
                continue
            path_id = str(path.get("path_id") or f"path_{chr(97 + idx)}").strip().lower()
            method_family = str(path.get("method_family") or "").strip().lower() or _infer_method_family(
                hid,
                title,
                str(hyp.get("hypothesis", "")),
                idx,
            )
            expected = path.get("expected_artifacts") if isinstance(path.get("expected_artifacts"), list) else []
            start_ts = time.time()
            status_payload = _path_artifacts_status(
                session_dir,
                [str(x) for x in expected if str(x).strip()],
                [str(x) for x in evidence_sources if str(x).strip()],
            )
            contrast_metrics = {}
            contrast_status = ""
            if path_id in {"path_a", "a"} and isinstance(contrast_entry.get("path_a"), dict):
                contrast_metrics = contrast_entry["path_a"].get("metrics", {})
                contrast_status = str(contrast_entry["path_a"].get("status", ""))
            elif path_id in {"path_b", "b"} and isinstance(contrast_entry.get("path_b"), dict):
                contrast_metrics = contrast_entry["path_b"].get("metrics", {})
                contrast_status = str(contrast_entry["path_b"].get("status", ""))
            if status_payload["status"] in {"failed", "partial"} and contrast_status == "ok":
                status_payload["status"] = "partial" if status_payload["status"] == "failed" else "validated"
            path_results.append(
                {
                    "path_id": path_id,
                    "method_family": method_family,
                    "steps": [str(x) for x in path.get("steps", []) if str(x).strip()],
                    "status": status_payload["status"],
                    "expected_artifacts": status_payload["expected_artifacts"],
                    "present_artifacts": status_payload["present_artifacts"],
                    "missing_artifacts": status_payload["missing_artifacts"],
                    "metrics": contrast_metrics if isinstance(contrast_metrics, dict) else {},
                    "duration_ms": int((time.time() - start_ts) * 1000),
                    "error": "" if status_payload["status"] != "failed" else "required_artifacts_missing",
                }
            )
        missing_total = sum(len(p.get("missing_artifacts", [])) for p in path_results if isinstance(p, dict))
        total_missing_expected += int(missing_total)
        total_invalid_expected += int(len(invalid_expected))
        consistency = str(contrast_entry.get("consistency", "unknown"))
        statuses = [str(x.get("status", "")) for x in path_results]
        if consistency == "conflict":
            overall = "inconclusive"
        elif statuses and all(x == "validated" for x in statuses):
            overall = "validated"
        elif statuses and any(x in {"validated", "partial"} for x in statuses):
            overall = "partial"
        elif statuses and all(x in {"failed", "skipped"} for x in statuses):
            overall = "failed"
        else:
            overall = "inconclusive"
        rows.append(
            {
                "hypothesis_id": hid,
                "title": title,
                "status": overall,
                "consistency": consistency,
                "conflict_reason": str(contrast_entry.get("conflict_reason", "")),
                "conflict_category": str(contrast_entry.get("conflict_category", "")),
                "recovery_action": (
                    "retry_secondary_or_code_repair"
                    if any(p.get("status") == "failed" for p in path_results)
                    else ""
                ),
                "invalid_expected_artifacts": [str(x) for x in invalid_expected if str(x).strip()],
                "paths": path_results,
            }
        )
    total = len(rows)
    conflict_count = sum(1 for row in rows if row.get("consistency") == "conflict")
    success_count = sum(1 for row in rows if row.get("status") == "validated")
    return {
        "hypotheses": rows,
        "stats": {
            "total_hypotheses": total,
            "validated": success_count,
            "inconclusive": sum(1 for row in rows if row.get("status") == "inconclusive"),
            "failed": sum(1 for row in rows if row.get("status") == "failed"),
            "partial": sum(1 for row in rows if row.get("status") == "partial"),
            "conflict_rate": round((conflict_count / total), 4) if total else 0.0,
            "path_success_rate": round(
                (
                    sum(
                        1
                        for row in rows
                        for p in row.get("paths", [])
                        if p.get("status") == "validated"
                    )
                    / max(
                        1,
                        sum(len(row.get("paths", [])) for row in rows),
                    )
                ),
                4,
            ),
            "invalid_expected_artifact_total": total_invalid_expected,
            "missing_expected_artifact_total": total_missing_expected,
        },
    }


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


def _load_structured_evidence(session_dir: Path) -> dict[str, Any]:
    candidates = [session_dir / "result" / "hypothesis_evidence_pack.json"]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            continue
    return {}


def _metric_names_from_evidence(evidence_payload: dict[str, Any]) -> set[str]:
    metric_names: set[str] = set()
    for hyp in evidence_payload.get("hypotheses", []) if isinstance(evidence_payload, dict) else []:
        if not isinstance(hyp, dict):
            continue
        quant_metrics = hyp.get("quant_metrics", {})
        if isinstance(quant_metrics, dict):
            metric_names.update(str(k).lower() for k in quant_metrics.keys() if str(k).strip())
        elif isinstance(quant_metrics, list):
            for item in quant_metrics:
                if isinstance(item, dict) and str(item.get("name", "")).strip():
                    metric_names.add(str(item.get("name", "")).strip().lower())
    return metric_names


def _llm_analysis_has_metric_grounding(
    analysis_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    min_metric_refs: int = 2,
) -> bool:
    metric_names = _metric_names_from_evidence(evidence_payload)
    if not metric_names:
        return False
    text_parts = [
        str(analysis_payload.get("summary", "")),
        " ".join(str(x) for x in analysis_payload.get("key_findings", [])),
        " ".join(str(x) for x in analysis_payload.get("evidence", [])),
    ]
    joined = " ".join(text_parts).lower()
    hits = sum(1 for name in metric_names if name in joined)
    return hits >= min_metric_refs
