"""文件操作工具模块.

提供统一的文件和目录操作功能,消除跨模块的重复代码.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在,如果不存在则创建.

    Args:
        path: 目录路径

    Returns:
        Path对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path: str | Path, default: T | None = None) -> Any:
    """安全加载JSON文件.

    Args:
        path: JSON文件路径
        default: 加载失败时返回的默认值,默认为空字典

    Returns:
        解析后的JSON数据或默认值
    """
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    try:
        content = json.loads(p.read_text(encoding="utf-8"))
        return content
    except Exception:
        return default


def load_json_with_factory(path: str | Path, default_factory: Callable[[], T]) -> T:
    """加载JSON,失败时使用工厂函数返回默认值.

    Args:
        path: JSON文件路径
        default_factory: 返回默认值的工厂函数

    Returns:
        解析后的JSON数据或工厂函数返回的默认值
    """
    p = Path(path)
    if not p.exists():
        return default_factory()
    try:
        content = json.loads(p.read_text(encoding="utf-8"))
        return content
    except Exception:
        return default_factory()


def save_json(path: str | Path, payload: Any, indent: int = 2) -> Path:
    """保存JSON文件,自动创建父目录.

    Args:
        path: 目标文件路径
        payload: 要保存的数据
        indent: JSON缩进,默认为2

    Returns:
        保存的文件Path对象
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=indent), encoding="utf-8")
    return p


def load_text(path: str | Path, default: str = "") -> str:
    """安全加载文本文件.

    Args:
        path: 文本文件路径
        default: 加载失败时返回的默认值

    Returns:
        文件内容或默认值
    """
    p = Path(path)
    if not p.exists():
        return default
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return default


def save_text(path: str | Path, content: str) -> Path:
    """保存文本文件,自动创建父目录.

    Args:
        path: 目标文件路径
        content: 要保存的文本内容

    Returns:
        保存的文件Path对象
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def hash_file(path: str | Path, algorithm: str = "sha256") -> str:
    """计算文件哈希值.

    Args:
        path: 文件路径
        algorithm: 哈希算法,支持 sha256, md5, sha1

    Returns:
        十六进制哈希字符串
    """
    p = Path(path)
    if not p.exists():
        return ""

    hash_obj = hashlib.new(algorithm)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def copy_file(src: str | Path, dst: str | Path) -> Path:
    """复制文件,自动创建目标目录.

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Returns:
        目标文件Path对象
    """
    import shutil

    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst_path)
    return dst_path