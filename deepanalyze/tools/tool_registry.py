"""
工具注册中心和执行器
集中管理所有分析工具
"""

from .tool_interface import ToolRegistry, ToolExecutor
from .python.data_manipulation import register_python_tools
from .sql.query_builder import register_sql_tools
from .r.r_bridge import register_r_tools

class AnalysisToolManager:
    """分析工具管理器"""
    
    def __init__(self):
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self._register_all_tools()
    
    def _register_all_tools(self):
        """注册所有工具"""
        # 注册Python工具
        register_python_tools(self.registry)
        
        # 注册SQL工具
        register_sql_tools(self.registry)
        
        # 注册R工具
        register_r_tools(self.registry)
    
    def get_available_tools(self, tool_type=None):
        """获取可用工具列表"""
        return self.registry.list_tools(tool_type)
    
    def search_tools(self, keyword):
        """搜索工具"""
        return self.registry.search_tools(keyword)
    
    def execute_analysis(self, tool_name, **kwargs):
        """执行分析工具"""
        return self.executor.execute_tool(tool_name, **kwargs)
    
    def get_tool_help(self, tool_name):
        """获取工具帮助信息"""
        tool = self.registry.get_tool(tool_name)
        if tool:
            return tool.get_help()
        return f"未找到工具: {tool_name}"
    
    def get_execution_history(self, limit=10):
        """获取执行历史"""
        return self.executor.get_execution_history(limit)

# 全局工具管理器实例
tool_manager = AnalysisToolManager()

def get_tool_manager():
    """获取全局工具管理器"""
    return tool_manager

# 便捷函数
def execute_tool(tool_name, **kwargs):
    """便捷执行工具函数"""
    return tool_manager.execute_analysis(tool_name, **kwargs)

def list_tools(tool_type=None):
    """便捷列出工具函数"""
    return tool_manager.get_available_tools(tool_type)

def search_tools(keyword):
    """便捷搜索工具函数"""
    return tool_manager.search_tools(keyword)