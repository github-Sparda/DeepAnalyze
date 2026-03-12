"""测试协作工具模块.

验证 collab_utils 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common.collab_utils import with_error_handling


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


class MockCollaborationManager:
    """模拟协作管理器"""
    def __init__(self):
        self.error_handler = MockErrorHandler()
    
    @with_error_handling(default_return=False)
    def add_collaborator(self, session_id: str, user_id: str) -> bool:
        """添加协作者"""
        if session_id == "error":
            raise ValueError("Test error")
        return True
    
    @with_error_handling(severity="high", default_return=None)
    def get_collaborators(self, session_id: str):
        """获取协作者列表"""
        if session_id == "error":
            raise RuntimeError("Test error")
        return []


def test_with_error_handling_success():
    """测试错误处理装饰器 - 成功."""
    print("测试 with_error_handling - 成功...")
    
    manager = MockCollaborationManager()
    result = manager.add_collaborator("session_1", "user_1")
    
    assert result is True
    assert len(manager.error_handler.errors) == 0
    
    print("  ✓ with_error_handling - 成功测试通过")


def test_with_error_handling_failure():
    """测试错误处理装饰器 - 失败."""
    print("测试 with_error_handling - 失败...")
    
    manager = MockCollaborationManager()
    result = manager.add_collaborator("error", "user_1")
    
    assert result is False  # 默认返回值
    assert len(manager.error_handler.errors) == 1
    assert manager.error_handler.errors[0]["severity"].value == "medium"
    assert manager.error_handler.errors[0]["context"]["session_id"] == "error"
    
    print("  ✓ with_error_handling - 失败测试通过")


def test_with_error_handling_high_severity():
    """测试错误处理装饰器 - 高严重程度."""
    print("测试 with_error_handling - 高严重程度...")
    
    manager = MockCollaborationManager()
    result = manager.get_collaborators("error")
    
    assert result is None  # 默认返回值
    assert len(manager.error_handler.errors) == 1
    assert manager.error_handler.errors[0]["severity"].value == "high"
    
    print("  ✓ with_error_handling - 高严重程度测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试协作工具模块")
    print("=" * 60)
    
    tests = [
        test_with_error_handling_success,
        test_with_error_handling_failure,
        test_with_error_handling_high_severity,
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
