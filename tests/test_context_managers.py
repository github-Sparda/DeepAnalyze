"""测试上下文管理器模块.

验证 context_managers 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common.context_managers import (
    error_handling_context,
    safe_execution_context,
    file_operation_context,
)


class MockErrorHandler:
    """模拟错误处理器"""
    def __init__(self):
        self.errors = []
    
    def handle_error(self, exception, severity, category, context):
        self.errors.append({
            "exception": exception,
            "severity": severity,
            "category": category,
            "context": context,
        })


def test_error_handling_context_no_error():
    """测试错误处理上下文 - 无错误."""
    print("测试 error_handling_context - 无错误...")
    
    handler = MockErrorHandler()
    
    with error_handling_context(handler, "high", "execution", {"test": True}):
        result = 42
    
    assert len(handler.errors) == 0
    assert result == 42
    
    print("  ✓ error_handling_context - 无错误测试通过")


def test_error_handling_context_with_error():
    """测试错误处理上下文 - 有错误."""
    print("测试 error_handling_context - 有错误...")
    
    handler = MockErrorHandler()
    
    try:
        with error_handling_context(handler, "high", "execution", {"test": True}):
            raise ValueError("Test error")
    except ValueError:
        pass  # 异常被重新抛出
    
    assert len(handler.errors) == 1
    assert handler.errors[0]["severity"].value == "high"
    assert handler.errors[0]["context"]["test"] is True
    
    print("  ✓ error_handling_context - 有错误测试通过")


def test_error_handling_context_no_reraise():
    """测试错误处理上下文 - 不重新抛出."""
    print("测试 error_handling_context - 不重新抛出...")
    
    handler = MockErrorHandler()
    
    with error_handling_context(handler, "medium", "execution", reraise=False):
        raise ValueError("Test error")
    
    # 不应该抛出异常
    assert len(handler.errors) == 1
    
    print("  ✓ error_handling_context - 不重新抛出测试通过")


def test_safe_execution_context_success():
    """测试安全执行上下文 - 成功."""
    print("测试 safe_execution_context - 成功...")
    
    handler = MockErrorHandler()
    
    with safe_execution_context(handler, default_return="default") as result:
        result.append("success")
    
    assert result == ["success"]
    assert len(handler.errors) == 0
    
    print("  ✓ safe_execution_context - 成功测试通过")


def test_safe_execution_context_failure():
    """测试安全执行上下文 - 失败."""
    print("测试 safe_execution_context - 失败...")
    
    handler = MockErrorHandler()
    
    with safe_execution_context(handler, default_return="default") as result:
        raise ValueError("Test error")
    
    assert result == ["default"]
    assert len(handler.errors) == 1
    
    print("  ✓ safe_execution_context - 失败测试通过")


def test_file_operation_context_success():
    """测试文件操作上下文 - 成功."""
    print("测试 file_operation_context - 成功...")
    
    handler = MockErrorHandler()
    
    with file_operation_context(handler, "read", {"file": "test.txt"}):
        # 正常操作
        pass
    
    assert len(handler.errors) == 0
    
    print("  ✓ file_operation_context - 成功测试通过")


def test_file_operation_context_file_not_found():
    """测试文件操作上下文 - 文件不存在."""
    print("测试 file_operation_context - 文件不存在...")
    
    handler = MockErrorHandler()
    
    with file_operation_context(handler, "read", {"file": "test.txt"}):
        raise FileNotFoundError("File not found")
    
    assert len(handler.errors) == 1
    assert handler.errors[0]["category"].value == "filesystem"
    
    print("  ✓ file_operation_context - 文件不存在测试通过")


def test_file_operation_context_permission_error():
    """测试文件操作上下文 - 权限错误."""
    print("测试 file_operation_context - 权限错误...")
    
    handler = MockErrorHandler()
    
    with file_operation_context(handler, "write", {"file": "test.txt"}):
        raise PermissionError("Permission denied")
    
    assert len(handler.errors) == 1
    assert handler.errors[0]["severity"].value == "high"
    
    print("  ✓ file_operation_context - 权限错误测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试上下文管理器模块")
    print("=" * 60)
    
    tests = [
        test_error_handling_context_no_error,
        test_error_handling_context_with_error,
        test_error_handling_context_no_reraise,
        test_safe_execution_context_success,
        test_safe_execution_context_failure,
        test_file_operation_context_success,
        test_file_operation_context_file_not_found,
        test_file_operation_context_permission_error,
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
