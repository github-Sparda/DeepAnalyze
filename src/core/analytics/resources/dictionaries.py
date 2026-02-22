from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REASON_RECOVERY_MAP: dict[str, str] = {
    "insufficient_sample": "increase_sample_or_reduce_model_complexity",
    "missing_artifact": "rerun_missing_step_and_verify_outputs",
    "path_invalid": "normalize_paths_and_reassemble",
    "assumption_violation": "switch_nonparametric_or_transform_data",
    "method_conflict": "run_third_path_and_compare_stability",
    "extract_failed": "repair_parser_and_retry_extraction",
    "execution_error": "invoke_code_repair_then_rerun",
    "invalid_evidence_pack": "repair_evidence_pack_schema_and_rerun",
}


def default_metric_dictionary() -> dict[str, dict[str, Any]]:
    return {
        "significant_p_lt_0_05": {
            "display_name": "显著特征数(p<0.05)",
            "unit": "count",
            "threshold": ">=1",
            "direction": "higher_is_stronger",
            "category": "significance",
        },
        "q_lt_0_05": {
            "display_name": "显著特征数(q<0.05)",
            "unit": "count",
            "threshold": ">=1",
            "direction": "higher_is_stronger",
            "category": "significance",
        },
        "centroid_accuracy": {
            "display_name": "质心分类准确率",
            "unit": "ratio",
            "threshold": ">=0.6",
            "direction": "higher_is_stronger",
            "category": "performance",
        },
        "cv_mean_accuracy": {
            "display_name": "交叉验证平均准确率",
            "unit": "ratio",
            "threshold": ">=0.6",
            "direction": "higher_is_stronger",
            "category": "performance",
        },
        "auc": {
            "display_name": "AUC",
            "unit": "ratio",
            "threshold": ">=0.7",
            "direction": "higher_is_stronger",
            "category": "performance",
        },
        "strongest_abs_corr": {
            "display_name": "最强绝对相关系数",
            "unit": "corr",
            "threshold": ">=0.5",
            "direction": "higher_is_stronger",
            "category": "correlation",
        },
        "abs_corr_gt_0_7_edges": {
            "display_name": "|corr|>0.7 边数",
            "unit": "count",
            "threshold": ">=1",
            "direction": "higher_is_stronger",
            "category": "correlation",
        },
        "cluster_count": {
            "display_name": "聚类簇数量",
            "unit": "count",
            "threshold": ">=2",
            "direction": "task_dependent",
            "category": "clustering",
        },
    }


def default_feature_dictionary() -> dict[str, dict[str, Any]]:
    return {}


def default_method_dictionary() -> dict[str, dict[str, Any]]:
    return {
        "parametric_test": {
            "assumption_checks": ["normality", "variance_homogeneity"],
            "notes": "参数检验路径，适合近似正态数据。",
        },
        "nonparametric_or_fdr": {
            "assumption_checks": ["rank_based_or_multiple_testing_control"],
            "notes": "非参数或多重检验校正路径。",
        },
        "feature_modeling": {
            "assumption_checks": ["label_balance", "feature_scaling"],
            "notes": "特征组合与建模路径。",
        },
        "cross_validation": {
            "assumption_checks": ["fold_stability", "sample_size_per_fold"],
            "notes": "交叉验证稳健性路径。",
        },
        "pearson_network": {
            "assumption_checks": ["linear_relationship"],
            "notes": "线性相关网络路径。",
        },
        "rank_or_sparse_network": {
            "assumption_checks": ["monotonic_or_sparse_assumption"],
            "notes": "秩相关/稀疏图路径。",
        },
        "pca_cluster": {
            "assumption_checks": ["scaling_required"],
            "notes": "PCA + 聚类路径。",
        },
        "tsne_or_umap_cluster": {
            "assumption_checks": ["perplexity_or_neighbor_setting"],
            "notes": "t-SNE/UMAP + 聚类路径。",
        },
    }


def _load_dictionary(session_dir: Path, filename: str, defaults: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        session_dir / "meta" / filename,
        session_dir / "config" / filename,
        Path("config") / filename,
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                merged = dict(defaults)
                merged.update(payload)
                return merged
        except Exception:
            continue
    return dict(defaults)


def load_metric_dictionary(session_dir: Path) -> dict[str, dict[str, Any]]:
    return _load_dictionary(session_dir, "metric_dictionary.json", default_metric_dictionary())


def load_feature_dictionary(session_dir: Path) -> dict[str, dict[str, Any]]:
    return _load_dictionary(session_dir, "feature_dictionary.json", default_feature_dictionary())


def load_method_dictionary(session_dir: Path) -> dict[str, dict[str, Any]]:
    return _load_dictionary(session_dir, "method_dictionary.json", default_method_dictionary())


def _annotated_quant_metrics(metrics: dict[str, Any], metric_dict: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in (metrics or {}).items():
        key = str(name)
        meta = metric_dict.get(key, {})
        rows.append(
            {
                "name": key,
                "display_name": meta.get("display_name", key),
                "value": value,
                "unit": meta.get("unit", ""),
                "threshold": meta.get("threshold", ""),
                "direction": meta.get("direction", "unknown"),
                "category": meta.get("category", "general"),
            }
        )
    return rows


def _effect_metrics_from_quant(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    for item in metrics:
        name = str(item.get("name", "")).lower()
        if any(k in name for k in ("corr", "accuracy", "auc", "fold", "diff")):
            effects.append(
                {
                    "name": item.get("name"),
                    "value": item.get("value"),
                    "unit": item.get("unit", ""),
                    "ci": "",
                    "sample_size": None,
                }
            )
    return effects


def _reason_and_recovery(status: str, consistency: str, missing_artifacts: list[str]) -> tuple[str, str]:
    if status == "failed":
        if missing_artifacts:
            return "missing_artifact", REASON_RECOVERY_MAP["missing_artifact"]
        return "execution_error", REASON_RECOVERY_MAP["execution_error"]
    if status == "inconclusive" or consistency == "conflict":
        return "method_conflict", REASON_RECOVERY_MAP["method_conflict"]
    if status == "partial":
        return "execution_error", REASON_RECOVERY_MAP["execution_error"]
    return "", ""


def build_hypothesis_evidence_pack(
    evidence_payload: dict[str, Any],
    contrast_payload: dict[str, Any],
    multipath_payload: dict[str, Any],
    metric_dict: dict[str, dict[str, Any]],
    feature_dict: dict[str, dict[str, Any]],
    method_dict: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    del feature_dict  # reserved for later feature-level annotation
    contrast_map = {
        str(item.get("hypothesis_id", "")).upper(): item
        for item in contrast_payload.get("hypotheses", [])
        if isinstance(item, dict)
    }
    multipath_map = {
        str(item.get("hypothesis_id", "")).upper(): item
        for item in multipath_payload.get("hypotheses", [])
        if isinstance(item, dict)
    }
    rows: list[dict[str, Any]] = []
    for item in evidence_payload.get("hypotheses", []) if isinstance(evidence_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        hid = str(item.get("hypothesis_id", "")).upper()
        claim = str(item.get("claim", ""))
        quant_metrics = _annotated_quant_metrics(
            item.get("quant_metrics", {}) if isinstance(item.get("quant_metrics"), dict) else {},
            metric_dict,
        )
        effect_metrics = _effect_metrics_from_quant(quant_metrics)
        contrast = contrast_map.get(hid, {})
        multipath = multipath_map.get(hid, {})
        status = str(multipath.get("status") or contrast.get("status") or item.get("status") or "inconclusive")
        consistency = str(contrast.get("consistency", "unknown"))
        missing_artifacts: list[str] = []
        method_trace: list[dict[str, Any]] = []
        for path in multipath.get("paths", []) if isinstance(multipath, dict) else []:
            if not isinstance(path, dict):
                continue
            family = str(path.get("method_family", ""))
            method_meta = method_dict.get(family, {})
            method_trace.append(
                {
                    "path_id": path.get("path_id", ""),
                    "method_family": family,
                    "assumption_checks": method_meta.get("assumption_checks", []),
                    "notes": method_meta.get("notes", ""),
                    "status": path.get("status", ""),
                }
            )
            missing_artifacts.extend([str(x) for x in path.get("missing_artifacts", []) if str(x).strip()])
        reason_code, recovery_action = _reason_and_recovery(status, consistency, missing_artifacts)
        if not reason_code:
            if not quant_metrics and not item.get("evidence_sources"):
                reason_code = "extract_failed"
                recovery_action = REASON_RECOVERY_MAP["extract_failed"]
        rows.append(
            {
                "hypothesis_id": hid,
                "claim": claim,
                "status": status,
                "quant_metrics": quant_metrics,
                "effect_metrics": effect_metrics,
                "method_trace": method_trace,
                "evidence_sources": item.get("evidence_sources", []),
                "consistency": {
                    "path_a": (contrast.get("path_a", {}) if isinstance(contrast.get("path_a"), dict) else {}).get("status", ""),
                    "path_b": (contrast.get("path_b", {}) if isinstance(contrast.get("path_b"), dict) else {}).get("status", ""),
                    "flag": consistency,
                },
                "reason_code": reason_code,
                "recovery_action": recovery_action,
            }
        )
    return {"hypotheses": rows}


def build_hypothesis_gate_report(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for hyp in evidence_pack.get("hypotheses", []) if isinstance(evidence_pack, dict) else []:
        if not isinstance(hyp, dict):
            continue
        quant = hyp.get("quant_metrics", []) if isinstance(hyp.get("quant_metrics"), list) else []
        effects = hyp.get("effect_metrics", []) if isinstance(hyp.get("effect_metrics"), list) else []
        status = str(hyp.get("status", ""))
        consistency = (hyp.get("consistency", {}) if isinstance(hyp.get("consistency"), dict) else {}).get("flag", "unknown")
        checks = {
            "quant_metric_count": len(quant) >= 2,
            "effect_plus_significance": bool(effects) and any(
                str(item.get("category", "")) == "significance" for item in quant
            ),
            "consistency": consistency != "conflict",
            "status": status not in {"failed", "skipped"},
        }
        gate_status = "pass" if all(checks.values()) else ("partial" if any(checks.values()) else "fail")
        rows.append(
            {
                "hypothesis_id": hyp.get("hypothesis_id", ""),
                "gate_status": gate_status,
                "checks": checks,
                "reason_code": hyp.get("reason_code", ""),
                "recovery_action": hyp.get("recovery_action", ""),
            }
        )
    return {"hypotheses": rows}


def validate_hypothesis_evidence_pack(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    hypotheses = evidence_pack.get("hypotheses", []) if isinstance(evidence_pack, dict) else []
    if not isinstance(hypotheses, list) or not hypotheses:
        return {"valid": False, "errors": ["missing_hypotheses"], "hypotheses_checked": 0}
    required_fields = {
        "hypothesis_id",
        "claim",
        "status",
        "quant_metrics",
        "effect_metrics",
        "method_trace",
        "evidence_sources",
        "consistency",
        "reason_code",
        "recovery_action",
    }
    for idx, item in enumerate(hypotheses):
        if not isinstance(item, dict):
            errors.append(f"hypothesis[{idx}]_not_object")
            continue
        missing = sorted([k for k in required_fields if k not in item])
        if missing:
            errors.append(f"hypothesis[{idx}]_missing_fields:{','.join(missing)}")
        if not isinstance(item.get("quant_metrics"), list):
            errors.append(f"hypothesis[{idx}]_quant_metrics_not_list")
        if not isinstance(item.get("effect_metrics"), list):
            errors.append(f"hypothesis[{idx}]_effect_metrics_not_list")
        if not isinstance(item.get("method_trace"), list):
            errors.append(f"hypothesis[{idx}]_method_trace_not_list")
        if not isinstance(item.get("evidence_sources"), list):
            errors.append(f"hypothesis[{idx}]_evidence_sources_not_list")
        if not isinstance(item.get("consistency"), dict):
            errors.append(f"hypothesis[{idx}]_consistency_not_object")
        for midx, metric in enumerate(item.get("quant_metrics", []) if isinstance(item.get("quant_metrics"), list) else []):
            if not isinstance(metric, dict):
                errors.append(f"hypothesis[{idx}]_quant_metric[{midx}]_not_object")
                continue
            for key in ("name", "value", "unit", "threshold", "direction"):
                if key not in metric:
                    errors.append(f"hypothesis[{idx}]_quant_metric[{midx}]_missing_{key}")
        for eidx, src in enumerate(item.get("evidence_sources", []) if isinstance(item.get("evidence_sources"), list) else []):
            if isinstance(src, dict):
                if "path" not in src:
                    errors.append(f"hypothesis[{idx}]_evidence_source[{eidx}]_missing_path")
            elif not isinstance(src, str):
                errors.append(f"hypothesis[{idx}]_evidence_source[{eidx}]_invalid_type")
    return {"valid": len(errors) == 0, "errors": errors, "hypotheses_checked": len(hypotheses)}
