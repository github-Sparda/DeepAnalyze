"""测试错误处理模块.

验证 error/handler 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.error.handler import (
    ErrorSeverity,
    ErrorCategory,
    ErrorInfo,
    RecoveryStrategy,
    ErrorHandler,
)


def test_error_severity_enum():
    """测试错误严重程度枚举."""
    print("测试 ErrorSeverity 枚举...")
    
    assert ErrorSeverity.LOW.value == "low"
    assert ErrorSeverity.MEDIUM.value == "medium"
    assert ErrorSeverity.HIGH.value == "high"
    assert ErrorSeverity.CRITICAL.value == "critical"
    
    print("  ✓ ErrorSeverity 枚举测试通过")


def test_error_category_enum():
    """测试错误分类枚举."""
    print("测试 ErrorCategory 枚举...")
    
    assert ErrorCategory.VALIDATION.value == "validation"
    assert ErrorCategory.EXECUTION.value == "execution"
    assert ErrorCategory.NETWORK.value == "network"
    assert ErrorCategory.UNKNOWN.value == "unknown"
    
    print("  ✓ ErrorCategory 枚举测试通过")


def test_error_info():
    """测试错误信息结构."""
    print("测试 ErrorInfo...")
    
    from datetime import datetime
    
    error_info = ErrorInfo(
        error_id="err_123",
        timestamp=datetime.now(),
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.EXECUTION,
        error_type="ValueError",
        message="Test error message",
        traceback="Traceback (most recent call last):...",
        context={"key": "value"},
        recovery_attempts=0,
        recovery_successful=False,
        resolved=False
    )
    
    assert error_info.error_id == "err_123"
    assert error_info.severity == ErrorSeverity.MEDIUM
    assert error_info.category == ErrorCategory.EXECUTION
    assert error_info.message == "Test error message"
    assert error_info.context == {"key": "value"}
    
    print("  ✓ ErrorInfo 测试通过")


def test_recovery_strategy():
    """测试恢复策略."""
    print("测试 RecoveryStrategy...")
    
    def mock_recovery(error_info):
        return True
    
    strategy = RecoveryStrategy(
        name="test_strategy",
        description="Test recovery strategy",
        applicable_categories=[ErrorCategory.EXECUTION],
        applicable_severities=[ErrorSeverity.LOW],
        max_attempts=3,
        retry_delay=1.0,
        recovery_function=mock_recovery
    )
    
    assert strategy.name == "test_strategy"
    assert strategy.max_attempts == 3
    assert strategy.retry_delay == 1.0
    
    # 测试恢复函数
    error_info = ErrorInfo(
        error_id="err_123",
        timestamp=__import__('datetime').datetime.now(),
        severity=ErrorSeverity.LOW,
        category=ErrorCategory.EXECUTION,
        error_type="ValueError",
        message="Test",
        traceback=""
    )
    result = strategy.recovery_function(error_info)
    assert result is True
    
    print("  ✓ RecoveryStrategy 测试通过")


def test_error_handler_init():
    """测试错误处理器初始化."""
    print("测试 ErrorHandler 初始化...")
    
    handler = ErrorHandler()
    
    assert handler is not None
    assert len(handler.errors) == 0
    assert len(handler.recovery_strategies) > 0  # 应该有默认策略
    
    print("  ✓ ErrorHandler 初始化测试通过")


def test_error_handler_register_strategy():
    """测试注册恢复策略."""
    print("测试 ErrorHandler 注册恢复策略...")
    
    handler = ErrorHandler()
    
    def mock_recovery(error_info):
        return True
    
    strategy = RecoveryStrategy(
        name="custom_strategy",
        description="Custom strategy",
        applicable_categories=[ErrorCategory.VALIDATION],
        applicable_severities=[ErrorSeverity.LOW],
        max_attempts=2,
        retry_delay=0.5,
        recovery_function=mock_recovery
    )
    
    handler.register_recovery_strategy("custom_strategy", strategy)
    assert "custom_strategy" in handler.recovery_strategies
    
    print("  ✓ ErrorHandler 注册恢复策略测试通过")


def test_error_handler_handle_error():
    """测试处理错误."""
    print("测试 ErrorHandler 处理错误...")
    
    handler = ErrorHandler()
    
    # 创建一个测试错误
    try:
        raise ValueError("Test error")
    except Exception as e:
        error_info = handler.handle_error(
            e,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXECUTION,
            context={"test": True}
        )
    
    assert error_info is not None
    assert error_info.error_type == "ValueError"
    assert error_info.message == "Test error"
    assert error_info.severity == ErrorSeverity.MEDIUM
    assert error_info.category == ErrorCategory.EXECUTION
    assert error_info.context == {"test": True}
    assert len(handler.errors) == 1
    
    print("  ✓ ErrorHandler 处理错误测试通过")


def test_error_handler_get_errors():
    """测试获取错误列表."""
    print("测试 ErrorHandler 获取错误列表...")
    
    handler = ErrorHandler()
    
    # 添加一些错误
    try:
        raise ValueError("Error 1")
    except Exception as e:
        handler.handle_error(e, severity=ErrorSeverity.LOW)
    
    try:
        raise TypeError("Error 2")
    except Exception as e:
        handler.handle_error(e, severity=ErrorSeverity.HIGH)
    
    # 获取所有错误（直接访问 errors 属性）
    errors = handler.errors
    assert len(errors) == 2
    
    print("  ✓ ErrorHandler 获取错误列表测试通过")


def test_error_handler_clear_errors():
    """测试清除错误."""
    print("测试 ErrorHandler 清除错误...")
    
    handler = ErrorHandler()
    
    # 添加错误
    try:
        raise ValueError("Test error")
    except Exception as e:
        handler.handle_error(e)
    
    assert len(handler.errors) == 1
    
    # 清除错误（直接清空列表）
    handler.errors.clear()
    assert len(handler.errors) == 0
    
    print("  ✓ ErrorHandler 清除错误测试通过")


def test_error_handler_error_stats():
    """测试错误统计."""
    print("测试 ErrorHandler 错误统计...")
    
    handler = ErrorHandler()
    
    # 添加不同严重程度的错误
    for _ in range(3):
        try:
            raise ValueError("Low error")
        except Exception as e:
            handler.handle_error(e, severity=ErrorSeverity.LOW)
    
    for _ in range(2):
        try:
            raise ValueError("High error")
        except Exception as e:
            handler.handle_error(e, severity=ErrorSeverity.HIGH)
    
    stats = handler.get_error_statistics()
    
    assert stats["total_errors"] == 5
    assert stats["severities"]["low"] == 3
    assert stats["severities"]["high"] == 2
    
    print("  ✓ ErrorHandler 错误统计测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试错误处理模块")
    print("=" * 60)
    
    tests = [
        test_error_severity_enum,
        test_error_category_enum,
        test_error_info,
        test_recovery_strategy,
        test_error_handler_init,
        test_error_handler_register_strategy,
        test_error_handler_handle_error,
        test_error_handler_get_errors,
        test_error_handler_clear_errors,
        test_error_handler_error_stats,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
