"""
SQL工具集合
提供数据库查询构建、数据提取和性能优化功能
"""

import sqlite3
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from ..tool_interface import ToolInterface, ToolMetadata, ToolType

class QueryBuilderTool(ToolInterface):
    """SQL查询构建器工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="query_builder",
            description="构建SQL查询语句",
            version="1.0.0",
            tool_type=ToolType.DATABASE,
            supported_languages=["SQL", "Python"],
            parameters={
                "table": "str - 表名",
                "columns": "list - 查询列名列表",
                "conditions": "dict - WHERE条件字典",
                "order_by": "str - 排序字段",
                "limit": "int - 限制返回行数"
            },
            returns="str - 生成的SQL查询语句",
            data_examples=[
                "query_builder(table='users', columns=['name', 'age'], conditions={'age': '>25'})",
                "query_builder(table='orders', columns=['*'], order_by='created_date DESC', limit=100)"
            ]
        )
        super().__init__("query_builder", metadata)
    
    def validate_parameters(self, **kwargs) -> bool:
        return 'table' in kwargs and 'columns' in kwargs
    
    def execute(self, **kwargs) -> str:
        table = kwargs['table']
        columns = kwargs.get('columns', ['*'])
        conditions = kwargs.get('conditions', {})
        order_by = kwargs.get('order_by')
        limit = kwargs.get('limit')
        
        # 构建SELECT子句
        columns_str = ', '.join(columns) if columns != ['*'] else '*'
        query = f"SELECT {columns_str} FROM {table}"
        
        # 添加WHERE条件
        if conditions:
            where_clauses = []
            for column, condition in conditions.items():
                if isinstance(condition, dict):
                    op = list(condition.keys())[0]
                    value = condition[op]
                    where_clauses.append(f"{column} {op} {self._format_value(value)}")
                else:
                    where_clauses.append(f"{column} = {self._format_value(condition)}")
            
            if where_clauses:
                query += f" WHERE {' AND '.join(where_clauses)}"
        
        # 添加ORDER BY
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # 添加LIMIT
        if limit:
            query += f" LIMIT {limit}"
        
        return query
    
    def _format_value(self, value) -> str:
        """格式化SQL值"""
        if isinstance(value, str):
            return f"'{value}'"
        elif value is None:
            return 'NULL'
        else:
            return str(value)

class DataExtractorTool(ToolInterface):
    """数据提取工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="data_extractor",
            description="从数据库提取数据到DataFrame",
            version="1.0.0",
            tool_type=ToolType.DATABASE,
            supported_languages=["Python"],
            parameters={
                "connection_string": "str - 数据库连接字符串",
                "query": "str - SQL查询语句",
                "db_type": "str - 数据库类型 (sqlite, mysql, postgresql)"
            },
            returns="pandas.DataFrame - 提取的数据",
            data_examples=[
                "data_extractor(connection_string='sqlite:///data.db', query='SELECT * FROM users')",
                "data_extractor(connection_string='postgresql://...', query='SELECT name, age FROM employees WHERE age > 30')"
            ]
        )
        super().__init__("data_extractor", metadata)
    
    def validate_parameters(self, **kwargs) -> bool:
        required_params = ['connection_string', 'query']
        return all(param in kwargs for param in required_params)
    
    def execute(self, **kwargs) -> pd.DataFrame:
        connection_string = kwargs['connection_string']
        query = kwargs['query']
        db_type = kwargs.get('db_type', 'sqlite')
        
        try:
            if db_type == 'sqlite':
                # SQLite连接
                conn = sqlite3.connect(connection_string.replace('sqlite:///', ''))
                df = pd.read_sql_query(query, conn)
                conn.close()
                return df
            else:
                # 其他数据库类型使用SQLAlchemy
                import sqlalchemy
                engine = sqlalchemy.create_engine(connection_string)
                df = pd.read_sql_query(query, engine)
                engine.dispose()
                return df
                
        except Exception as e:
            raise Exception(f"数据提取失败: {str(e)}")

class PerformanceOptimizerTool(ToolInterface):
    """SQL性能优化工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="performance_optimizer",
            description="分析和优化SQL查询性能",
            version="1.0.0",
            tool_type=ToolType.DATABASE,
            supported_languages=["SQL"],
            parameters={
                "query": "str - 待优化的SQL查询",
                "explain_plan": "bool - 是否生成执行计划",
                "index_suggestions": "bool - 是否提供建议索引"
            },
            returns="dict - 性能分析和优化建议",
            data_examples=[
                "performance_optimizer(query='SELECT * FROM large_table WHERE date > \"2023-01-01\"')",
                "performance_optimizer(query='SELECT * FROM users JOIN orders ON users.id = orders.user_id', explain_plan=True)"
            ]
        )
        super().__init__("performance_optimizer", metadata)
    
    def validate_parameters(self, **kwargs) -> bool:
        return 'query' in kwargs and isinstance(kwargs['query'], str)
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs['query']
        explain_plan = kwargs.get('explain_plan', False)
        index_suggestions = kwargs.get('index_suggestions', True)
        
        analysis = {
            'original_query': query,
            'complexity_score': self._calculate_complexity(query),
            'potential_issues': self._identify_issues(query),
            'optimization_suggestions': self._generate_suggestions(query)
        }
        
        if explain_plan:
            analysis['explain_plan_template'] = self._generate_explain_template(query)
        
        if index_suggestions:
            analysis['index_recommendations'] = self._suggest_indexes(query)
        
        return analysis
    
    def _calculate_complexity(self, query: str) -> float:
        """计算查询复杂度"""
        complexity_factors = {
            'JOIN': 0.3,
            'GROUP BY': 0.2,
            'ORDER BY': 0.1,
            'DISTINCT': 0.15,
            'SUBQUERY': 0.4,
            'UNION': 0.35
        }
        
        complexity = 0.0
        query_upper = query.upper()
        
        for keyword, weight in complexity_factors.items():
            if keyword in query_upper:
                complexity += weight
        
        # 考虑表数量
        table_count = query_upper.count('FROM') + query_upper.count('JOIN')
        complexity += min(table_count * 0.1, 0.5)
        
        return min(complexity, 1.0)
    
    def _identify_issues(self, query: str) -> List[str]:
        """识别潜在问题"""
        issues = []
        query_upper = query.upper()
        
        # SELECT * 检查
        if 'SELECT *' in query_upper:
            issues.append("使用SELECT *可能导致不必要的数据传输")
        
        # 缺少WHERE条件检查
        if 'WHERE' not in query_upper and ('UPDATE' in query_upper or 'DELETE' in query_upper):
            issues.append("UPDATE/DELETE语句缺少WHERE条件，可能导致意外的数据修改")
        
        # 大表扫描检查
        if 'LIKE \'%\' || column || \'%\'' in query or 'LIKE CONCAT(\'%\', column, \'%\')' in query_upper:
            issues.append("模糊查询可能导致全表扫描")
        
        return issues
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """生成优化建议"""
        suggestions = []
        query_upper = query.upper()
        
        if 'SELECT *' in query_upper:
            suggestions.append("明确指定需要的列，避免SELECT *")
        
        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            suggestions.append("考虑添加LIMIT子句限制返回行数")
        
        if 'JOIN' in query_upper:
            suggestions.append("确保JOIN字段上有适当的索引")
        
        return suggestions
    
    def _generate_explain_template(self, query: str) -> str:
        """生成执行计划模板"""
        return f"EXPLAIN QUERY PLAN {query}"
    
    def _suggest_indexes(self, query: str) -> List[str]:
        """建议索引"""
        suggestions = []
        query_upper = query.upper()
        
        # 简单的索引建议逻辑
        if 'WHERE' in query_upper:
            # 提取WHERE条件中的字段
            where_part = query_upper.split('WHERE')[1].split('ORDER BY')[0].split('GROUP BY')[0]
            # 这里可以实现更复杂的字段提取逻辑
            suggestions.append("考虑在WHERE条件字段上创建索引")
        
        if 'JOIN' in query_upper:
            suggestions.append("考虑在JOIN字段上创建复合索引")
        
        return suggestions

# 注册所有SQL工具
def register_sql_tools(registry):
    """注册SQL工具到工具注册中心"""
    tools = [
        QueryBuilderTool(),
        DataExtractorTool(),
        PerformanceOptimizerTool()
    ]
    
    for tool in tools:
        registry.register_tool(tool)
    
    return tools