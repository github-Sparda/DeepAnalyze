"""协作工具函数.

提供统一的协作管理辅助函数，减少代码重复.
"""

from typing import Any, Callable, TypeVar
from functools import wraps

T = TypeVar('T')


def with_error_handling(
    error_handler_attr: str = "error_handler",
    severity: str = "medium",
    category: str = "execution",
    default_return: Any = False
) -> Callable:
    """错误处理装饰器，用于协作管理器方法.

    Args:
        error_handler_attr: 错误处理器属性名
        severity: 严重程度
        category: 错误分类
        default_return: 异常时的默认返回值

    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_handler = getattr(self, error_handler_attr, None)
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
                    
                    # 提取上下文信息
                    context = {}
                    if args:
                        context["session_id"] = args[0] if isinstance(args[0], str) else None
                    if len(args) > 1:
                        context["user_id"] = args[1] if isinstance(args[1], str) else None
                    
                    error_handler.handle_error(
                        e,
                        severity=severity_map.get(severity, ErrorSeverity.MEDIUM),
                        category=category_map.get(category, ErrorCategory.EXECUTION),
                        context=context
                    )
                return default_return
        return wrapper
    return decorator
