"""测试工具注册中心模块.

验证 tool_registry 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.tools.tool_registry import (
    AnalysisToolManager,
    get_tool_manager,
    execute_tool,
    list_tools,
    search_tools,
)


def test_analysis_tool_manager_init():
    """测试工具管理器初始化."""
    print("测试 AnalysisToolManager 初始化...")
    
    manager = AnalysisToolManager()
    
    assert manager.registry is not None
    assert manager.executor is not None
    
    print("  ✓ AnalysisToolManager 初始化测试通过")


def test_get_available_tools():
    """测试获取可用工具."""
    print("测试 get_available_tools...")
    
    manager = AnalysisToolManager()
    
    # 获取所有工具
    tools = manager.get_available_tools()
    assert isinstance(tools, list)
    
    # 按类型获取工具
    tools = manager.get_available_tools(tool_type="data_processing")
    assert isinstance(tools, list)
    
    print("  ✓ get_available_tools 测试通过")


def test_search_tools():
    """测试搜索工具."""
    print("测试 search_tools...")
    
    manager = AnalysisToolManager()
    
    # 搜索工具
    results = manager.search_tools("data")
    assert isinstance(results, list)
    
    # 搜索不存在的关键词
    results = manager.search_tools("xyz_nonexistent")
    assert isinstance(results, list)
    
    print("  ✓ search_tools 测试通过")


def test_execute_analysis():
    """测试执行分析."""
    print("测试 execute_analysis...")
    
    manager = AnalysisToolManager()
    
    # 执行不存在的工具
    result = manager.execute_analysis("nonexistent_tool")
    assert result["success"] is False
    
    print("  ✓ execute_analysis 测试通过")


def test_get_tool_help():
    """测试获取工具帮助."""
    print("测试 get_tool_help...")
    
    manager = AnalysisToolManager()
    
    # 获取不存在的工具帮助
    help_text = manager.get_tool_help("nonexistent_tool")
    assert "未找到工具" in help_text
    
    print("  ✓ get_tool_help 测试通过")


def test_get_execution_history():
    """测试获取执行历史."""
    print("测试 get_execution_history...")
    
    manager = AnalysisToolManager()
    
    # 获取历史
    history = manager.get_execution_history(limit=10)
    assert isinstance(history, list)
    
    history = manager.get_execution_history(limit=5)
    assert isinstance(history, list)
    
    print("  ✓ get_execution_history 测试通过")


def test_get_tool_manager():
    """测试获取全局工具管理器."""
    print("测试 get_tool_manager...")
    
    manager1 = get_tool_manager()
    manager2 = get_tool_manager()
    
    assert manager1 is manager2, "应该返回同一个实例"
    assert isinstance(manager1, AnalysisToolManager)
    
    print("  ✓ get_tool_manager 测试通过")


def test_list_tools():
    """测试便捷列出工具函数."""
    print("测试 list_tools...")
    
    # 列出所有工具
    tools = list_tools()
    assert isinstance(tools, list)
    
    # 按类型列出
    tools = list_tools(tool_type="data_processing")
    assert isinstance(tools, list)
    
    print("  ✓ list_tools 测试通过")


def test_search_tools_global():
    """测试全局搜索工具函数."""
    print("测试 search_tools 全局函数...")
    
    results = search_tools("query")
    assert isinstance(results, list)
    
    print("  ✓ search_tools 全局函数测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试工具注册中心模块")
    print("=" * 60)
    
    tests = [
        test_analysis_tool_manager_init,
        test_get_available_tools,
        test_search_tools,
        test_execute_analysis,
        test_get_tool_help,
        test_get_execution_history,
        test_get_tool_manager,
        test_list_tools,
        test_search_tools_global,
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
