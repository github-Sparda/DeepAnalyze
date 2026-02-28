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
    "path_conflict": "run_third_path_and_compare_stability",
    "metric_missing": "rerun_missing_step_and_verify_outputs",
    "threshold_not_met": "adjust_method_or_data_processing_and_rerun",
    "performance_gap": "improve_label_quality_and_feature_strategy_then_rerun",
}

GATE_RULE_TYPE_RECOVERY: dict[str, str] = {
    "significance_and_effect": "add_effect_size_and_multiple_testing_control",
    "predictive_performance": "improve_label_quality_and_cross_validation",
    "correlation_structure": "add_rank_based_or_sparse_network_validation",
    "embedding_structure": "add_cluster_quality_and_group_separation_metrics",
    "generic_evidence": "add_quantitative_metrics_and_secondary_path",
}

GATE_RULE_TYPE_EXPECTED_ARTIFACTS: dict[str, list[str]] = {
    "significance_and_effect": ["result/stats_results.json", "result/multiple_testing.json"],
    "predictive_performance": ["result/model_eval.json", "result/cv_results.json"],
    "correlation_structure": ["result/correlation.json", "plots/network.png"],
    "embedding_structure": ["result/dimensionality.json", "result/clustering.json"],
    "generic_evidence": ["result/hypothesis_evidence_pack.json"],
}


def default_gate_calibration_profiles() -> dict[str, dict[str, Any]]:
    return {
        "strict": {
            "significance_count_min": 2.0,
            "primary_performance_min": 0.7,
            "secondary_performance_min": 0.68,
            "corr_strength_min": 0.6,
            "corr_edge_min": 2.0,
            "cluster_count_min": 2.0,
            "generic_quant_min": 3,
        },
        "standard": {
            "significance_count_min": 1.0,
            "primary_performance_min": 0.6,
            "secondary_performance_min": 0.6,
            "corr_strength_min": 0.5,
            "corr_edge_min": 1.0,
            "cluster_count_min": 2.0,
            "generic_quant_min": 2,
        },
        "exploratory": {
            "significance_count_min": 1.0,
            "primary_performance_min": 0.55,
            "secondary_performance_min": 0.5,
            "corr_strength_min": 0.4,
            "corr_edge_min": 1.0,
            "cluster_count_min": 1.0,
            "generic_quant_min": 1,
        },
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


def default_hypothesis_profile_registry() -> dict[str, dict[str, Any]]:
    return {
        "difference": {
            "title": "分组差异检验",
            "hypothesis": "不同分组之间存在统计学显著差异特征。",
            "claim": "组间存在显著差异标志物",
            "primary_method_family": "parametric_test",
            "secondary_method_family": "nonparametric_or_fdr",
            "visual_artifacts": ["plots/volcano_plot.png", "plots/top_features_bar.png"],
            "aliases": ["差异", "显著", "检验", "p值", "q值", "difference", "differential"],
        },
        "predictive": {
            "title": "预测性能验证",
            "hypothesis": "特征组合可用于预测或区分目标分组。",
            "claim": "多特征组合具备诊断预测力",
            "primary_method_family": "feature_modeling",
            "secondary_method_family": "cross_validation",
            "visual_artifacts": ["result/model_eval.json", "result/cv_results.json", "result/feature_selection.json"],
            "aliases": ["预测", "分类", "模型", "auc", "accuracy", "predict", "classification"],
        },
        "correlation": {
            "title": "相关结构验证",
            "hypothesis": "关键变量之间存在可解释的相关结构。",
            "claim": "变量间存在结构化相关网络",
            "primary_method_family": "pearson_network",
            "secondary_method_family": "rank_or_sparse_network",
            "visual_artifacts": ["plots/heatmap.png", "plots/network.png"],
            "aliases": ["相关", "网络", "协同", "corr", "correlation", "network"],
        },
        "embedding": {
            "title": "低维结构验证",
            "hypothesis": "样本在降维或聚类空间中存在稳定结构。",
            "claim": "样本在降维空间中存在可解释结构",
            "primary_method_family": "pca_cluster",
            "secondary_method_family": "tsne_or_umap_cluster",
            "visual_artifacts": ["plots/embedding_pca.png", "plots/embedding_tsne.png", "plots/scatter.png"],
            "aliases": ["聚类", "降维", "pca", "tsne", "umap", "embedding", "cluster"],
        },
        "generic": {
            "title": "通用证据验证",
            "hypothesis": "当前问题可通过多路径验证获得定量证据支持。",
            "claim": "已形成可追溯的定量证据",
            "primary_method_family": "primary",
            "secondary_method_family": "secondary",
            "visual_artifacts": [],
            "aliases": [],
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


def load_hypothesis_profile_registry(session_dir: Path) -> dict[str, dict[str, Any]]:
    return _load_dictionary(
        session_dir,
        "hypothesis_profile_registry.json",
        default_hypothesis_profile_registry(),
    )


def infer_hypothesis_profile_key(
    title: str = "",
    hypothesis_text: str = "",
    metric_names: list[str] | None = None,
    explicit_key: str = "",
    registry: dict[str, dict[str, Any]] | None = None,
) -> str:
    reg = registry if isinstance(registry, dict) and registry else default_hypothesis_profile_registry()
    key = str(explicit_key or "").strip().lower()
    if key in reg:
        return key
    metric_tokens = " ".join(str(x).lower() for x in (metric_names or []) if str(x).strip())
    haystack = f"{title} {hypothesis_text} {metric_tokens}".lower()
    for profile_key, meta in reg.items():
        aliases = meta.get("aliases", []) if isinstance(meta, dict) else []
        if any(str(alias).strip().lower() in haystack for alias in aliases):
            return profile_key
    return "generic"


def resolve_hypothesis_profile(
    session_dir: Path,
    title: str = "",
    hypothesis_text: str = "",
    metric_names: list[str] | None = None,
    explicit_key: str = "",
) -> dict[str, Any]:
    registry = load_hypothesis_profile_registry(session_dir)
    key = infer_hypothesis_profile_key(
        title=title,
        hypothesis_text=hypothesis_text,
        metric_names=metric_names,
        explicit_key=explicit_key,
        registry=registry,
    )
    profile = registry.get(key, registry.get("generic", {}))
    merged = dict(profile)
    merged["key"] = key
    return merged


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
        if any(k in name for k in ("corr", "accuracy", "auc", "fold", "diff", "effect", "change", "log2")):
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


def _to_float(value: Any) -> float | None:
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except Exception:
        return None


def _detect_gate_rule_type(quant: list[dict[str, Any]], method_trace: list[dict[str, Any]]) -> str:
    names = {str(item.get("name", "")).lower() for item in quant if isinstance(item, dict)}
    categories = {str(item.get("category", "")).lower() for item in quant if isinstance(item, dict)}
    families = {
        str(item.get("method_family", "")).lower()
        for item in method_trace
        if isinstance(item, dict) and str(item.get("method_family", "")).strip()
    }
    if "significance" in categories or any("p_" in n or "q_" in n for n in names):
        return "significance_and_effect"
    if "performance" in categories or any(n in {"auc", "centroid_accuracy", "cv_mean_accuracy"} for n in names):
        return "predictive_performance"
    if "correlation" in categories or any("corr" in n for n in names):
        return "correlation_structure"
    if "clustering" in categories or any("cluster" in n or "embedding" in n for n in names):
        return "embedding_structure"
    if any("model" in family or "cross_validation" in family for family in families):
        return "predictive_performance"
    if any("network" in family or "corr" in family for family in families):
        return "correlation_structure"
    return "generic_evidence"


def _metric_index(quant: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for metric in quant:
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("name", "")).strip().lower()
        if name:
            index[name] = metric
    return index


def _gate_checks_for_type(
    gate_rule_type: str,
    quant: list[dict[str, Any]],
    effects: list[dict[str, Any]],
    consistency: str,
    status: str,
    thresholds: dict[str, Any] | None = None,
) -> tuple[dict[str, bool], dict[str, Any], list[str]]:
    metric_map = _metric_index(quant)
    thresholds = thresholds or {}
    check_details: dict[str, Any] = {}
    required_checks: list[str] = []

    def _check(name: str, passed: bool, detail: Any) -> None:
        check_details[name] = detail
        checks[name] = bool(passed)

    checks: dict[str, bool] = {}
    _check("has_dual_path_status", status not in {"failed", "skipped"}, {"status": status})
    _check("path_consistency", consistency != "conflict", {"consistency": consistency})

    if gate_rule_type == "significance_and_effect":
        required_checks.extend(["has_significance_metric", "has_effect_metric", "significance_count_ge_min"])
        sig = metric_map.get("significant_p_lt_0_05") or metric_map.get("q_lt_0_05")
        sig_value = _to_float(sig.get("value")) if isinstance(sig, dict) else None
        sig_min = float(thresholds.get("significance_count_min", 1.0))
        _check("has_significance_metric", sig_value is not None, {"value": sig_value})
        _check("has_effect_metric", bool(effects), {"effect_metric_count": len(effects)})
        _check(
            "significance_count_ge_min",
            (sig_value or 0.0) >= sig_min,
            {"value": sig_value, "threshold": f">={sig_min}"},
        )
    elif gate_rule_type == "predictive_performance":
        required_checks.extend(
            [
                "has_primary_performance",
                "has_secondary_performance",
                "primary_performance_ge_min",
                "secondary_performance_ge_min",
            ]
        )
        primary = metric_map.get("centroid_accuracy") or metric_map.get("auc")
        secondary = metric_map.get("cv_mean_accuracy")
        p_val = _to_float(primary.get("value")) if isinstance(primary, dict) else None
        s_val = _to_float(secondary.get("value")) if isinstance(secondary, dict) else None
        p_min = float(thresholds.get("primary_performance_min", 0.6))
        s_min = float(thresholds.get("secondary_performance_min", 0.6))
        _check("has_primary_performance", p_val is not None, {"value": p_val})
        _check("has_secondary_performance", s_val is not None, {"value": s_val})
        _check(
            "primary_performance_ge_min",
            (p_val or 0.0) >= p_min,
            {"value": p_val, "threshold": f">={p_min}"},
        )
        _check(
            "secondary_performance_ge_min",
            (s_val or 0.0) >= s_min,
            {"value": s_val, "threshold": f">={s_min}"},
        )
    elif gate_rule_type == "correlation_structure":
        required_checks.extend(["has_corr_strength", "has_corr_edge_support", "corr_strength_ge_min", "corr_edge_ge_min"])
        strongest = metric_map.get("strongest_abs_corr")
        edges = metric_map.get("abs_corr_gt_0_7_edges") or metric_map.get("abs_corr_gt_0_5_edges")
        strongest_val = _to_float(strongest.get("value")) if isinstance(strongest, dict) else None
        edge_val = _to_float(edges.get("value")) if isinstance(edges, dict) else None
        corr_min = float(thresholds.get("corr_strength_min", 0.5))
        edge_min = float(thresholds.get("corr_edge_min", 1.0))
        _check("has_corr_strength", strongest_val is not None, {"value": strongest_val})
        _check("has_corr_edge_support", edge_val is not None, {"value": edge_val})
        _check(
            "corr_strength_ge_min",
            (strongest_val or 0.0) >= corr_min,
            {"value": strongest_val, "threshold": f">={corr_min}"},
        )
        _check(
            "corr_edge_ge_min",
            (edge_val or 0.0) >= edge_min,
            {"value": edge_val, "threshold": f">={edge_min}"},
        )
    elif gate_rule_type == "embedding_structure":
        required_checks.extend(["has_cluster_or_embedding_metric"])
        has_cluster = "cluster_count" in metric_map and _to_float(metric_map["cluster_count"].get("value")) is not None
        has_embedding = any("embedding" in name for name in metric_map.keys())
        cluster_val = _to_float(metric_map["cluster_count"].get("value")) if "cluster_count" in metric_map else None
        cluster_min = float(thresholds.get("cluster_count_min", 2.0))
        _check(
            "has_cluster_or_embedding_metric",
            has_cluster or has_embedding,
            {"cluster_count": cluster_val, "has_embedding_metric": has_embedding},
        )
        _check(
            "cluster_count_ge_min",
            (cluster_val or 0.0) >= cluster_min if cluster_val is not None else False,
            {"value": cluster_val, "threshold": f">={cluster_min}"},
        )
    else:
        required_checks.extend(["quant_metric_count_ge_2"])
        quant_min = int(thresholds.get("generic_quant_min", 2))
        _check(
            "quant_metric_count_ge_min",
            len(quant) >= quant_min,
            {"count": len(quant), "threshold": f">={quant_min}"},
        )
        _check("effect_or_consistency_support", bool(effects) or consistency == "consistent", {"effect_metric_count": len(effects), "consistency": consistency})

    return checks, check_details, required_checks


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
        base_quant = item.get("quant_metrics", {}) if isinstance(item.get("quant_metrics"), dict) else {}
        contrast = contrast_map.get(hid, {})
        # Merge path-level metrics as fallback quantitative evidence for gate checks.
        for path_key in ("path_a", "path_b"):
            path_payload = contrast.get(path_key, {}) if isinstance(contrast.get(path_key), dict) else {}
            path_metrics = path_payload.get("metrics", {}) if isinstance(path_payload.get("metrics"), dict) else {}
            for name, value in path_metrics.items():
                key = str(name).strip()
                if key and key not in base_quant:
                    base_quant[key] = value
        quant_metrics = _annotated_quant_metrics(base_quant, metric_dict)
        effect_metrics = _effect_metrics_from_quant(quant_metrics)
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
                "hypothesis_type": str(item.get("hypothesis_type", "")).strip(),
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


def build_hypothesis_gate_report(
    evidence_pack: dict[str, Any],
    calibration_profile: str = "standard",
    calibration_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profiles = default_gate_calibration_profiles()
    profile_name = calibration_profile if calibration_profile in profiles else "standard"
    thresholds = dict(profiles.get(profile_name, profiles["standard"]))
    if isinstance(calibration_overrides, dict):
        thresholds.update(calibration_overrides)
    rows: list[dict[str, Any]] = []

    def _infer_reason_code(
        failed_checks: list[str],
        consistency: str,
        gate_rule_type: str,
        existing: str,
    ) -> str:
        if not failed_checks:
            return ""
        if existing:
            return existing
        if consistency == "conflict" or "path_consistency" in failed_checks:
            return "path_conflict"
        if any(name.startswith("has_") for name in failed_checks):
            return "metric_missing"
        if any(name.endswith("_ge_min") for name in failed_checks):
            if gate_rule_type == "predictive_performance":
                return "performance_gap"
            return "threshold_not_met"
        if "has_dual_path_status" in failed_checks:
            return "missing_artifact"
        return "assumption_violation"

    def _build_recovery_plan(gate_rule_type: str, failed_checks: list[str], reason_code: str) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []
        if not failed_checks:
            return plan
        expected = GATE_RULE_TYPE_EXPECTED_ARTIFACTS.get(gate_rule_type, GATE_RULE_TYPE_EXPECTED_ARTIFACTS["generic_evidence"])
        if reason_code in {"metric_missing", "missing_artifact"}:
            plan.append(
                {
                    "priority": "P0",
                    "action": "rerun_missing_modules_and_verify_expected_artifacts",
                    "expected_artifacts": expected,
                }
            )
        if reason_code in {"threshold_not_met", "performance_gap"}:
            plan.append(
                {
                    "priority": "P1",
                    "action": "adjust_method_or_feature_strategy_then_rerun",
                    "expected_artifacts": expected,
                }
            )
        if reason_code in {"path_conflict", "method_conflict"}:
            plan.append(
                {
                    "priority": "P1",
                    "action": "run_third_validation_path_for_conflict_resolution",
                    "expected_artifacts": expected,
                }
            )
        if not plan:
            plan.append(
                {
                    "priority": "P2",
                    "action": "manual_review_and_relabel_if_needed",
                    "expected_artifacts": expected,
                }
            )
        return plan

    for hyp in evidence_pack.get("hypotheses", []) if isinstance(evidence_pack, dict) else []:
        if not isinstance(hyp, dict):
            continue
        quant = hyp.get("quant_metrics", []) if isinstance(hyp.get("quant_metrics"), list) else []
        effects = hyp.get("effect_metrics", []) if isinstance(hyp.get("effect_metrics"), list) else []
        method_trace = hyp.get("method_trace", []) if isinstance(hyp.get("method_trace"), list) else []
        status = str(hyp.get("status", ""))
        consistency = (hyp.get("consistency", {}) if isinstance(hyp.get("consistency"), dict) else {}).get("flag", "unknown")
        gate_rule_type = _detect_gate_rule_type(quant, method_trace)
        checks, check_details, required_checks = _gate_checks_for_type(
            gate_rule_type,
            quant,
            effects,
            consistency,
            status,
            thresholds,
        )
        required_pass = all(checks.get(name, False) for name in required_checks) if required_checks else True
        consistency_pass = checks.get("path_consistency", False)
        status_pass = checks.get("has_dual_path_status", False)
        if required_pass and consistency_pass and status_pass:
            gate_status = "pass"
        elif any(checks.values()):
            gate_status = "partial"
        else:
            gate_status = "fail"
        failed_checks = [name for name, passed in checks.items() if not passed]
        reason_code = str(hyp.get("reason_code", "")).strip()
        recovery_action = str(hyp.get("recovery_action", "")).strip()
        reason_code = _infer_reason_code(failed_checks, consistency, gate_rule_type, reason_code)
        if not failed_checks:
            recovery_action = ""
        if not recovery_action and reason_code:
            recovery_action = REASON_RECOVERY_MAP.get(reason_code, "")
        if not recovery_action and failed_checks:
            recovery_action = GATE_RULE_TYPE_RECOVERY.get(gate_rule_type, "")
        recovery_plan = _build_recovery_plan(gate_rule_type, failed_checks, reason_code)
        decision_evidence = []
        for check_name in required_checks:
            decision_evidence.append(
                {
                    "check": check_name,
                    "passed": bool(checks.get(check_name, False)),
                    "detail": check_details.get(check_name, {}),
                }
            )
        decision_trace = (
            f"profile={profile_name}; rule={gate_rule_type}; "
            f"required={','.join(required_checks)}; failed={','.join(failed_checks)}"
        )
        rows.append(
            {
                "hypothesis_id": hyp.get("hypothesis_id", ""),
                "gate_status": gate_status,
                "gate_rule_type": gate_rule_type,
                "calibration_profile": profile_name,
                "checks": checks,
                "check_details": check_details,
                "required_checks": required_checks,
                "failed_checks": failed_checks,
                "reason_code": reason_code,
                "recovery_action": recovery_action,
                "recovery_plan": recovery_plan,
                "decision_evidence": decision_evidence,
                "decision_trace": decision_trace,
            }
        )
    return {"hypotheses": rows, "calibration_profile": profile_name, "thresholds": thresholds}


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
