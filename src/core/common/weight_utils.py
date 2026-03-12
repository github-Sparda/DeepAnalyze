"""权重调整工具函数.

提供统一的权重调整逻辑，减少代码重复.
"""

from typing import Any


def adjust_weights_by_p_value(
    weights: dict[str, float],
    p_value: float,
    source_keyword: str = "stats",
    strong_threshold: float = 0.01,
    weak_threshold: float = 0.05,
    strong_multiplier: float = 1.3,
    weak_multiplier: float = 1.1
) -> None:
    """根据p值调整权重.

    Args:
        weights: 权重字典
        p_value: p值
        source_keyword: 源关键词
        strong_threshold: 强显著性阈值
        weak_threshold: 弱显著性阈值
        strong_multiplier: 强显著性乘数
        weak_multiplier: 弱显著性乘数
    """
    if p_value < strong_threshold:
        for source in weights:
            if source_keyword in source:
                weights[source] *= strong_multiplier
    elif p_value < weak_threshold:
        for source in weights:
            if source_keyword in source:
                weights[source] *= weak_multiplier


def adjust_weights_by_auc(
    weights: dict[str, float],
    auc: float,
    source_keyword: str = "model",
    strong_threshold: float = 0.9,
    weak_threshold: float = 0.8,
    strong_multiplier: float = 1.3,
    weak_multiplier: float = 1.1
) -> None:
    """根据AUC调整权重.

    Args:
        weights: 权重字典
        auc: AUC值
        source_keyword: 源关键词
        strong_threshold: 强AUC阈值
        weak_threshold: 弱AUC阈值
        strong_multiplier: 强AUC乘数
        weak_multiplier: 弱AUC乘数
    """
    if auc > strong_threshold:
        for source in weights:
            if source_keyword in source:
                weights[source] *= strong_multiplier
    elif auc > weak_threshold:
        for source in weights:
            if source_keyword in source:
                weights[source] *= weak_multiplier


def adjust_weights_by_correlation(
    weights: dict[str, float],
    corr: float,
    source_keyword: str = "correlation",
    strong_threshold: float = 0.8,
    weak_threshold: float = 0.6,
    strong_multiplier: float = 1.3,
    weak_multiplier: float = 1.1
) -> None:
    """根据相关系数调整权重.

    Args:
        weights: 权重字典
        corr: 相关系数
        source_keyword: 源关键词
        strong_threshold: 强相关阈值
        weak_threshold: 弱相关阈值
        strong_multiplier: 强相关乘数
        weak_multiplier: 弱相关乘数
    """
    if corr > strong_threshold:
        for source in weights:
            if source_keyword in source:
                weights[source] *= strong_multiplier
    elif corr > weak_threshold:
        for source in weights:
            if source_keyword in source:
                weights[source] *= weak_multiplier


def adjust_weights_by_metric(
    weights: dict[str, float],
    metric_value: float,
    metric_name: str,
    source_keyword: str,
    thresholds: list[tuple[float, float]],
    mode: str = "higher_is_better"
) -> None:
    """通用权重调整函数.

    Args:
        weights: 权重字典
        metric_value: 指标值
        metric_name: 指标名称
        source_keyword: 源关键词
        thresholds: 阈值和乘数列表 [(threshold, multiplier), ...]
        mode: 模式，"higher_is_better" 或 "lower_is_better"
    """
    for threshold, multiplier in thresholds:
        if mode == "higher_is_better":
            if metric_value > threshold:
                for source in weights:
                    if source_keyword in source:
                        weights[source] *= multiplier
                break
        else:  # lower_is_better
            if metric_value < threshold:
                for source in weights:
                    if source_keyword in source:
                        weights[source] *= multiplier
                break
