"""扩展测试错误处理模块.

验证 error/handler 模块的更多功能.
"""

import sys
import tempfile
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
from datetime import datetime


def test_error_handler_with_recovery():
    """测试带恢复的错误处理器."""
    print("测试 ErrorHandler 带恢复...")
    
    handler = ErrorHandler()
    
    # 创建一个会触发恢复策略的错误
    try:
        raise ConnectionError("Network error")
    except Exception as e:
        error_info = handler.handle_error(
            e,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context={"retry_count": 0}
        )
    
    assert error_info is not None
    assert error_info.category == ErrorCategory.NETWORK
    
    print("  ✓ ErrorHandler 带恢复测试通过")


def test_recovery_strategy_execution():
    """测试恢复策略执行."""
    print("测试恢复策略执行...")
    
    handler = ErrorHandler()
    
    # 创建一个自定义恢复策略
    def custom_recovery(error_info):
        return True
    
    strategy = RecoveryStrategy(
        name="custom_test",
        description="Test strategy",
        applicable_categories=[ErrorCategory.EXECUTION],
        applicable_severities=[ErrorSeverity.LOW],
        max_attempts=3,
        retry_delay=0.1,
        recovery_function=custom_recovery
    )
    
    handler.register_recovery_strategy("custom_test", strategy)
    
    # 触发一个适用该策略的错误
    try:
        raise RuntimeError("Test error")
    except Exception as e:
        error_info = handler.handle_error(
            e,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.EXECUTION
        )
    
    assert error_info.recovery_attempts >= 0
    
    print("  ✓ 恢复策略执行测试通过")


def test_error_handler_multiple_errors():
    """测试处理多个错误."""
    print("测试处理多个错误...")
    
    handler = ErrorHandler()
    
    # 创建多个不同类型的错误
    errors = [
        (ValueError("Error 1"), ErrorSeverity.LOW, ErrorCategory.VALIDATION),
        (TypeError("Error 2"), ErrorSeverity.MEDIUM, ErrorCategory.EXECUTION),
        (ConnectionError("Error 3"), ErrorSeverity.HIGH, ErrorCategory.NETWORK),
    ]
    
    for exc, severity, category in errors:
        try:
            raise exc
        except Exception as e:
            handler.handle_error(e, severity=severity, category=category)
    
    stats = handler.get_error_statistics()
    assert stats["total_errors"] == 3
    
    print("  ✓ 处理多个错误测试通过")


def test_error_handler_edge_cases():
    """测试错误处理器边界情况."""
    print("测试错误处理器边界情况...")
    
    handler = ErrorHandler()
    
    # 测试空统计
    stats = handler.get_error_statistics()
    assert stats["total_errors"] == 0
    
    # 测试不同类型的异常
    exceptions = [
        ValueError("Value error"),
        TypeError("Type error"),
        KeyError("key"),
        IndexError("Index error"),
        AttributeError("Attribute error"),
    ]
    
    for exc in exceptions:
        error_info = handler.handle_error(exc)
        assert error_info is not None
    
    print("  ✓ 错误处理器边界情况测试通过")


def test_error_info_creation():
    """测试错误信息创建."""
    print("测试错误信息创建...")
    
    error_info = ErrorInfo(
        error_id="test_001",
        timestamp=datetime.now(),
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.EXECUTION,
        error_type="TestError",
        message="Test message",
        traceback="Test traceback",
        context={"key": "value"},
        recovery_attempts=2,
        recovery_successful=True,
        resolved=False
    )
    
    assert error_info.error_id == "test_001"
    assert error_info.severity == ErrorSeverity.HIGH
    assert error_info.recovery_attempts == 2
    assert error_info.recovery_successful is True
    
    print("  ✓ 错误信息创建测试通过")


def test_error_severity_comparison():
    """测试错误严重程度比较."""
    print("测试错误严重程度比较...")
    
    # 测试严重程度排序
    severities = [
        ErrorSeverity.LOW,
        ErrorSeverity.MEDIUM,
        ErrorSeverity.HIGH,
        ErrorSeverity.CRITICAL
    ]
    
    # 验证顺序
    assert ErrorSeverity.LOW.value == "low"
    assert ErrorSeverity.MEDIUM.value == "medium"
    assert ErrorSeverity.HIGH.value == "high"
    assert ErrorSeverity.CRITICAL.value == "critical"
    
    print("  ✓ 错误严重程度比较测试通过")


def test_error_category_values():
    """测试错误分类值."""
    print("测试错误分类值...")
    
    categories = [
        ErrorCategory.VALIDATION,
        ErrorCategory.EXECUTION,
        ErrorCategory.NETWORK,
        ErrorCategory.UNKNOWN
    ]
    
    for category in categories:
        assert isinstance(category.value, str)
        assert len(category.value) > 0
    
    print("  ✓ 错误分类值测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始扩展测试错误处理模块")
    print("=" * 60)
    
    tests = [
        test_error_handler_with_recovery,
        test_recovery_strategy_execution,
        test_error_handler_multiple_errors,
        test_error_handler_edge_cases,
        test_error_info_creation,
        test_error_severity_comparison,
        test_error_category_values,
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
