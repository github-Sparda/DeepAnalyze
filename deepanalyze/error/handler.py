"""
Enhanced Error Handling and Recovery System for DeepAnalyze
完善的错误处理和恢复系统
"""

from __future__ import annotations

import logging
import traceback
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import sys
import signal

# 添加项目根目录到路径
import os
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"      # 低严重性，可忽略或警告
    MEDIUM = "medium"  # 中等严重性，需要处理但不影响整体流程
    HIGH = "high"    # 高严重性，影响主要功能
    CRITICAL = "critical"  # 临界错误，可能导致系统不稳定


class ErrorCategory(Enum):
    """错误分类"""
    VALIDATION = "validation"    # 输入验证错误
    EXECUTION = "execution"     # 代码执行错误
    NETWORK = "network"        # 网络通信错误
    FILESYSTEM = "filesystem"   # 文件系统错误
    MEMORY = "memory"         # 内存相关错误
    TIMEOUT = "timeout"       # 超时错误
    CONFIGURATION = "configuration"  # 配置错误
    EXTERNAL_API = "external_api"   # 外部API错误
    UNKNOWN = "unknown"       # 未知错误


@dataclass
class ErrorInfo:
    """错误信息结构"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    message: str
    traceback: str
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    recovery_successful: bool = False
    resolved: bool = False


@dataclass
class RecoveryStrategy:
    """恢复策略"""
    name: str
    description: str
    applicable_categories: List[ErrorCategory]
    applicable_severities: List[ErrorSeverity]
    max_attempts: int
    retry_delay: float  # 秒
    recovery_function: Callable[[ErrorInfo], bool]


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, log_level: int = logging.INFO):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # 错误存储
        self.errors: List[ErrorInfo] = []
        self.max_error_history = 1000
        
        # 恢复策略注册表
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        
        # 注册默认恢复策略
        self._register_default_strategies()
        
        # 设置信号处理器
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器以优雅地处理中断"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _register_default_strategies(self):
        """注册默认恢复策略"""
        
        # 网络超时重试策略
        network_retry_strategy = RecoveryStrategy(
            name="network_retry",
            description="网络超时错误重试策略",
            applicable_categories=[ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_API],
            applicable_severities=[ErrorSeverity.LOW, ErrorSeverity.MEDIUM],
            max_attempts=3,
            retry_delay=2.0,
            recovery_function=self._retry_network_operation
        )
        self.register_recovery_strategy("network_retry", network_retry_strategy)
        
        # 文件系统错误恢复策略
        filesystem_recovery_strategy = RecoveryStrategy(
            name="filesystem_recovery",
            description="文件系统错误恢复策略",
            applicable_categories=[ErrorCategory.FILESYSTEM],
            applicable_severities=[ErrorSeverity.LOW, ErrorSeverity.MEDIUM],
            max_attempts=2,
            retry_delay=1.0,
            recovery_function=self._recover_filesystem_error
        )
        self.register_recovery_strategy("filesystem_recovery", filesystem_recovery_strategy)
        
        # 执行错误隔离策略
        execution_isolation_strategy = RecoveryStrategy(
            name="execution_isolation",
            description="代码执行错误隔离策略",
            applicable_categories=[ErrorCategory.EXECUTION],
            applicable_severities=[ErrorSeverity.HIGH],
            max_attempts=1,
            retry_delay=0,
            recovery_function=self._isolate_execution_error
        )
        self.register_recovery_strategy("execution_isolation", execution_isolation_strategy)
    
    def register_recovery_strategy(self, name: str, strategy: RecoveryStrategy):
        """注册恢复策略"""
        self.recovery_strategies[name] = strategy
        self.logger.debug(f"Registered recovery strategy: {name}")
    
    def handle_error(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ) -> ErrorInfo:
        """
        处理错误
        
        Args:
            error: 异常对象
            severity: 错误严重程度
            category: 错误分类
            context: 上下文信息
            recoverable: 是否可恢复
            
        Returns:
            错误信息对象
        """
        # 生成错误ID
        error_id = f"err_{int(time.time() * 1000000)}_{hash(str(error)) % 10000:04d}"
        
        # 获取堆栈跟踪
        tb_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            error_type=type(error).__name__,
            message=str(error),
            traceback=tb_str,
            context=context or {}
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 存储错误
        self._store_error(error_info)
        
        # 尝试自动恢复
        if recoverable:
            self._attempt_recovery(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_msg = (
            f"Error [{error_info.error_id}] "
            f"Severity: {error_info.severity.value}, "
            f"Category: {error_info.category.value}, "
            f"Type: {error_info.error_type}, "
            f"Message: {error_info.message}"
        )
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_msg)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_msg)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
    
    def _store_error(self, error_info: ErrorInfo):
        """存储错误信息"""
        self.errors.append(error_info)
        
        # 限制历史记录大小
        if len(self.errors) > self.max_error_history:
            # 保留最近的错误，删除最旧的
            self.errors = self.errors[-self.max_error_history:]
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """尝试错误恢复"""
        recovery_success = False
        
        # 查找适用的恢复策略
        for strategy in self.recovery_strategies.values():
            if self._is_strategy_applicable(strategy, error_info):
                self.logger.info(f"Attempting recovery using strategy: {strategy.name}")
                
                try:
                    # 执行恢复
                    success = strategy.recovery_function(error_info)
                    
                    # 更新错误信息
                    error_info.recovery_attempts += 1
                    error_info.recovery_successful = success
                    
                    if success:
                        self.logger.info(f"Recovery successful for error {error_info.error_id}")
                        recovery_success = True
                        break
                    else:
                        self.logger.warning(
                            f"Recovery attempt {error_info.recovery_attempts} failed "
                            f"for error {error_info.error_id}"
                        )
                        
                except Exception as recovery_error:
                    self.logger.error(
                        f"Recovery strategy {strategy.name} failed: {recovery_error}"
                    )
        
        return recovery_success
    
    def _is_strategy_applicable(self, strategy: RecoveryStrategy, error_info: ErrorInfo) -> bool:
        """检查策略是否适用于该错误"""
        return (
            error_info.category in strategy.applicable_categories and
            error_info.severity in strategy.applicable_severities and
            error_info.recovery_attempts < strategy.max_attempts
        )
    
    def _retry_network_operation(self, error_info: ErrorInfo) -> bool:
        """网络操作重试策略"""
        # 这里可以实现具体的重试逻辑
        # 例如：等待一段时间后重试API调用
        time.sleep(error_info.recovery_attempts * 2)  # 指数退避
        return True  # 表示重试机制已触发
    
    def _recover_filesystem_error(self, error_info: ErrorInfo) -> bool:
        """文件系统错误恢复"""
        # 检查磁盘空间
        # 清理临时文件
        # 重新创建缺失的目录
        try:
            # 示例：清理临时文件
            temp_dir = Path("/tmp")
            if temp_dir.exists():
                # 清理超过1小时的临时文件
                import os
                current_time = time.time()
                for temp_file in temp_dir.glob("*.tmp"):
                    if current_time - temp_file.stat().st_mtime > 3600:
                        temp_file.unlink()
            return True
        except Exception:
            return False
    
    def _isolate_execution_error(self, error_info: ErrorInfo) -> bool:
        """执行错误隔离"""
        # 记录错误状态，防止进一步执行
        # 可以在这里实现更复杂的隔离逻辑
        self.logger.info("Execution error isolated, preventing further damage")
        return True
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self.errors:
            return {"total_errors": 0}
        
        # 按类别统计
        category_stats = {}
        severity_stats = {}
        recovery_stats = {"successful": 0, "failed": 0, "attempts": 0}
        
        for error in self.errors:
            # 类别统计
            category = error.category.value
            category_stats[category] = category_stats.get(category, 0) + 1
            
            # 严重程度统计
            severity = error.severity.value
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
            
            # 恢复统计
            recovery_stats["attempts"] += error.recovery_attempts
            if error.recovery_successful:
                recovery_stats["successful"] += 1
            elif error.recovery_attempts > 0:
                recovery_stats["failed"] += 1
        
        return {
            "total_errors": len(self.errors),
            "categories": category_stats,
            "severities": severity_stats,
            "recovery": recovery_stats,
            "first_error": self.errors[0].timestamp.isoformat(),
            "last_error": self.errors[-1].timestamp.isoformat()
        }
    
    def export_error_report(self, filepath: str) -> bool:
        """导出错误报告"""
        try:
            stats = self.get_error_statistics()
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "recent_errors": [
                    {
                        "id": error.error_id,
                        "timestamp": error.timestamp.isoformat(),
                        "severity": error.severity.value,
                        "category": error.category.value,
                        "type": error.error_type,
                        "message": error.message,
                        "recovery_attempts": error.recovery_attempts,
                        "recovery_successful": error.recovery_successful
                    }
                    for error in self.errors[-50:]  # 最近50个错误
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to export error report: {e}")
            return False
    
    def clear_error_history(self, older_than_hours: Optional[int] = None):
        """清空错误历史"""
        if older_than_hours is None:
            self.errors.clear()
            self.logger.info("Error history cleared")
        else:
            cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
            self.errors = [
                error for error in self.errors
                if error.timestamp.timestamp() >= cutoff_time
            ]
            self.logger.info(f"Error history cleared (older than {older_than_hours} hours)")
    
    def shutdown(self):
        """关闭错误处理器"""
        self.logger.info("Shutting down error handler...")
        # 可以在这里添加清理逻辑
        # 例如：导出最终错误报告
        pass


class SafeExecutor:
    """安全执行器，提供带错误处理的执行环境"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    def execute_with_recovery(
        self,
        func: Callable[..., Any],
        *args,
        fallback_value: Any = None,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """
        带恢复机制的安全执行
        
        Args:
            func: 要执行的函数
            fallback_value: 失败时的回退值
            max_retries: 最大重试次数
            **kwargs: 函数参数
            
        Returns:
            函数执行结果或回退值
        """
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.EXECUTION,
                    context={
                        "function": func.__name__,
                        "attempt": attempt,
                        "args": str(args)[:100],  # 限制长度避免日志过大
                        "kwargs": str(kwargs)[:100]
                    }
                )
                
                if attempt < max_retries:
                    delay = 2 ** attempt  # 指数退避
                    self.error_handler.logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    self.error_handler.logger.error(
                        f"All {max_retries + 1} attempts failed for {func.__name__}"
                    )
                    return fallback_value
    
    def execute_critical_operation(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        执行关键操作（不可恢复的错误会被重新抛出）
        
        Args:
            func: 要执行的关键函数
            **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            Exception: 如果是关键错误且无法恢复
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.EXECUTION,
                context={
                    "function": func.__name__,
                    "critical": True
                },
                recoverable=False
            )
            
            # 对于关键操作的错误，重新抛出
            raise e


# 全局错误处理器实例
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_exception(
    error: Exception,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    context: Optional[Dict[str, Any]] = None
) -> ErrorInfo:
    """便捷函数：处理异常"""
    handler = get_error_handler()
    return handler.handle_error(error, severity, category, context)


def safe_execute(
    func: Callable[..., Any],
    *args,
    fallback_value: Any = None,
    max_retries: int = 3,
    **kwargs
) -> Any:
    """便捷函数：安全执行"""
    handler = get_error_handler()
    executor = SafeExecutor(handler)
    return executor.execute_with_recovery(func, *args, fallback_value=fallback_value, 
                                        max_retries=max_retries, **kwargs)


# 装饰器
def safe_operation(max_retries: int = 3, fallback_value: Any = None):
    """安全操作装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return safe_execute(func, *args, fallback_value=fallback_value, 
                              max_retries=max_retries, **kwargs)
        return wrapper
    return decorator


def critical_operation(func):
    """关键操作装饰器"""
    def wrapper(*args, **kwargs):
        handler = get_error_handler()
        executor = SafeExecutor(handler)
        return executor.execute_critical_operation(func, *args, **kwargs)
    return wrapper