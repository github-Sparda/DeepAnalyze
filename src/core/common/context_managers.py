"""上下文管理器工具.

提供统一的上下文管理器，减少代码重复.
"""

from contextlib import contextmanager
from typing import Any, Generator


@contextmanager
def error_handling_context(
    error_handler: Any,
    severity: str = "medium",
    category: str = "execution",
    context: dict | None = None,
    default_return: Any = None,
    reraise: bool = False
) -> Generator[None, None, None]:
    """错误处理上下文管理器.

    Args:
        error_handler: 错误处理器
        severity: 严重程度 (low, medium, high, critical)
        category: 错误分类
        context: 上下文信息
        default_return: 异常时的默认返回值
        reraise: 是否重新抛出异常

    Yields:
        None

    Example:
        with error_handling_context(error_handler, "high", "execution", {"id": 1}):
            # 可能抛出异常的代码
            result = risky_operation()
    """
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
        "filesystem": ErrorCategory.FILESYSTEM,
        "unknown": ErrorCategory.UNKNOWN,
    }

    try:
        yield
    except Exception as e:
        if error_handler:
            error_handler.handle_error(
                e,
                severity=severity_map.get(severity, ErrorSeverity.MEDIUM),
                category=category_map.get(category, ErrorCategory.EXECUTION),
                context=context or {}
            )
        if reraise:
            raise


@contextmanager
def safe_execution_context(
    error_handler: Any = None,
    severity: str = "medium",
    category: str = "execution",
    context: dict | None = None,
    default_return: Any = None
) -> Generator[list, None, None]:
    """安全执行上下文管理器.

    捕获异常并返回默认值.

    Args:
        error_handler: 错误处理器
        severity: 严重程度
        category: 错误分类
        context: 上下文信息
        default_return: 异常时的默认返回值

    Yields:
        结果列表，用于存储执行结果

    Example:
        with safe_execution_context(error_handler, default_return={}) as result:
            result.append(risky_operation())
        # 如果发生异常，result 会是 [default_return]
    """
    result = []
    try:
        yield result
    except Exception as e:
        if error_handler:
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
                "filesystem": ErrorCategory.FILESYSTEM,
                "unknown": ErrorCategory.UNKNOWN,
            }

            error_handler.handle_error(
                e,
                severity=severity_map.get(severity, ErrorSeverity.MEDIUM),
                category=category_map.get(category, ErrorCategory.EXECUTION),
                context=context or {}
            )
        result.append(default_return)


@contextmanager
def file_operation_context(
    error_handler: Any = None,
    operation: str = "read",
    context: dict | None = None
) -> Generator[None, None, None]:
    """文件操作上下文管理器.

    专门用于文件操作的错误处理.

    Args:
        error_handler: 错误处理器
        operation: 操作类型 (read, write, delete)
        context: 上下文信息

    Yields:
        None
    """
    try:
        yield
    except FileNotFoundError as e:
        if error_handler:
            from src.core.error.handler import ErrorSeverity, ErrorCategory
            error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.FILESYSTEM,
                context={"operation": operation, **(context or {})}
            )
    except PermissionError as e:
        if error_handler:
            from src.core.error.handler import ErrorSeverity, ErrorCategory
            error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.FILESYSTEM,
                context={"operation": operation, **(context or {})}
            )
    except Exception as e:
        if error_handler:
            from src.core.error.handler import ErrorSeverity, ErrorCategory
            error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.FILESYSTEM,
                context={"operation": operation, **(context or {})}
            )
