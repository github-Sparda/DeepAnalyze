from __future__ import annotations

import re
from typing import Any


METRIC_EXPLANATION: dict[str, dict[str, str]] = {
    "majority_accuracy": {
        "name": "多数类基线准确率",
        "definition": "始终预测样本最多类别时的准确率基线",
    },
    "centroid_accuracy": {
        "name": "质心分类准确率",
        "definition": "最近质心分类器在当前数据上的准确率",
    },
    "cv_mean_accuracy": {
        "name": "交叉验证平均准确率",
        "definition": "各折验证准确率的平均值",
    },
    "cv_std_accuracy": {
        "name": "交叉验证准确率标准差",
        "definition": "各折准确率的离散程度，越小通常越稳定",
    },
    "auc": {
        "name": "AUC",
        "definition": "模型区分正负样本能力（ROC 曲线下面积）",
    },
    "f1": {
        "name": "F1 分数",
        "definition": "精确率与召回率的调和平均，用于平衡漏检与误检",
    },
    "p_value": {
        "name": "p 值",
        "definition": "在零假设成立时观察到当前差异或更极端结果的概率",
    },
    "q_value": {
        "name": "q 值",
        "definition": "多重比较校正后的显著性指标，控制假阳性率",
    },
    "fdr": {
        "name": "FDR",
        "definition": "错误发现率估计，反映多重比较下假阳性占比",
    },
    "effect_size": {
        "name": "效应量",
        "definition": "差异强度的量化指标，用于判断统计显著之外的实际意义",
    },
    "fold_change": {
        "name": "Fold Change",
        "definition": "两组均值（或中位数）倍数变化，反映变化幅度",
    },
    "log2_fold_change": {
        "name": "Log2 Fold Change",
        "definition": "Fold Change 的对数尺度，用于对称表达上调与下调幅度",
    },
    "correlation_coefficient": {
        "name": "相关系数",
        "definition": "两个变量线性或秩相关强度的量化值",
    },
    "network_density": {
        "name": "网络密度",
        "definition": "网络中实际边数占最大可能边数的比例",
    },
    "component_count": {
        "name": "连通分量数量",
        "definition": "网络中相互连通子图的数量，反映结构离散程度",
    },
    "significant_p_lt_0_05": {
        "name": "显著特征数 (p<0.05)",
        "definition": "在显著性检验下达到 p<0.05 的特征数量",
    },
    "q_lt_0_05": {
        "name": "显著特征数 (q<0.05)",
        "definition": "经多重比较校正后达到 q<0.05 的特征数量",
    },
    "strongest_abs_corr": {
        "name": "最强绝对相关系数",
        "definition": "变量对之间最大相关强度（绝对值）",
    },
    "abs_corr_gt_0_7_edges": {
        "name": "|corr|>0.7 边数",
        "definition": "相关网络中强相关边的数量",
    },
    "cluster_count": {
        "name": "聚类簇数量",
        "definition": "聚类结果中的簇数量",
    },
    "silhouette": {
        "name": "轮廓系数",
        "definition": "聚类内紧凑度与簇间分离度的综合指标",
    },
    "cluster_separation": {
        "name": "簇间分离度",
        "definition": "不同簇之间的可分离程度",
    },
    "tested_features": {
        "name": "检验特征数",
        "definition": "本次分析中实际检验的特征总数",
    },
    "max_abs_log2_fold_change": {
        "name": "最大绝对 Log2 Fold Change",
        "definition": "处理组相对对照组最大变化倍数的对数尺度（log2），|log2FC|>1 表示显著变化",
    },
    "mean_abs_log2_fold_change": {
        "name": "平均绝对 Log2 Fold Change",
        "definition": "所有特征 log2FC 绝对值的平均，反映整体变化幅度",
    },
    "max_abs_fold_change": {
        "name": "最大绝对 Fold Change",
        "definition": "处理组相对对照组最大倍数变化，FC>2 表示上调，FC<0.5 表示下调",
    },
    "mean_abs_fold_change": {
        "name": "平均绝对 Fold Change",
        "definition": "所有特征 FC 绝对值的平均，反映整体倍数变化水平",
    },
    "max_abs_mean_diff": {
        "name": "最大绝对均值差",
        "definition": "处理组与对照组最大绝对均值差，反映绝对差异大小",
    },
    "mean_abs_mean_diff": {
        "name": "平均绝对均值差",
        "definition": "所有特征均值差异绝对值的平均，反映整体差异水平",
    },
    "top_features": {
        "name": "Top 特征列表",
        "definition": "按统计显著性或效应量排序的前列特征",
    },

}

GATE_RULE_TYPE_EXPLANATION: dict[str, str] = {
    "significance_and_effect": "显著性与效应量联合判定：要求显著性证据与效应量证据同时成立。",
    "predictive_performance": "预测性能判定：要求主性能与交叉验证稳定性同时达到最低要求。",
    "correlation_structure": "相关结构判定：要求相关强度与网络支撑证据同时满足。",
    "embedding_structure": "嵌入结构判定：要求存在分离/聚类类证据，避免仅凭可视化印象下结论。",
    "generic_evidence": "通用证据判定：用于无法归入特定方法族时的基础约束。",
}

GATE_STATUS_EXPLANATION: dict[str, str] = {
    "pass": "通过：核心检查项全部满足，当前证据可以支持阶段性结论。",
    "partial": "部分通过：已有部分证据，但关键检查仍有缺口，结论应限定为“有限支持”。",
    "fail": "未通过：关键检查未满足，当前不应输出确定性结论。",
}

FAILED_CHECK_EXPLANATION: dict[str, str] = {
    "has_dual_path_status": "双路径执行状态检查：确认两条验证路径都已产出可用状态。",
    "path_consistency": "路径一致性检查：确认路径 A 与路径 B 的结论方向一致。",
    "has_significance_metric": "显著性指标存在性检查：确认至少有显著性统计量可用。",
    "has_effect_metric": "效应量证据检查：确认不仅“显著”，还具备效应强度证据。",
    "significance_count_ge_min": "显著特征数量检查：确认显著特征数量达到最小阈值。",
    "has_primary_performance": "主性能指标存在性检查：确认存在主模型性能指标（如 centroid/AUC）。",
    "has_secondary_performance": "次性能指标存在性检查：确认存在交叉验证性能指标。",
    "primary_performance_ge_min": "主性能检查：确认主性能达到最低阈值。",
    "secondary_performance_ge_min": "交叉验证性能检查：确认交叉验证平均性能达到最低阈值。",
    "has_corr_strength": "相关强度指标检查：确认存在相关强度量化结果。",
    "has_corr_edge_support": "相关网络边支撑检查：确认强相关边数量支持网络结构判断。",
    "corr_strength_ge_min": "相关强度检查：确认最强相关达到最低阈值。",
    "corr_edge_ge_min": "相关边数量检查：确认强相关边数量达到最低阈值。",
    "has_cluster_or_embedding_metric": "聚类/嵌入证据检查：确认存在可用于结构分离判断的指标。",
    "cluster_count_ge_min": "聚类数量检查：确认簇数达到最低要求。",
    "quant_metric_count_ge_min": "定量指标数量检查：确认指标数量足够支持结论。",
    "effect_or_consistency_support": "效应量或一致性补充检查：确认至少具备效应量证据或路径一致性。",
}

REASON_CODE_EXPLANATION: dict[str, str] = {
    "metric_missing": "缺少关键指标，当前证据链不完整。",
    "threshold_not_met": "指标已产出，但未达到预设判定阈值。",
    "performance_gap": "预测性能存在缺口，需要改进特征或标签质量。",
    "path_conflict": "多路径结论冲突，需要进行路径对齐和复核。",
    "method_conflict": "方法间结论冲突，建议补充第三路径验证。",
    "missing_artifact": "关键产物缺失，需补跑相关步骤。",
    "execution_error": "执行阶段异常，需要修复代码后重跑。",
    "assumption_violation": "统计/建模前提可能不满足，需要更换方法或转换数据。",
}

FAILED_CHECK_REVIEW_STEPS: dict[str, list[str]] = {
    "path_consistency": [
        "核对路径 A/B 的特征清洗与标准化参数是否一致。",
        "核对两条路径使用的标签列与标签映射是否一致。",
        "对同一批样本输出路径级中间结果并逐项比对。",
    ],
    "primary_performance_ge_min": [
        "检查训练/验证划分是否分层并避免信息泄露。",
        "核对核心特征是否存在异常值或缺失值泄漏。",
        "增加稳健模型或特征筛选后重跑并比较变化。",
    ],
    "secondary_performance_ge_min": [
        "检查各折样本量与类别比例是否稳定。",
        "核对随机种子与交叉验证策略是否固定。",
        "记录折间波动并定位异常折对应样本。",
    ],
    "has_effect_metric": [
        "补充效应量指标（如 fold change、Cohen's d 或相关强度）。",
        "将显著性结果与效应方向联合汇报。",
    ],
}


def _to_float(value: Any) -> float | None:
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except Exception:
        return None


def _eval_threshold(value: Any, threshold: str) -> tuple[str, str]:
    v = _to_float(value)
    text = str(threshold or "").strip()
    if v is None or not text:
        return ("unknown", "")
    m = re.match(r"^(>=|<=|>|<|==)\s*(-?\d+(?:\.\d+)?)$", text)
    if not m:
        return ("unknown", "")
    op, raw = m.group(1), float(m.group(2))
    if op == ">=":
        passed = v >= raw
    elif op == "<=":
        passed = v <= raw
    elif op == ">":
        passed = v > raw
    elif op == "<":
        passed = v < raw
    else:
        passed = v == raw
    relation = f"{v:.4g} {op} {raw:.4g}"
    return ("pass" if passed else "fail", relation)


def metric_narrative(metric: dict[str, Any], style_seed: int = 0) -> str:
    key = str(metric.get("name", "")).strip().lower()
    unit = str(metric.get("unit", "")).strip()
    threshold = str(metric.get("threshold", "")).strip()
    value = metric.get("value")
    direction = str(metric.get("direction", "")).strip().lower()
    explain = METRIC_EXPLANATION.get(key, {})
    display_name_raw = metric.get("display_name", "")
    explain_name = explain.get("name", "")
    if display_name_raw and display_name_raw.lower() != key.lower() and display_name_raw != key:
        display_name = display_name_raw
    elif explain_name:
        display_name = explain_name
    else:
        display_name = key
    definition = explain.get("definition", "")
    judgement, relation = _eval_threshold(value, threshold)

    v = _to_float(value)
    value_text = f"{v:.4g}" if v is not None else str(value)

    if v is not None:
        implication = _metric_implication_sentence(key, v)
    else:
        implication = ""

    if threshold:
        if judgement == "pass":
            verdict = f"✓ 通过（{relation}）"
        elif judgement == "fail":
            verdict = f"✗ 未达阈值（{relation}）"
        else:
            verdict = f"? 阈值{threshold}，比较失败"
    else:
        verdict = ""

    parts = [f"{display_name} = {value_text}"]
    if unit and unit not in ("ratio", "count", ""):
        parts[-1] += f" {unit}"

    llm_interpretation = _try_llm_interpretation(key, value)
    if llm_interpretation and not llm_interpretation.startswith(f"{key} ="):
        parts.append(llm_interpretation)
    elif definition:
        parts.append(definition)

    if verdict:
        parts.append(verdict)
    if implication:
        parts.append(implication)

    return " | ".join(parts)


def _try_llm_interpretation(metric_key: str, value: Any) -> str:
    """尝试使用LLM生成指标解读，失败时返回空字符串"""
    try:
        from src.core.reporting.metric_interpreter import LLMMetricInterpreter
        interpreter = LLMMetricInterpreter()
        return interpreter.interpret(metric_key, value)
    except Exception:
        return ""


def _metric_implication_sentence(metric_key: str, value: Any) -> str:
    v = _to_float(value)
    if v is None:
        return ""
    key = str(metric_key or "").lower()
    if key == "cv_std_accuracy":
        if v <= 0.02:
            return "交叉验证折间波动较小，模型稳定性较好。"
        if v <= 0.05:
            return "交叉验证存在一定波动，稳定性中等。"
        return "交叉验证波动较大，模型稳定性不足。"
    if key in {"cv_mean_accuracy", "centroid_accuracy", "auc", "f1", "majority_accuracy"}:
        if v >= 0.8:
            return "性能表现较强。"
        if v >= 0.6:
            return "性能达到可用区间，但仍建议关注泛化风险。"
        return "性能偏弱，当前不宜给出强结论。"
    if key in {"p_value", "q_value", "fdr"}:
        if v < 0.01:
            return "显著性较强。"
        if v < 0.05:
            return "达到常见显著性阈值。"
        return "未达到常见显著性阈值。"
    if key in {"effect_size"}:
        av = abs(v)
        if av >= 0.8:
            return "效应强。"
        if av >= 0.5:
            return "效应中等。"
        if av >= 0.2:
            return "效应较小。"
        return "效应很弱。"
    if key in {"strongest_abs_corr", "correlation_coefficient"}:
        av = abs(v)
        if av >= 0.7:
            return "相关性较强。"
        if av >= 0.4:
            return "相关性中等。"
        return "相关性偏弱。"
    if key in {"silhouette", "cluster_separation"}:
        if v >= 0.5:
            return "聚类可分性较好。"
        if v >= 0.25:
            return "聚类可分性一般。"
        return "聚类可分性较弱。"
    return ""


def gate_rule_type_sentence(rule_type: str) -> str:
    key = str(rule_type or "").strip().lower()
    return GATE_RULE_TYPE_EXPLANATION.get(key, f"判定规则类型为 {key or 'generic_evidence'}，当前未配置详细中文解释。")


def gate_status_sentence(status: str) -> str:
    key = str(status or "").strip().lower()
    return GATE_STATUS_EXPLANATION.get(key, f"当前判定状态为 {key or 'unknown'}。")


def failed_check_sentence(check: str) -> str:
    key = str(check or "").strip()
    text = FAILED_CHECK_EXPLANATION.get(key, "")
    if text:
        return f"{text}（{key}）"
    return f"检查项 {key} 未通过，当前无详细中文释义。"


def reason_code_sentence(reason_code: str) -> str:
    key = str(reason_code or "").strip()
    text = REASON_CODE_EXPLANATION.get(key, "")
    if text:
        return f"{text}（{key}）"
    if key:
        return f"当前原因码为 {key}，尚未配置中文解释。"
    return ""


def has_failed_check_explanation(check: str) -> bool:
    return str(check or "").strip() in FAILED_CHECK_EXPLANATION


def has_reason_code_explanation(reason_code: str) -> bool:
    return str(reason_code or "").strip() in REASON_CODE_EXPLANATION


def recovery_action_sentence(action: str) -> str:
    raw = str(action or "").strip()
    if not raw:
        return ""
    mapping = {
        "rerun_missing_step_and_verify_outputs": "补跑缺失步骤并核对预期产物是否生成。",
        "run_third_path_and_compare_stability": "增加第三验证路径并对比稳定性，定位冲突来源。",
        "adjust_method_or_data_processing_and_rerun": "调整方法或数据处理策略后重跑，并比较判定结果变化。",
        "improve_label_quality_and_feature_strategy_then_rerun": "提升标签质量与特征策略后重跑评估。",
        "switch_nonparametric_or_transform_data": "切换到更稳健方法或先做数据变换再验证。",
        "invoke_code_repair_then_rerun": "先修复执行错误，再重跑验证流程。",
    }
    if raw in mapping:
        return f"{mapping[raw]}（{raw}）"
    humanized = raw.replace("_", " ").strip()
    return f"建议执行动作：{humanized}（{raw}）"


def failed_check_review_steps(check: str) -> list[str]:
    key = str(check or "").strip()
    return FAILED_CHECK_REVIEW_STEPS.get(key, [])


def detect_metric_conflicts_detailed(quant_metrics: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    quant_metrics = quant_metrics or []
    index: dict[str, float] = {}
    for item in quant_metrics:
        if not isinstance(item, dict):
            continue
        key = str(item.get("name", "")).strip().lower()
        value = _to_float(item.get("value"))
        if key and value is not None:
            index[key] = value

    findings: list[dict[str, Any]] = []
    centroid = index.get("centroid_accuracy")
    cv_mean = index.get("cv_mean_accuracy")
    if centroid is not None and cv_mean is not None and centroid <= 0.05 and cv_mean >= 0.6:
        findings.append(
            {
                "severity": "high",
                "title": "分类性能指标冲突",
                "evidence": f"centroid_accuracy={centroid:.4g}，cv_mean_accuracy={cv_mean:.4g}",
                "causes": [
                    "评估设置不一致（单次评估 vs 交叉验证）",
                    "标签映射或正负类定义不一致",
                    "模型路径的数据预处理配置不一致",
                ],
                "next_steps": [
                    "统一评估设置并重算 centroid 与 CV 指标",
                    "复核标签编码、类别顺序与训练/验证划分",
                    "导出并比对路径 A/B 的预处理参数快照",
                ],
            }
        )

    sig = index.get("significant_p_lt_0_05") or index.get("q_lt_0_05")
    strongest = index.get("strongest_abs_corr")
    if sig is not None and sig >= 1 and strongest is not None and abs(strongest) < 0.1:
        findings.append(
            {
                "severity": "medium",
                "title": "显著性与结构证据不一致",
                "evidence": f"significant_count={sig:.4g}，strongest_abs_corr={strongest:.4g}",
                "causes": [
                    "显著性结果可能受样本量驱动，效应强度不足",
                    "相关结构未能支持同方向的网络性证据",
                ],
                "next_steps": [
                    "补充效应量与置信区间，避免仅凭 p 值下结论",
                    "执行亚组/稳健性分析验证结论稳定性",
                ],
            }
        )
    return findings


def detect_metric_conflicts(quant_metrics: list[dict[str, Any]] | None) -> list[str]:
    details = detect_metric_conflicts_detailed(quant_metrics)
    return [
        f"{item.get('title','冲突')}：{item.get('evidence','')}。常见原因包括" + "、".join(item.get("causes", [])[:3]) + "。"
        for item in details
    ]
