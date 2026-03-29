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


def format_metric_html(
    metric_key: str,
    value: Any,
    interpretation: str | None = None,
    status: str | None = None,
) -> str:
    """
    生成带颜色标记的HTML指标显示

    Args:
        metric_key: 指标英文名
        value: 指标值
        interpretation: LLM解读（如有）
        status: 状态 ('positive', 'negative', 'warning', 'error', 'neutral')

    Returns:
        HTML格式的指标显示，包含颜色和样式
    """
    metadata = METRIC_METADATA.get(metric_key, {})
    display_name = metadata.get("name", metric_key)

    # 确定颜色状态
    if status is None:
        status = _infer_metric_status(metric_key, value)

    # 根据状态选择CSS类
    css_class_map = {
        "positive": "metric-positive",
        "negative": "metric-negative",
        "warning": "metric-warning",
        "error": "metric-error",
        "neutral": "metric-neutral",
    }
    css_class = css_class_map.get(status, "metric-neutral")

    # 格式化数值
    if isinstance(value, float):
        if abs(value) < 0.001:
            value_str = f"{value:.2e}"
        elif abs(value) < 1:
            value_str = f"{value:.4f}"
        else:
            value_str = f"{value:.4g}"
    else:
        value_str = str(value)

    # 构建HTML
    parts = [f'<span class="{css_class}"><strong>{display_name}</strong></span>']
    parts.append(f'<span class="{css_class}"> = <span class="metric-value">{value_str}</span></span>')

    if interpretation:
        parts.append(f'<span class="{css_class}">（{interpretation}）</span>')

    return "".join(parts)


def _infer_metric_status(metric_key: str, value: Any) -> str:
    """根据指标类型和取值推断颜色状态"""
    # 阈值判断类指标
    threshold_indicators = {
        "auc": (0.7, 0.8, 0.9),
        "cv_mean_accuracy": (0.7, 0.8, 0.9),
        "silhouette": (0.5, 0.7, 0.9),
        "significant_p_lt_0_05": (5, 20, 40),
    }

    if metric_key in threshold_indicators:
        low, mid, high = threshold_indicators[metric_key]
        if value >= high:
            return "positive"
        elif value >= mid:
            return "neutral"
        else:
            return "negative"

    # 通过/失败类
    if "pass" in metric_key or "passed" in metric_key:
        return "positive" if value else "negative"

    if "fail" in metric_key or "conflict" in metric_key or "error" in metric_key:
        return "negative"

    # 数量类
    if value is not None:
        if isinstance(value, (int, float)):
            if value > 0:
                return "positive"

    return "neutral"


def format_check_result_html(item: dict[str, Any], interpretation: str | None = None) -> str:
    """
    生成带颜色标记的HTML检查结果显示

    Args:
        item: 检查结果字典
        interpretation: LLM解读

    Returns:
        HTML格式的检查结果
    """
    check = item.get("check", "")
    passed = item.get("passed")
    metadata = METRIC_METADATA.get(check, {})
    check_name = metadata.get("name", check)

    if passed:
        status = "positive"
        status_text = '<span class="tag tag-pass">通过</span>'
    else:
        status = "negative"
        status_text = '<span class="tag tag-fail">未通过</span>'

    css_class = "metric-positive" if passed else "metric-negative"

    parts = [
        f'<span class="{css_class}"><strong>{check_name}</strong></span>',
        f" {status_text}",
    ]

    if interpretation:
        parts.append(f'<span class="{css_class}">（{interpretation}）</span>')

    return "".join(parts)


def format_conclusion_html(text: str, level: str = "normal") -> str:
    """
    生成带颜色标记的HTML结论显示

    Args:
        text: 结论文本
        level: 重要程度 ('highlight', 'normal', 'warning')

    Returns:
        HTML格式的结论
    """
    if level == "highlight":
        return f'<span class="conclusion-highlight">{text}</span>'
    elif level == "warning":
        return f'<span class="metric-warning">{text}</span>'
    else:
        return text


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
    from src.core.reporting.narrative import METRIC_EXPLANATION

    check = str(item.get("check", ""))
    passed = item.get("passed")

    # Look up Chinese name from METRIC_EXPLANATION first
    check_name = METRIC_EXPLANATION.get(check, {}).get("name", "")
    if not check_name:
        # Fallback to METRIC_METADATA
        check_name = METRIC_METADATA.get(check, {}).get("name", check)

    parts = []
    if passed is not None:
        parts.append("通过" if passed else "未通过")

    if isinstance(detail := item.get("detail", {}), dict):
        if value := detail.get("value"):
            # Format value nicely
            if isinstance(value, float):
                value_str = f"{value:.4g}"
            elif isinstance(value, list):
                value_str = f"[{', '.join(str(v) for v in value[:3])}{'...' if len(value) > 3 else ''}]"
            else:
                value_str = str(value)
            parts.append(f"值={value_str}")

    return "；".join(parts) if parts else check_name


def interpret_metrics_summary(metrics: dict[str, Any], max_length: int = 150) -> str:
    """
    解释指标摘要字典，生成可读的自然语言描述

    Args:
        metrics: 指标字典 {key: value, ...}
        max_length: 最大长度限制

    Returns:
        可读的指标摘要描述
    """
    if not metrics:
        return "无指标数据"

    try:
        interpreter = LLMMetricInterpreter()
        metrics_str = json.dumps(metrics, ensure_ascii=False, indent=2)
        messages = [
            {"role": "system", "content": """你是一个统计分析助手，负责将指标字典转换为简洁的自然语言摘要。

要求：
- 提取关键指标及其数值
- 说明整体分析结论
- 限制在50字以内
直接输出摘要，不要使用引号或格式。"""},
            {"role": "user", "content": f"指标数据：{metrics_str}\n\n生成50字以内的简洁摘要："}
        ]
        response = interpreter.llm_client.chat(messages, max_tokens=100)
        return response.strip()[:max_length]
    except Exception:
        return _fallback_metrics_summary(metrics, max_length)


def _fallback_metrics_summary(metrics: dict, max_length: int = 150) -> str:
    """指标摘要降级解释"""
    if not metrics:
        return "无指标数据"

    from src.core.reporting.narrative import METRIC_EXPLANATION

    parts = []
    for k, v in list(metrics.items())[:5]:
        # Look up Chinese name
        chinese_name = METRIC_EXPLANATION.get(k, {}).get("name", k)
        if isinstance(v, float):
            parts.append(f"{chinese_name}={v:.3f}")
        else:
            parts.append(f"{chinese_name}={v}")

    result = "；".join(parts)
    return result[:max_length] + ("..." if len(result) > max_length else "")


class NarrativeGenerator:
    """
    报告写作自然语言生成器

    将结构化数据转换为流畅、易读的中文报告文本。
    """

    def __init__(self, llm_client=None):
        self._llm_client = llm_client

    @property
    def llm_client(self):
        if self._llm_client is None:
            from src.core.orchestration.llm import LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    def generate_hypothesis_conclusion(
        self,
        hyp_id: str,
        hyp_text: str,
        quant_metrics: dict | None,
        quant_evaluations: list | None,
        gate_entry: dict | None,
        evidence_sources: list | None,
    ) -> str:
        """
        生成假设结论段落

        Args:
            hyp_id: 假设ID
            hyp_text: 假设文本
            quant_metrics: 定量指标
            quant_evaluations: 定量评估（已解释的指标列表）
            gate_entry: 门限条目
            evidence_sources: 证据来源

        Returns:
            自然语言段落
        """
        try:
            messages = [
                {"role": "system", "content": """你是一个专业的生物统计学报告撰写助手，负责将分析结果转换为流畅、易读的中文报告。

要求：
- 不要使用生硬的模板句式（如"依据："、"关键数值见本节"）
- 将定量指标融入流畅的叙述中
- 突出关键发现和数据意义
- 限制在200字以内
直接输出报告段落，不要使用引号或格式标记。"""},
                {"role": "user", "content": f"""假设：{hyp_text}
定量评估：{quant_evaluations[:3] if quant_evaluations else '无'}
门限状态：{gate_entry.get('gate_status', '') if gate_entry else ''}
门限规则：{gate_entry.get('gate_rule_type', '') if gate_entry else ''}
证据来源：{evidence_sources[:2] if evidence_sources else '无'}

请撰写一段流畅的假设验证结论（100字以内）："""}
            ]
            response = self.llm_client.chat(messages, max_tokens=200)
            return response.strip()
        except Exception:
            return self._fallback_hypothesis_conclusion(hyp_id, hyp_text, quant_evaluations)

    def generate_metric_reference(
        self,
        quant_evaluations: list,
        max_items: int = 4,
    ) -> str:
        """
        生成指标参考段落，替代"关键数值见本节"

        Args:
            quant_evaluations: 定量评估列表
            max_items: 最大显示条目数

        Returns:
            自然语言指标参考
        """
        if not quant_evaluations:
            return ""

        try:
            from src.core.reporting.narrative import METRIC_EXPLANATION

            # Replace English metric names with Chinese names
            items_text = "\n".join([f"- {item}" for item in quant_evaluations[:max_items]])
            for eng_key, info in METRIC_EXPLANATION.items():
                chinese_name = info.get("name", eng_key)
                if chinese_name != eng_key:
                    # Handle both quoted and unquoted patterns
                    for pattern in [f'"{eng_key}"', f'"{eng_key.lower()}"', eng_key]:
                        if pattern in items_text:
                            items_text = items_text.replace(pattern, chinese_name)

            messages = [
                {"role": "system", "content": """你是一个专业的统计分析报告撰写助手。

将指标列表转换为流畅的叙述性参考。不要说"关键数值见本节"，而是直接用自然语言引用关键数据。

要求：
- 直接引用关键数值
- 用通俗语言解释数值意义
- 限制在80字以内
直接输出，不要使用引号。"""},
                {"role": "user", "content": f"关键指标：\n{items_text}\n\n生成自然语言引用（60字以内）："}
            ]
            response = self.llm_client.chat(messages, max_tokens=100)
            return response.strip()
        except Exception:
            return self._fallback_metric_reference(quant_evaluations, max_items)

    def generate_judgment_narrative(
        self,
        gate_rule_type: str,
        gate_status: str,
        failed_checks: list | None,
        reason_code: str | None,
    ) -> str:
        """
        生成判定叙述，替代"判定规则说明：XXX 判定状态说明：YYY"

        Args:
            gate_rule_type: 门限规则类型
            gate_status: 门限状态
            failed_checks: 失败检查列表
            reason_code: 原因代码

        Returns:
            自然语言判定叙述
        """
        try:
            messages = [
                {"role": "system", "content": """你是一个专业的统计分析报告撰写助手。

将判定规则和状态信息转换为流畅的叙述性语言。不要说"判定规则说明"这种生硬的话。

要求：
- 直接说明判定结果
- 用自然语言解释规则和状态
- 如果有失败检查，说明原因
- 限制在100字以内
直接输出，不要使用引号。"""},
                {"role": "user", "content": f"""判定规则：{gate_rule_type}
判定状态：{gate_status}
失败检查：{failed_checks[:2] if failed_checks else '无'}
原因代码：{reason_code or '无'}

生成自然语言判定叙述（80字以内）："""}
            ]
            response = self.llm_client.chat(messages, max_tokens=120)
            return response.strip()
        except Exception:
            return self._fallback_judgment_narrative(gate_status)

    def generate_missing_analysis(
        self,
        hyp_text: str,
        missing: list,
        evidence_sources: list | None,
    ) -> str:
        """
        生成缺失分析叙述，替代"针对XXX的分析尚未形成足够证据"

        Args:
            hyp_text: 假设文本
            missing: 缺失产物
            evidence_sources: 证据来源

        Returns:
            自然语言缺失叙述
        """
        try:
            messages = [
                {"role": "system", "content": """你是一个专业的统计分析报告撰写助手。

将分析缺失信息转换为建设性的建议性语言。不要说"尚未形成足够证据"这种消极表达。

要求：
- 用积极的语言说明下一步
- 指出具体需要补充的内容
- 限制在80字以内
直接输出，不要使用引号。"""},
                {"role": "user", "content": f"""假设：{hyp_text}
缺失产物：{', '.join(missing[:3]) if missing else '无'}
证据来源：{evidence_sources[:2] if evidence_sources else '无'}

生成建议性叙述（60字以内）："""}
            ]
            response = self.llm_client.chat(messages, max_tokens=100)
            return response.strip()
        except Exception:
            missing_str = "、" .join(missing[:2]) if missing else "关键产物"
            return f"当前分析尚需补充{missing_str}，建议完善后再进行评估。"

    def _fallback_hypothesis_conclusion(
        self,
        hyp_id: str,
        hyp_text: str,
        quant_evaluations: list | None,
    ) -> str:
        """假设结论降级"""
        if quant_evaluations:
            summary = "；".join(str(e)[:30] for e in quant_evaluations[:2])
            return f"{hyp_text}。{summary}。"
        return f"{hyp_text}。相关定量分析已完成。"

    def _fallback_metric_reference(
        self,
        quant_evaluations: list,
        max_items: int = 4,
    ) -> str:
        """指标参考降级"""
        if not quant_evaluations:
            return ""
        items = "、".join(str(e)[:25] for e in quant_evaluations[:max_items])
        return f"关键指标包括：{items}。"

    def _fallback_judgment_narrative(self, gate_status: str) -> str:
        """判定叙述降级"""
        if gate_status == "passed":
            return "本假设通过验证。"
        elif gate_status == "failed":
            return "本假设未通过验证。"
        return "本假设尚在评估中。"

    def _fallback_missing_narrative(
        self,
        missing: list,
        evidence_sources: list | None,
    ) -> str:
        """缺失叙述降级"""
        missing_str = "、".join(missing[:2]) if missing else "关键产物"
        return f"当前分析尚需补充{missing_str}，建议完善后再进行评估。"


def wrap_headings_with_details(html_content: str) -> str:
    """
    将HTML中的标题转换为可折叠的details元素

    Args:
        html_content: HTML内容

    Returns:
        转换后的HTML
    """
    import re

    # 要默认折叠的小节标题关键词
    default_collapsed_keywords = [
        '一致性与冲突',
        '计划产物',
        '执行事实',
        '证据摘录',
        '判定依据',
        '恢复计划',
        '校准',
        '路径对照',
    ]

    def make_collapsed(title_text: str) -> bool:
        return any(kw in title_text for kw in default_collapsed_keywords)

    # 标题层级class映射
    heading_class = {'h2': 'heading-level-1', 'h3': 'heading-level-2', 'h4': 'heading-level-3', 'h5': 'heading-level-4'}

    # 处理 h2, h3, h4, h5
    for tag in ['h2', 'h3', 'h4', 'h5']:
        pattern = rf'(<{tag}>([^<]*)</{tag}>)\s*(.*?)(?=(?:<h[2345]>)|$)'

        def replacer(m):
            title = m.group(2)
            inner = m.group(3) if len(m.groups()) > 2 else ''
            collapsed = make_collapsed(title)
            arrow = '▶' if collapsed else '▼'
            open_attr = '' if collapsed else ' open'
            cls = heading_class.get(tag, 'heading-level-default')
            return f'<details class="collapsible-section"{open_attr}><summary><span class="collapse-arrow">{arrow}</span><span class="{cls}">{title}</span></summary>{inner}</details>'

        html_content = re.sub(
            pattern,
            replacer,
            html_content,
            flags=re.DOTALL | re.IGNORECASE
        )

    return html_content


def interpret_metric(metric_key: str, value: Any, context: dict | None = None) -> str:
    """便捷函数：使用LLM解释单个指标"""
    interpreter = LLMMetricInterpreter()
    return interpreter.interpret(metric_key, value, context)
