"""Fallback 降级处理工具函数.

从原 graph.py 中提取的 LLM 降级和 fallback 相关工具函数.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def is_llm_unavailable_error(raw: str) -> bool:
    """检查错误信息是否表明 LLM 不可用.

    Args:
        raw: 错误信息字符串

    Returns:
        如果是 LLM 不可用错误返回 True
    """
    text = str(raw or "").strip().lower()
    if not text:
        return False
    tokens = [
        "model_not_found",
        "rate limit",
        "429",
        "service unavailable",
        "connection error",
        "connection refused",
        "timed out",
        "timeout",
        "api key",
        "invalid api key",
        "authentication",
    ]
    return any(token in text for token in tokens)


def record_llm_degradation(
    state: dict[str, Any],
    node: str,
    action: str,
    reason: str,
    impact: str,
) -> list[dict[str, Any]]:
    """记录 LLM 降级事件.

    Args:
        state: 当前状态字典
        node: 节点名称
        action: 执行的动作
        reason: 降级原因
        impact: 影响描述

    Returns:
        更新后的事件列表
    """
    events = list(state.get("llm_degradation_events", []) or [])
    events.append(
        {
            "node": node,
            "action": action,
            "reason": reason,
            "impact": impact,
            "timestamp": int(time.time()),
        }
    )
    return events


def has_llm_unavailable_event(events: list[dict[str, Any]] | None) -> bool:
    """检查事件列表中是否包含 LLM 不可用事件.

    Args:
        events: 事件列表

    Returns:
        如果包含 LLM 不可用事件返回 True
    """
    if not isinstance(events, list):
        return False
    for event in events:
        if not isinstance(event, dict):
            continue
        if is_llm_unavailable_error(event.get("reason", "")):
            return True
    return False


def strong_fallback_plan_ok(plan_json: dict[str, Any]) -> tuple[bool, str]:
    """验证降级计划是否满足基本要求.

    Args:
        plan_json: 计划 JSON 对象

    Returns:
        (是否有效, 原因代码)
    """
    if not isinstance(plan_json, dict):
        return False, "plan_not_object"
    hypotheses = plan_json.get("hypotheses", [])
    if not isinstance(hypotheses, list) or len(hypotheses) < 3:
        return False, "hypothesis_count_lt_3"
    ids: set[str] = set()
    for row in hypotheses:
        if not isinstance(row, dict):
            return False, "hypothesis_not_object"
        hid = str(row.get("id", "")).strip().upper()
        if not re.fullmatch(r"H\d+", hid):
            return False, "hypothesis_id_invalid"
        if hid in ids:
            return False, "hypothesis_id_duplicated"
        ids.add(hid)
        if not str(row.get("title", "")).strip():
            return False, "hypothesis_title_missing"
        if not str(row.get("hypothesis_type", "")).strip():
            return False, "hypothesis_type_missing"
        steps = row.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return False, f"{hid}_steps_missing"
        paths = row.get("validation_paths", [])
        if not isinstance(paths, list) or len(paths) < 2:
            return False, f"{hid}_validation_paths_lt_2"
    return True, "ok"


def strong_fallback_report_ok(
    completion_validation: dict[str, Any],
    set_consistency: dict[str, Any],
    pack_validation: dict[str, Any],
) -> tuple[bool, list[str]]:
    """验证降级报告是否满足基本要求.

    Args:
        completion_validation: 完成验证结果
        set_consistency: 假设集合一致性检查结果
        pack_validation: 证据包验证结果

    Returns:
        (是否有效, 原因列表)
    """
    reasons: list[str] = []
    if not bool((completion_validation or {}).get("complete", False)):
        reasons.append("completion_validation_failed")
    if not bool((set_consistency or {}).get("satisfied", False)):
        reasons.append("hypothesis_set_inconsistent")
    if not bool((pack_validation or {}).get("valid", False)):
        reasons.append("evidence_pack_invalid")
    return len(reasons) == 0, reasons


def fallback_followup_hypotheses(session_dir: Path) -> list[str]:
    """生成后续假设建议列表（LLM 不可用时使用）.

    Args:
        session_dir: 会话目录路径

    Returns:
        后续假设建议列表
    """
    gate_payload = load_json_if_exists(session_dir / "result" / "hypothesis_gate_report.json")
    rows = gate_payload.get("hypotheses", []) if isinstance(gate_payload, dict) else []
    followups: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("gate_status", "")).strip().lower()
        if status not in {"partial", "fail"}:
            continue
        hid = str(row.get("hypothesis_id", "")).strip() or "UNKNOWN"
        reason = str(row.get("reason_code", "")).strip() or "证据不足"
        followups.append(f"{hid} 未闭环（{reason}），建议补充缺失证据并重跑对应路径。")
    if followups:
        return followups[:6]
    multipath_payload = load_json_if_exists(session_dir / "result" / "hypothesis_multipath.json")
    rows = multipath_payload.get("hypotheses", []) if isinstance(multipath_payload, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "")).strip().lower()
        if status == "inconclusive":
            hid = str(row.get("hypothesis_id", "")).strip() or "UNKNOWN"
            followups.append(f"{hid} 路径存在冲突，建议运行第三路径或复核数据切分口径。")
    return followups[:6]


def fallback_report_outline(state: dict[str, Any]) -> str:
    """生成降级报告大纲（LLM 不可用时使用）.

    Args:
        state: 当前状态字典

    Returns:
        报告大纲 Markdown 字符串
    """
    plan_json = state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {}
    hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    lines = [
        "# 报告大纲（LLM 不可用时自动生成）",
        "",
        "## 一、研究目标与数据说明",
        "## 二、方法与执行路径",
        "## 三、假设验证结果",
    ]
    if isinstance(hypotheses, list) and hypotheses:
        for idx, hyp in enumerate(hypotheses, 1):
            if not isinstance(hyp, dict):
                continue
            hid = str(hyp.get("id", "")).strip() or f"H{idx}"
            title = str(hyp.get("title", "")).strip() or "未命名假设"
            lines.append(f"### {hid} {title}")
            lines.append("- 验证方案")
            lines.append("- 执行结果")
            lines.append("- 定量分析")
            lines.append("- 结论与后续动作")
    else:
        lines.extend(
            [
                "### 假设验证（待补充）",
                "- 验证方案",
                "- 执行结果",
                "- 定量分析",
                "- 结论与后续动作",
            ]
        )
    lines.extend(
        [
            "",
            "## 四、跨假设综合讨论",
            "## 五、结论与建议",
            "## 六、附件与证据索引",
        ]
    )
    return "\n".join(lines)


def fallback_analysis_code() -> str:
    """生成降级分析代码（LLM 不可用时使用）.

    Returns:
        Python 代码字符串
    """
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
