"""JSON处理工具模块.

提供高级的JSON解析和处理功能,特别适用于从LLM输出中提取JSON.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def extract_json_candidates(text: str) -> list[str]:
    """从文本中提取可能的JSON候选字符串.

    支持提取代码块中的JSON和普通JSON对象/数组.

    Args:
        text: 包含JSON的文本

    Returns:
        候选JSON字符串列表
    """
    candidates = []

    # 匹配代码块中的JSON
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    for match in re.finditer(code_block_pattern, text):
        candidates.append(match.group(1).strip())

    # 匹配普通JSON对象
    object_pattern = r"\{[\s\S]*?\}"
    for match in re.finditer(object_pattern, text):
        candidates.append(match.group(0))

    # 匹配JSON数组
    array_pattern = r"\[[\s\S]*?\]"
    for match in re.finditer(array_pattern, text):
        candidates.append(match.group(0))

    return candidates


def safe_json_load(text: str, default: Any = ...) -> Any:
    """安全解析JSON字符串,支持多种容错处理.

    Args:
        text: JSON字符串
        default: 解析失败时返回的默认值,默认为空字典

    Returns:
        解析后的数据或默认值
    """
    # 使用 ... 作为哨兵值来区分未传参和传入 None
    if default is ...:
        default = {}

    if not text or not isinstance(text, str):
        return default

    text = text.strip()
    if not text:
        return default

    # 直接尝试解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取候选JSON
    candidates = extract_json_candidates(text)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # 尝试清理常见格式问题
    cleaned = text
    # 移除尾部逗号
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    # 修复单引号
    cleaned = cleaned.replace("'", '"')

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    return default


def safe_json_any(obj: Any, default: Any = None) -> Any:
    """安全地将任意对象转换为JSON兼容的数据结构.

    Args:
        obj: 任意对象
        default: 转换失败时返回的默认值

    Returns:
        JSON兼容的数据结构
    """
    if default is None:
        default = {}

    if obj is None:
        return default

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, (list, tuple)):
        return [safe_json_any(item, None) for item in obj]

    if isinstance(obj, dict):
        return {str(k): safe_json_any(v, None) for k, v in obj.items()}

    # 尝试转换为字典
    if hasattr(obj, "__dict__"):
        return safe_json_any(obj.__dict__, default)

    # 尝试使用默认序列化
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return default


def load_json_if_exists(path: Path) -> dict[str, Any]:
    """如果文件存在则加载JSON,否则返回空字典.

    Args:
        path: JSON文件路径

    Returns:
        解析后的字典或空字典
    """
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def merge_json_objects(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并两个字典,override的值会覆盖base中的值.

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的新字典
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_json_objects(result[key], value)
        else:
            result[key] = value
    return result


def validate_json_schema(data: Any, schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """简单的JSON Schema验证.

    Args:
        data: 要验证的数据
        schema: 简化的schema定义,支持 type, required, properties

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    # 检查类型
    expected_type = schema.get("type")
    if expected_type:
        type_map = {
            "object": dict,
            "array": list,
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "null": type(None),
        }
        if expected_type in type_map:
            if not isinstance(data, type_map[expected_type]):
                errors.append(f"Expected type {expected_type}, got {type(data).__name__}")

    # 检查必需字段
    if isinstance(data, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # 递归检查属性
        properties = schema.get("properties", {})
        for prop, prop_schema in properties.items():
            if prop in data:
                valid, prop_errors = validate_json_schema(data[prop], prop_schema)
                if not valid:
                    errors.extend([f"{prop}.{err}" for err in prop_errors])

    return len(errors) == 0, errors