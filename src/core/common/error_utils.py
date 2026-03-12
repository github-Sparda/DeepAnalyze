"""错误处理工具函数.

提供统一的错误处理模式，减少代码重复.
"""

from typing import Any, Callable, TypeVar
from functools import wraps

T = TypeVar('T')


def safe_execute(
    func: Callable[..., T],
    *args,
    default: T = None,
    error_message: str = "",
    **kwargs
) -> T:
    """安全执行函数，捕获异常并返回默认值.

    Args:
        func: 要执行的函数
        *args: 位置参数
        default: 异常时返回的默认值
        error_message: 错误日志消息
        **kwargs: 关键字参数

    Returns:
        函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        if error_message:
            import logging
            logging.getLogger(__name__).error(error_message)
        return default


def safe_convert_to_float(value: Any) -> float | None:
    """安全地将值转换为浮点数.

    Args:
        value: 要转换的值

    Returns:
        浮点数或None
    """
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except Exception:
        return None


def safe_convert_to_int(value: Any) -> int | None:
    """安全地将值转换为整数.

    Args:
        value: 要转换的值

    Returns:
        整数或None
    """
    try:
        if isinstance(value, bool):
            return None
        return int(value)
    except Exception:
        return None


def extract_hypothesis_id(text: str, default_idx: int = 0) -> str:
    """从文本中提取假设ID.

    Args:
        text: 包含假设ID的文本
        default_idx: 默认索引

    Returns:
        假设ID
    """
    import re
    hid_match = re.search(r"\b(H\d+)\b", text.upper())
    return hid_match.group(1) if hid_match else f"H{default_idx + 1}"


def find_nearest_centroid(
    sample: Any,
    centroids: dict[str, list[float]]
) -> str:
    """找到最近的质心.

    Args:
        sample: 样本向量
        centroids: 质心字典

    Returns:
        最近质心的标签
    """
    import numpy as np
    best_label = ""
    best_dist = None
    for label, centroid in centroids.items():
        vec = np.array(centroid)
        dist = float(np.linalg.norm(sample - vec))
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_label = label
    return best_label


def detect_time_column(df: Any) -> str | None:
    """检测DataFrame中的时间列.

    Args:
        df: DataFrame

    Returns:
        时间列名或None
    """
    for col in df.columns:
        if "time" in col.lower() or "date" in col.lower():
            return col
    return None


def normalize_output_dir(output_dir: Any, default_name: str = "result") -> Any:
    """规范化输出目录.

    Args:
        output_dir: 输出目录路径
        default_name: 默认目录名

    Returns:
        规范化的路径
    """
    from pathlib import Path
    p = Path(output_dir)
    if not p.name or p.name == ".":
        p = p / default_name
    p.mkdir(parents=True, exist_ok=True)
    return p


def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    *args,
    **kwargs
) -> T:
    """带指数退避的重试机制.

    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        base_delay: 基础延迟
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数返回值
    """
    import time
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

    raise last_exception


def handle_error_with_context(
    error_handler: Any,
    exception: Exception,
    severity: str = "medium",
    category: str = "execution",
    context: dict | None = None
) -> Any:
    """统一处理错误并返回错误信息.

    Args:
        error_handler: 错误处理器
        exception: 异常对象
        severity: 严重程度
        category: 错误分类
        context: 上下文信息

    Returns:
        错误信息对象
    """
    if error_handler is None:
        return None

    from src.core.error.handler import ErrorSeverity, ErrorCategory

    severity_map = {
        "low": ErrorSeverity.LOW,
        "medium": ErrorSeverity.MEDIUM,
        "high": ErrorSeverity.HIGH,
        "critical": ErrorSeverity.CRITICAL,
    }

    category_map = {
        "validation": ErrorCategory.VALIDATION,
        "execution": ErrorCategory.EXECUTION,
        "network": ErrorCategory.NETWORK,
        "unknown": ErrorCategory.UNKNOWN,
    }

    return error_handler.handle_error(
        exception,
        severity=severity_map.get(severity, ErrorSeverity.MEDIUM),
        category=category_map.get(category, ErrorCategory.EXECUTION),
        context=context or {}
    )


def error_handler_decorator(
    error_handler_attr: str = "error_handler",
    severity: str = "medium",
    category: str = "execution",
    context_factory: Any = None
):
    """错误处理装饰器.

    Args:
        error_handler_attr: 错误处理器属性名
        severity: 严重程度
        category: 错误分类
        context_factory: 上下文工厂函数

    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_handler = getattr(self, error_handler_attr, None)
                if error_handler:
                    ctx = context_factory(self) if context_factory else {}
                    handle_error_with_context(
                        error_handler, e,
                        severity=severity,
                        category=category,
                        context=ctx
                    )
                raise
        return wrapper
    return decorator
