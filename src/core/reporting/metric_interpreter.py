"""
LLM Metric Interpreter - 指标解释器

使用LLM生成指标的自然语言解读。
"""

from __future__ import annotations

from typing import Any


METRIC_METADATA: dict[str, dict[str, Any]] = {
    "max_abs_log2_fold_change": {
        "name": "最大绝对 Log2 Fold Change",
        "calculation": "max(|log2(mean_treatment / mean_control)|)",
        "physical_meaning": "处理组相对对照组最大倍数变化的以2为底的对数尺度",
        "interpretation": {
            "high_positive": "处理组显著高于对照组（log2FC>1表示约2倍以上）",
            "high_negative": "处理组显著低于对照组（log2FC<-1表示约50%以下）",
            "near_zero": "两组无显著差异",
        },
        "common_thresholds": "|log2FC| > 1 为显著变化阈值",
        "unit": "log2 ratio",
    },
    "mean_abs_log2_fold_change": {
        "name": "平均绝对 Log2 Fold Change",
        "calculation": "mean(|log2(mean_treatment / mean_control)|)",
        "physical_meaning": "所有特征log2FC绝对值的平均，反映整体变化幅度",
        "interpretation": {
            "high": "整体变化幅度较大",
            "low": "整体变化幅度较小",
        },
        "unit": "log2 ratio",
    },
    "max_abs_fold_change": {
        "name": "最大绝对 Fold Change",
        "calculation": "max(|mean_treatment / mean_control|)",
        "physical_meaning": "处理组相对对照组最大倍数变化",
        "interpretation": {
            "high_positive": "处理组约是对照组的N倍（FC>2表示上调约2倍以上）",
            "high_negative": "处理组约是对照组的1/N（FC<0.5表示下调约50%以下）",
        },
        "common_thresholds": "FC > 2 或 FC < 0.5 表示显著变化",
        "unit": "fold change ratio",
    },
    "tested_features": {
        "name": "检验特征数",
        "calculation": "len(features)",
        "physical_meaning": "本次分析中实际检验的特征总数",
        "interpretation": {
            "adequate": "样本量充足",
        },
        "unit": "count",
    },
    "significant_p_lt_0_05": {
        "name": "显著特征数 (p<0.05)",
        "calculation": "count(features with p_value < 0.05)",
        "physical_meaning": "在显著性检验下达到 p<0.05 的特征数量",
        "interpretation": {
            "high_ratio": "较高比例的特征存在显著差异",
            "low_ratio": "较少特征存在显著差异",
        },
        "unit": "count",
    },
    "auc": {
        "name": "ROC曲线下面积 (AUC)",
        "calculation": "sklearn.metrics.roc_auc_score(y_true, y_pred_proba)",
        "physical_meaning": "模型区分正负样本的概率，0.5为随机，1.0为完美",
        "interpretation": {
            "0.5": "等同于随机猜测，无区分能力",
            "0.7-0.8": "有一定区分能力",
            "0.8-0.9": "区分能力较好",
            "0.9-1.0": "区分能力极强",
        },
        "common_thresholds": ">= 0.7 为可接受，>= 0.8 为较好",
        "unit": "ratio (0-1)",
    },
    "cv_mean_accuracy": {
        "name": "交叉验证平均准确率",
        "calculation": "mean(accuracy_scores across folds)",
        "physical_meaning": "各折准确率的平均，反映模型整体性能",
        "interpretation": {
            "high": "模型性能较好",
            "low": "模型性能较差",
        },
        "unit": "ratio (0-1)",
    },
    "top_features": {
        "name": "Top 特征列表",
        "calculation": "features ranked by significance or effect size",
        "physical_meaning": "按统计显著性或效应量排序的前列特征",
        "interpretation": {
            "informative": "这些特征可能是潜在的生物标志物",
        },
        "unit": "list",
    },
}


class LLMMetricInterpreter:
    """LLM指标解释器"""

    SYSTEM_PROMPT = """你是一个专业的生物统计学助手，负责解释数据分析指标的含义。

对于每个指标，你需要给出简洁的中文解读，说明：
1. 这个值表示什么
2. 与正常范围相比如何
3. 对结论有什么影响

请用简洁、专业的语言撰写，避免冗余。直接输出解读内容。"""

    USER_TEMPLATE = """**指标**: {metric_name}
**取值**: {value}
**计算方式**: {calculation}
**物理含义**: {physical_meaning}
**解读参考**: {interpretation}
**常见阈值**: {common_thresholds}

生成50字以内的简洁中文解读："""

    def __init__(self, llm_client=None):
        self._llm_client = llm_client

    @property
    def llm_client(self):
        if self._llm_client is None:
            from src.core.orchestration.llm import LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    def interpret(self, metric_key: str, value: Any, context: dict | None = None) -> str:
        """使用LLM生成指标的自然语言解读"""
        metadata = METRIC_METADATA.get(metric_key, {})

        if not metadata:
            return self._fallback_interpretation(metric_key, value)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self.USER_TEMPLATE.format(
                    metric_name=metadata.get("name", metric_key),
                    value=self._format_value(value),
                    calculation=metadata.get("calculation", "未知"),
                    physical_meaning=metadata.get("physical_meaning", "未知"),
                    interpretation=self._format_interpretation(metadata.get("interpretation", {})),
                    common_thresholds=metadata.get("common_thresholds", "无特定阈值"),
                )
            }
        ]

        try:
            response = self.llm_client.chat(messages, max_tokens=128)
            return response.strip()
        except Exception as e:
            return self._fallback_interpretation(metric_key, value, str(e))

    def _format_value(self, value: Any) -> str:
        if isinstance(value, float):
            if abs(value) < 0.001:
                return f"{value:.2e}"
            elif abs(value) < 1:
                return f"{value:.4f}"
            else:
                return f"{value:.4g}"
        elif isinstance(value, list):
            items = ", ".join(str(v) for v in value[:5])
            suffix = "..." if len(value) > 5 else ""
            return f"[{items}{suffix}]"
        return str(value)

    def _format_interpretation(self, interpretation: dict) -> str:
        if not interpretation:
            return "无参考解读"
        return "; ".join(f"{k}: {v}" for k, v in interpretation.items())

    def _fallback_interpretation(self, metric_key: str, value: Any, error: str = "") -> str:
        metadata = METRIC_METADATA.get(metric_key, {})
        name = metadata.get("name", metric_key)
        physical = metadata.get("physical_meaning", "")
        thresholds = metadata.get("common_thresholds", "")

        parts = [f"{name} = {self._format_value(value)}"]
        if physical:
            parts.append(physical)
        if thresholds:
            parts.append(f"参考阈值: {thresholds}")
        if error:
            parts.append("（LLM暂不可用）")

        return " | ".join(parts)


def interpret_check_result(item: dict[str, Any]) -> str:
    """
    解释检查结果项，生成可读的自然语言描述

    Args:
        item: 包含 check, passed, detail 等字段的字典

    Returns:
        可读的解释字符串
    """
    check_name = item.get("check", "")
    passed = item.get("passed")
    detail = item.get("detail", {})

    try:
        interpreter = LLMMetricInterpreter()
        messages = [
            {"role": "system", "content": """你是一个专业的统计分析助手，负责解释检查结果。

对于每个检查项，你需要：
1. 说明这是什么检查（如显著性检验、效应量检验等）
2. 解释检查是否通过
3. 解读具体数值的含义

请用简洁的中文直接输出，不要使用引号或格式标记。"""},
            {"role": "user", "content": f"""检查项：{check_name}
是否通过：{'通过' if passed else '未通过'}
详细信息：{json.dumps(detail, ensure_ascii=False, indent=2)}

请生成30字以内的简洁解释："""}
        ]
        response = interpreter.llm_client.chat(messages, max_tokens=128)
        return response.strip()
    except Exception:
        return _fallback_check_interpretation(item)


def _fallback_check_interpretation(item: dict[str, Any]) -> str:
    """检查结果降级解释"""
    check = str(item.get("check", ""))
    passed = item.get("passed")
    detail = item.get("detail", {})

    parts = []
    if passed is not None:
        parts.append("通过" if passed else "未通过")

    if isinstance(detail, dict):
        value = detail.get("value")
        if value is not None:
            parts.append(f"值={value}")

    return "；".join(parts) if parts else check


import json


def interpret_metric(metric_key: str, value: Any, context: dict | None = None) -> str:
    """便捷函数：使用LLM解释单个指标"""
    interpreter = LLMMetricInterpreter()
    return interpreter.interpret(metric_key, value, context)
