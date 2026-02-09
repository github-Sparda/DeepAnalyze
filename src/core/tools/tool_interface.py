"""
统一工具接口层
为不同编程语言和分析工具提供统一的调用接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

class ToolType(Enum):
    """工具类型枚举"""
    DATA_PROCESSING = "data_processing"
    STATISTICAL_ANALYSIS = "statistical_docs_analysis"
    VISUALIZATION = "visualization"
    MACHINE_LEARNING = "machine_learning"
    DATABASE = "database"
    UTILITY = "utility"

@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    version: str
    tool_type: ToolType
    supported_languages: List[str]
    parameters: Dict[str, Any]
    returns: str
    data_examples: List[str]

class ToolInterface(ABC):
    """统一工具接口抽象基类"""
    
    def __init__(self, name: str, metadata: ToolMetadata):
        self.name = name
        self.metadata = metadata
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行工具功能"""
        pass
    
    @abstractmethod
    def validate_parameters(self, **kwargs) -> bool:
        """验证参数有效性"""
        pass
    
    def get_help(self) -> str:
        """获取工具使用帮助"""
        return f"""
工具名称: {self.metadata.name}
描述: {self.metadata.description}
支持语言: {', '.join(self.metadata.supported_languages)}
参数: {self.metadata.parameters}
返回值: {self.metadata.returns}
使用示例: {self.metadata.data_examples}
        """

class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, ToolInterface] = {}
        self._categories: Dict[ToolType, List[str]] = {}
    
    def register_tool(self, tool: ToolInterface) -> bool:
        """注册工具"""
        try:
            if tool.name in self._tools:
                raise ValueError(f"工具 {tool.name} 已存在")
            
            self._tools[tool.name] = tool
            
            # 按类别分类
            tool_type = tool.metadata.tool_type
            if tool_type not in self._categories:
                self._categories[tool_type] = []
            self._categories[tool_type].append(tool.name)
            
            return True
        except Exception as e:
            print(f"注册工具失败: {e}")
            return False
    
    def get_tool(self, name: str) -> Optional[ToolInterface]:
        """获取工具实例"""
        return self._tools.get(name)
    
    def list_tools(self, tool_type: Optional[ToolType] = None) -> List[str]:
        """列出工具"""
        if tool_type:
            return self._categories.get(tool_type, [])
        return list(self._tools.keys())
    
    def search_tools(self, keyword: str) -> List[str]:
        """搜索工具"""
        results = []
        for name, tool in self._tools.items():
            if (keyword.lower() in name.lower() or 
                keyword.lower() in tool.metadata.description.lower()):
                results.append(name)
        return results

class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.execution_history: List[Dict[str, Any]] = []
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行指定工具"""
        try:
            tool = self.registry.get_tool(tool_name)
            if not tool:
                raise ValueError(f"未找到工具: {tool_name}")
            
            # 验证参数
            if not tool.validate_parameters(**kwargs):
                raise ValueError(f"参数验证失败: {kwargs}")
            
            # 执行工具
            result = tool.execute(**kwargs)
            
            # 记录执行历史
            execution_record = {
                'tool_name': tool_name,
                'parameters': kwargs,
                'result': result,
                'timestamp': __import__('time').time(),
                'success': True
            }
            self.execution_history.append(execution_record)
            
            return {
                'success': True,
                'result': result,
                'tool_info': {
                    'name': tool.name,
                    'description': tool.metadata.description
                }
            }
            
        except Exception as e:
            error_record = {
                'tool_name': tool_name,
                'parameters': kwargs,
                'error': str(e),
                'timestamp': __import__('time').time(),
                'success': False
            }
            self.execution_history.append(error_record)
            
            return {
                'success': False,
                'error': str(e),
                'tool_info': {'name': tool_name}
            }
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:]