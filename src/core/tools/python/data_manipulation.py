"""
Python数据分析工具集合
提供常用的数据处理、统计分析、可视化等功能
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
from ..tool_interface import ToolInterface, ToolMetadata, ToolType

class DataLoadTool(ToolInterface):
    """数据加载工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="data_loader",
            description="从文件加载数据到DataFrame",
            version="1.0.0",
            tool_type=ToolType.DATA_PROCESSING,
            supported_languages=["Python"],
            parameters={
                "file_path": "str - 文件路径",
                "file_type": "str - 文件类型 (csv, excel, json, parquet)",
                "encoding": "str - 文件编码 (默认utf-8)",
                "sep": "str - 分隔符 (CSV文件专用)"
            },
            returns="pandas.DataFrame - 加载的数据",
            data_examples=[
                "data_loader(file_path='data.csv', file_type='csv')",
                "data_loader(file_path='data.xlsx', file_type='excel')"
            ]
        )
        super().__init__("data_loader", metadata)
    
    def validate_parameters(self, **kwargs) -> bool:
        required_params = ['file_path', 'file_type']
        return all(param in kwargs for param in required_params)
    
    def execute(self, **kwargs) -> pd.DataFrame:
        file_path = kwargs['file_path']
        file_type = kwargs['file_type']
        encoding = kwargs.get('encoding', 'utf-8')
        sep = kwargs.get('sep', ',')
        
        if file_type == 'csv':
            return pd.read_csv(file_path, encoding=encoding, sep=sep)
        elif file_type == 'excel':
            return pd.read_excel(file_path)
        elif file_type == 'json':
            return pd.read_json(file_path)
        elif file_type == 'parquet':
            return pd.read_parquet(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

class DataCleanTool(ToolInterface):
    """数据清洗工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="data_cleaner",
            description="数据清洗和预处理",
            version="1.0.0",
            tool_type=ToolType.DATA_PROCESSING,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame - 待清洗的数据",
                "drop_missing": "bool - 是否删除缺失值行",
                "fill_missing": "dict - 缺失值填充策略",
                "remove_duplicates": "bool - 是否删除重复行",
                "convert_types": "dict - 数据类型转换映射"
            },
            returns="pandas.DataFrame - 清洗后的数据",
            data_examples=[
                "data_cleaner(data=df, drop_missing=True)",
                "data_cleaner(data=df, fill_missing={'age': 'mean', 'salary': 0})"
            ]
        )
        super().__init__("data_cleaner", metadata)
    
    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs and isinstance(kwargs['data'], pd.DataFrame)
    
    def execute(self, **kwargs) -> pd.DataFrame:
        data = kwargs['data'].copy()
        
        # 删除缺失值
        if kwargs.get('drop_missing', False):
            data = data.dropna()
        
        # 填充缺失值
        if 'fill_missing' in kwargs:
            fill_strategy = kwargs['fill_missing']
            for column, strategy in fill_strategy.items():
                if column in data.columns:
                    if strategy == 'mean':
                        data[column] = data[column].fillna(data[column].mean())
                    elif strategy == 'median':
                        data[column] = data[column].fillna(data[column].median())
                    elif strategy == 'mode':
                        data[column] = data[column].fillna(data[column].mode()[0])
                    else:
                        data[column] = data[column].fillna(strategy)
        
        # 删除重复行
        if kwargs.get('remove_duplicates', False):
            data = data.drop_duplicates()
        
        # 数据类型转换
        if 'convert_types' in kwargs:
            type_mapping = kwargs['convert_types']
            for column, dtype in type_mapping.items():
                if column in data.columns:
                    data[column] = data[column].astype(dtype)
        
        return data

class StatisticalSummaryTool(ToolInterface):
    """统计摘要工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="statistical_summary",
            description="生成数据的统计摘要信息",
            version="1.0.0",
            tool_type=ToolType.STATISTICAL_ANALYSIS,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame - 分析数据",
                "include_categorical": "bool - 是否包含分类变量",
                "percentiles": "list - 百分位数列表"
            },
            returns="dict - 统计摘要信息",
            data_examples=[
                "statistical_summary(data=df)",
                "statistical_summary(data=df, include_categorical=True, percentiles=[0.25, 0.75])"
            ]
        )
        super().__init__("statistical_summary", metadata)
    
    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs and isinstance(kwargs['data'], pd.DataFrame)
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        data = kwargs['data']
        include_categorical = kwargs.get('include_categorical', False)
        percentiles = kwargs.get('percentiles', [0.25, 0.5, 0.75])
        
        # 数值型变量统计
        numeric_data = data.select_dtypes(include=[np.number])
        numeric_summary = numeric_data.describe(percentiles=percentiles).to_dict()
        
        result = {
            'numeric_summary': numeric_summary,
            'shape': data.shape,
            'columns': list(data.columns),
            'dtypes': {col: str(dtype) for col, dtype in data.dtypes.items()},
            'missing_values': data.isnull().sum().to_dict()
        }
        
        # 分类变量统计
        if include_categorical:
            categorical_data = data.select_dtypes(include=['object', 'category'])
            categorical_summary = {}
            for col in categorical_data.columns:
                categorical_summary[col] = {
                    'unique_count': categorical_data[col].nunique(),
                    'top_values': categorical_data[col].value_counts().head().to_dict(),
                    'missing_count': categorical_data[col].isnull().sum()
                }
            result['categorical_summary'] = categorical_summary
        
        return result

# 注册所有工具
def register_python_tools(registry):
    """注册Python工具到工具注册中心"""
    tools = [
        DataLoadTool(),
        DataCleanTool(),
        StatisticalSummaryTool()
    ]
    
    for tool in tools:
        registry.register_tool(tool)
    
    return tools