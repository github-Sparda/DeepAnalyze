"""测试工具接口模块.

验证 tool_interface 和 tool_registry 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.tools.tool_interface import (
    ToolType,
    ToolMetadata,
    ToolInterface,
    ToolRegistry,
    ToolExecutor,
)


class MockTool(ToolInterface):
    """模拟工具用于测试"""
    
    def execute(self, **kwargs):
        return {"result": "mock_result", **kwargs}
    
    def validate_parameters(self, **kwargs):
        return True


def test_tool_type_enum():
    """测试工具类型枚举."""
    print("测试 ToolType 枚举...")
    
    assert ToolType.DATA_PROCESSING.value == "data_processing"
    assert ToolType.STATISTICAL_ANALYSIS.value == "statistical_docs_analysis"
    assert ToolType.VISUALIZATION.value == "visualization"
    
    print("  ✓ ToolType 枚举测试通过")


def test_tool_metadata():
    """测试工具元数据."""
    print("测试 ToolMetadata...")
    
    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        version="1.0.0",
        tool_type=ToolType.DATA_PROCESSING,
        supported_languages=["python"],
        parameters={"param1": "str"},
        returns="dict",
        data_examples=["example1"]
    )
    
    assert metadata.name == "test_tool"
    assert metadata.description == "A test tool"
    assert metadata.version == "1.0.0"
    
    print("  ✓ ToolMetadata 测试通过")


def test_tool_interface():
    """测试工具接口."""
    print("测试 ToolInterface...")
    
    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        version="1.0.0",
        tool_type=ToolType.DATA_PROCESSING,
        supported_languages=["python"],
        parameters={},
        returns="dict",
        data_examples=[]
    )
    
    tool = MockTool("test_tool", metadata)
    
    assert tool.name == "test_tool"
    assert tool.metadata == metadata
    
    # 测试 get_help
    help_text = tool.get_help()
    assert "test_tool" in help_text
    assert "A test tool" in help_text
    
    # 测试 execute
    result = tool.execute(param1="value1")
    assert result["result"] == "mock_result"
    assert result["param1"] == "value1"
    
    # 测试 validate_parameters
    assert tool.validate_parameters() is True
    
    print("  ✓ ToolInterface 测试通过")


def test_tool_registry():
    """测试工具注册中心."""
    print("测试 ToolRegistry...")
    
    registry = ToolRegistry()
    
    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        version="1.0.0",
        tool_type=ToolType.DATA_PROCESSING,
        supported_languages=["python"],
        parameters={},
        returns="dict",
        data_examples=[]
    )
    
    tool = MockTool("test_tool", metadata)
    
    # 测试注册工具
    result = registry.register_tool(tool)
    assert result is True
    
    # 测试重复注册
    result = registry.register_tool(tool)
    assert result is False
    
    # 测试获取工具
    retrieved_tool = registry.get_tool("test_tool")
    assert retrieved_tool is not None
    assert retrieved_tool.name == "test_tool"
    
    # 测试获取不存在的工具
    assert registry.get_tool("nonexistent") is None
    
    # 测试列出工具
    tools = registry.list_tools()
    assert "test_tool" in tools
    
    # 测试按类型列出
    tools = registry.list_tools(ToolType.DATA_PROCESSING)
    assert "test_tool" in tools
    
    tools = registry.list_tools(ToolType.VISUALIZATION)
    assert "test_tool" not in tools
    
    # 测试搜索工具
    results = registry.search_tools("test")
    assert "test_tool" in results
    
    results = registry.search_tools("nonexistent")
    assert "test_tool" not in results
    
    print("  ✓ ToolRegistry 测试通过")


def test_tool_executor():
    """测试工具执行器."""
    print("测试 ToolExecutor...")
    
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    
    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        version="1.0.0",
        tool_type=ToolType.DATA_PROCESSING,
        supported_languages=["python"],
        parameters={},
        returns="dict",
        data_examples=[]
    )
    
    tool = MockTool("test_tool", metadata)
    registry.register_tool(tool)
    
    # 测试执行工具
    result = executor.execute_tool("test_tool", param1="value1")
    assert result["success"] is True
    assert result["result"]["result"] == "mock_result"
    
    # 测试执行不存在的工具
    result = executor.execute_tool("nonexistent")
    assert result["success"] is False
    assert "error" in result
    
    # 测试执行历史
    history = executor.get_execution_history(limit=10)
    assert len(history) == 2  # 一次成功，一次失败
    
    history = executor.get_execution_history(limit=1)
    assert len(history) == 1
    
    print("  ✓ ToolExecutor 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试工具接口模块")
    print("=" * 60)
    
    tests = [
        test_tool_type_enum,
        test_tool_metadata,
        test_tool_interface,
        test_tool_registry,
        test_tool_executor,
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
