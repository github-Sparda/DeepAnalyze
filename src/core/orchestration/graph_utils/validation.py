"""验证路径工具函数.

从原 graph.py 中提取的验证路径相关工具函数.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def infer_method_family(step_description: str) -> str:
    """从步骤描述推断方法家族.

    Args:
        step_description: 步骤描述文本

    Returns:
        方法家族名称
    """
    from src.core.common import METHOD_FAMILY_KEYWORDS

    text = str(step_description or "").lower()

    priority = [
        "survival",
        "time_series",
        "causal_inference",
        "correlation",
        "embedding",
        "machine_learning",
        "statistical_inference",
    ]
    for family in priority:
        keywords = METHOD_FAMILY_KEYWORDS.get(family, [])
        if any(k in text for k in keywords):
            return family

    return "statistical_inference"


def runtime_bound_validation_templates(method_family: str) -> list[dict[str, Any]]:
    """获取运行时绑定的验证模板.

    Args:
        method_family: 方法家族名称

    Returns:
        验证模板列表
    """
    templates: dict[str, list[dict[str, Any]]] = {
        "statistical_inference": [
            {"profile_key": "statistical_significance", "required": True},
            {"profile_key": "effect_size", "required": True},
            {"profile_key": "robustness", "required": False},
        ],
        "correlation": [
            {"profile_key": "correlation_strength", "required": True},
            {"profile_key": "correlation_significance", "required": True},
            {"profile_key": "sample_size", "required": False},
        ],
        "machine_learning": [
            {"profile_key": "model_performance", "required": True},
            {"profile_key": "cross_validation", "required": True},
            {"profile_key": "feature_importance", "required": False},
        ],
        "embedding": [
            {"profile_key": "cluster_quality", "required": True},
            {"profile_key": "dimensionality_reduction", "required": True},
            {"profile_key": "visualization", "required": False},
        ],
        "survival": [
            {"profile_key": "survival_curve", "required": True},
            {"profile_key": "hazard_ratio", "required": True},
            {"profile_key": "log_rank_test", "required": False},
        ],
        "time_series": [
            {"profile_key": "trend_analysis", "required": True},
            {"profile_key": "seasonality", "required": True},
            {"profile_key": "forecast_accuracy", "required": False},
        ],
        "causal_inference": [
            {"profile_key": "causal_effect", "required": True},
            {"profile_key": "balance_check", "required": True},
            {"profile_key": "sensitivity_analysis", "required": False},
        ],
    }

    return templates.get(method_family, templates.get("statistical_inference", []))


def canonical_hypothesis_identity(hypothesis: dict[str, Any]) -> str:
    """生成假设的规范身份标识.

    Args:
        hypothesis: 假设数据

    Returns:
        规范身份标识字符串
    """
    if not isinstance(hypothesis, dict):
        return ""

    hid = str(hypothesis.get("id", "")).strip().upper()
    title = str(hypothesis.get("title", "")).strip()
    hyp_type = str(hypothesis.get("hypothesis_type", "")).strip()

    parts = [p for p in [hid, title, hyp_type] if p]
    return "|".join(parts)


def parse_result_hypothesis_identity(result_row: dict[str, Any]) -> str:
    """从结果行解析假设身份标识.

    Args:
        result_row: 结果行数据

    Returns:
        假设身份标识字符串
    """
    if not isinstance(result_row, dict):
        return ""

    hid = str(result_row.get("hypothesis_id", "")).strip().upper()
    title = str(result_row.get("title", "") or result_row.get("hypothesis", "")).strip()
    hyp_type = str(result_row.get("hypothesis_type", "")).strip()

    parts = [p for p in [hid, title, hyp_type] if p]
    return "|".join(parts)


def align_plan_json_to_runtime_hypotheses(
    plan_json: dict[str, Any], runtime_hypotheses: list[dict[str, Any]]
) -> dict[str, Any]:
    """对齐计划JSON与运行时假设.

    Args:
        plan_json: 计划JSON数据
        runtime_hypotheses: 运行时假设列表

    Returns:
        对齐后的计划JSON
    """
    if not isinstance(plan_json, dict):
        return {"hypotheses": []}

    plan_hypotheses = plan_json.get("hypotheses", [])
    if not isinstance(plan_hypotheses, list):
        return plan_json

    # 构建运行时假设映射
    runtime_map: dict[str, dict[str, Any]] = {}
    for hyp in runtime_hypotheses:
        if isinstance(hyp, dict):
            hid = str(hyp.get("id", "")).strip().upper()
            if hid:
                runtime_map[hid] = hyp

    # 对齐假设
    aligned: list[dict[str, Any]] = []
    for hyp in plan_hypotheses:
        if not isinstance(hyp, dict):
            continue

        hid = str(hyp.get("id", "")).strip().upper()
        if hid and hid in runtime_map:
            # 合并运行时数据
            merged = {**hyp, **runtime_map[hid]}
            aligned.append(merged)
        else:
            aligned.append(hyp)

    return {**plan_json, "hypotheses": aligned}


def default_validation_paths(hypothesis_type: str) -> list[dict[str, Any]]:
    """获取默认验证路径.

    Args:
        hypothesis_type: 假设类型

    Returns:
        验证路径列表
    """
    paths: dict[str, list[dict[str, Any]]] = {
        "difference": [
            {"path": "statistical_test", "method": "t-test or Mann-Whitney U", "priority": 1},
            {"path": "effect_size", "method": "Cohen's d", "priority": 2},
            {"path": "robustness", "method": "Bootstrap", "priority": 3},
        ],
        "predictive": [
            {"path": "model_training", "method": "Cross-validation", "priority": 1},
            {"path": "performance", "method": "AUC/Accuracy", "priority": 2},
            {"path": "feature_importance", "method": "SHAP or Permutation", "priority": 3},
        ],
        "correlation": [
            {"path": "correlation_test", "method": "Pearson or Spearman", "priority": 1},
            {"path": "significance", "method": "P-value adjustment", "priority": 2},
            {"path": "sample_size", "method": "Power analysis", "priority": 3},
        ],
        "embedding": [
            {"path": "dimensionality_reduction", "method": "PCA or t-SNE", "priority": 1},
            {"path": "clustering", "method": "K-means or Hierarchical", "priority": 2},
            {"path": "visualization", "method": "2D/3D plot", "priority": 3},
        ],
    }

    return paths.get(hypothesis_type, paths.get("difference", []))


def merge_validation_paths(
    base_paths: list[dict[str, Any]], override_paths: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """合并验证路径.

    Args:
        base_paths: 基础验证路径
        override_paths: 覆盖验证路径

    Returns:
        合并后的验证路径列表
    """
    if not isinstance(base_paths, list):
        base_paths = []
    if not isinstance(override_paths, list):
        override_paths = []

    # 构建路径映射
    path_map: dict[str, dict[str, Any]] = {}
    for path in base_paths:
        if isinstance(path, dict):
            path_name = str(path.get("path", "")).strip()
            if path_name:
                path_map[path_name] = path

    # 应用覆盖
    for path in override_paths:
        if isinstance(path, dict):
            path_name = str(path.get("path", "")).strip()
            if path_name:
                if path_name in path_map:
                    path_map[path_name] = {**path_map[path_name], **path}
                else:
                    path_map[path_name] = path

    # 按优先级排序
    sorted_paths = sorted(path_map.values(), key=lambda x: x.get("priority", 999))

    return sorted_paths
