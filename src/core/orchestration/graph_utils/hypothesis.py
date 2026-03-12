"""假设处理工具函数.

从原 graph.py 中提取的假设相关工具函数.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def extract_hypothesis_id_from_label(raw: str) -> str:
    """从标签中提取假设ID.

    Args:
        raw: 包含假设ID的字符串

    Returns:
        提取的假设ID，如果未找到则返回空字符串
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    m = re.search(r"(H\d+)", text, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def active_hypothesis_ids_from_plan(plan_json: dict[str, Any]) -> list[str]:
    """从计划JSON中获取活跃的假设ID列表.

    Args:
        plan_json: 计划JSON数据

    Returns:
        假设ID列表
    """
    if not isinstance(plan_json, dict):
        return []
    hypotheses = plan_json.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return []
    ids: list[str] = []
    for hyp in hypotheses:
        if isinstance(hyp, dict):
            hid = str(hyp.get("id", "")).strip().upper()
            if hid:
                ids.append(hid)
    return ids


def filter_hypothesis_results_payload(
    payload: dict[str, Any], allowed_ids: list[str]
) -> dict[str, Any]:
    """过滤假设结果，只保留允许的假设ID.

    Args:
        payload: 假设结果数据
        allowed_ids: 允许的假设ID列表

    Returns:
        过滤后的结果数据
    """
    if not isinstance(payload, dict):
        return {}
    if not allowed_ids:
        return payload

    allowed_set = {str(hid).strip().upper() for hid in allowed_ids}
    rows = payload.get("hypotheses", [])
    if not isinstance(rows, list):
        return payload

    filtered: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            hid = str(row.get("hypothesis_id", "")).strip().upper()
            if hid in allowed_set:
                filtered.append(row)

    return {**payload, "hypotheses": filtered}


def hypothesis_title_only(plan_json: dict[str, Any]) -> dict[str, str]:
    """从计划JSON中提取假设ID到标题的映射.

    Args:
        plan_json: 计划JSON数据

    Returns:
        假设ID到标题的映射字典
    """
    result: dict[str, str] = {}
    if not isinstance(plan_json, dict):
        return result

    hypotheses = plan_json.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return result

    for hyp in hypotheses:
        if isinstance(hyp, dict):
            hid = str(hyp.get("id", "")).strip().upper()
            title = str(hyp.get("title", "")).strip()
            if hid:
                result[hid] = title

    return result


def extract_hypotheses(text: str) -> list[dict[str, Any]]:
    """从文本中提取假设列表.

    Args:
        text: 包含假设描述的文本

    Returns:
        假设列表，每个假设包含id、title和description
    """
    hypotheses: list[dict[str, Any]] = []
    lines = text.splitlines()
    current: dict[str, Any] | None = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 匹配假设标题行
        match = re.match(r"^(H\d+)[\s\-\:]*(.+)$", line, re.IGNORECASE)
        if match:
            if current:
                hypotheses.append(current)
            current = {
                "id": match.group(1).upper(),
                "title": match.group(2).strip(),
                "description": "",
            }
        elif current is not None:
            # 累加描述
            current["description"] += line + " "

    if current:
        hypotheses.append(current)

    return hypotheses


def extract_hypothesis_ids_from_report(report_markdown: str) -> list[str]:
    """从报告Markdown中提取假设ID列表.

    Args:
        report_markdown: 报告Markdown文本

    Returns:
        假设ID列表
    """
    ids: list[str] = []
    pattern = re.compile(r"(H\d+)", re.IGNORECASE)
    for match in pattern.findall(report_markdown):
        hid = match.upper()
        if hid not in ids:
            ids.append(hid)
    return ids


def sync_hypothesis_alignment_artifacts(
    session_dir: Path, plan_ids: list[str]
) -> dict[str, Any]:
    """同步假设对齐的产物.

    Args:
        session_dir: 会话目录
        plan_ids: 计划中的假设ID列表

    Returns:
        同步结果统计
    """
    result_dir = session_dir / "result"
    result: dict[str, Any] = {
        "aligned": [],
        "removed": [],
        "missing": [],
    }

    # 加载现有结果
    results_path = result_dir / "hypothesis_results.json"
    results = load_json_if_exists(results_path)

    existing_ids: set[str] = set()
    if isinstance(results, dict) and "hypotheses" in results:
        for row in results.get("hypotheses", []):
            if isinstance(row, dict):
                hid = str(row.get("hypothesis_id", "")).strip().upper()
                if hid:
                    existing_ids.add(hid)

    plan_ids_set = {str(hid).strip().upper() for hid in plan_ids}

    # 找出需要对齐的ID
    for hid in plan_ids_set:
        if hid in existing_ids:
            result["aligned"].append(hid)
        else:
            result["missing"].append(hid)

    # 找出需要移除的ID
    for hid in existing_ids:
        if hid not in plan_ids_set:
            result["removed"].append(hid)

    return result
