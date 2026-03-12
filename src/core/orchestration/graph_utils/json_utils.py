"""JSON 处理工具函数.

从原 graph.py 中提取的 JSON 相关工具函数.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def extract_json_candidates(raw: str) -> list[str]:
    """从文本中提取可能的 JSON 候选字符串.

    支持从代码块和普通文本中提取 JSON 对象/数组.

    Args:
        raw: 包含 JSON 的原始文本

    Returns:
        候选 JSON 字符串列表
    """
    if not raw:
        return []
    candidates: list[str] = []
    fence = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    for match in fence.findall(raw):
        candidates.append(match.strip())
    obj_match = re.search(r"(\{[\s\S]*\})", raw)
    if obj_match:
        candidates.append(obj_match.group(1))
    arr_match = re.search(r"(\[[\s\S]*\])", raw)
    if arr_match:
        candidates.append(arr_match.group(1))
    return candidates


def safe_json_any(raw: str) -> Any:
    """安全地将字符串解析为任意 JSON 对象.

    尝试多种方式解析 JSON,包括直接解析和从代码块中提取.

    Args:
        raw: JSON 字符串

    Returns:
        解析后的对象,失败时返回空字典
    """
    try:
        return json.loads(raw)
    except Exception:
        pass
    for candidate in extract_json_candidates(raw):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return {}


def safe_json_load(raw: str) -> dict[str, Any]:
    """安全地加载 JSON 字符串为字典.

    Args:
        raw: JSON 字符串

    Returns:
        解析后的字典,失败时返回空字典
    """
    payload = safe_json_any(raw)
    return payload if isinstance(payload, dict) else {}


def load_json_if_exists(path: Path) -> dict[str, Any]:
    """如果文件存在则加载 JSON,否则返回空字典.

    Args:
        path: JSON 文件路径

    Returns:
        解析后的字典或空字典
    """
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}