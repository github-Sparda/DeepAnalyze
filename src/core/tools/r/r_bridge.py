"""
R语言工具桥接器
提供与R语言统计包的交互接口
"""

import subprocess
import json
import tempfile
import os
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from ..tool_interface import ToolInterface, ToolMetadata, ToolType

class RBridgeTool(ToolInterface):
    """R语言桥接工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="r_bridge",
            description="执行R语言代码并与Python数据交互",
            version="1.0.0",
            tool_type=ToolType.STATISTICAL_ANALYSIS,
            supported_languages=["R", "Python"],
            parameters={
                "r_code": "str - R语言代码",
                "data": "pandas.DataFrame - 输入数据 (可选)",
                "return_variables": "list - 要返回的R变量名",
                "packages": "list - 需要加载的R包"
            },
            returns="dict - 执行结果和返回变量",
            data_examples=[
                "r_bridge(r_code='summary(mtcars)', packages=['base'])",
                "r_bridge(r_code='lm(mpg ~ wt, data=cars_data)', data=cars_df, return_variables=['coefficients'])"
            ]
        )
        super().__init__("r_bridge", metadata)
        self.r_available = self._check_r_availability()
    
    def _check_r_availability(self) -> bool:
        """检查R环境是否可用"""
        try:
            result = subprocess.run(['R', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def validate_parameters(self, **kwargs) -> bool:
        if not self.r_available:
            raise Exception("R环境不可用")
        return 'r_code' in kwargs
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        r_code = kwargs['r_code']
        data = kwargs.get('data')
        return_variables = kwargs.get('return_variables', [])
        packages = kwargs.get('packages', ['base'])
        
        # 准备R脚本
        r_script = self._prepare_r_script(r_code, data, return_variables, packages)
        
        # 执行R脚本
        result = self._execute_r_script(r_script)
        
        return result
    
    def _prepare_r_script(self, r_code: str, data: Optional[pd.DataFrame], 
                         return_variables: List[str], packages: List[str]) -> str:
        """准备R脚本"""
        script_lines = []
        
        # 加载必要的包
        for package in packages:
            script_lines.append(f"library({package})")
        
        # 如果有数据，将其传递给R
        if data is not None:
            # 将DataFrame保存为CSV并读入R
            temporary_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            data.to_csv(temporary_file.name, index=False)
            temporary_file.close()
            
            script_lines.append(f'data_py <- read.csv("{temporary_file.name}")')
            script_lines.append('rm(list=ls(pattern="^data_py$"))')  # 清理临时文件
            
            # 删除临时文件
            script_lines.append(f'unlink("{temporary_file.name}")')
        
        # 添加用户R代码
        script_lines.append(r_code)
        
        # 收集返回变量
        if return_variables:
            script_lines.append('result_list <- list()')
            for var in return_variables:
                script_lines.append(f'if(exists("{var}")) result_list${var} <- {var}')
            script_lines.append('result_list')
        else:
            script_lines.append('NULL')
        
        return '\n'.join(script_lines)
    
    def _execute_r_script(self, r_script: str) -> Dict[str, Any]:
        """执行R脚本"""
        try:
            # 创建临时R脚本文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
                f.write(r_script)
                script_path = f.name
            
            # 执行R脚本
            result = subprocess.run([
                'R', '--slave', '--no-restore', '--file=' + script_path
            ], capture_output=True, text=True, timeout=300)
            
            # 清理临时文件
            os.unlink(script_path)
            
            if result.returncode != 0:
                raise Exception(f"R脚本执行失败: {result.stderr}")
            
            # 解析输出
            output = result.stdout.strip()
            return {
                'success': True,
                'output': output,
                'r_code_executed': r_script
            }
            
        except subprocess.TimeoutExpired:
            raise Exception("R脚本执行超时")
        except Exception as e:
            raise Exception(f"R桥接执行错误: {str(e)}")

class RStatisticalPackagesTool(ToolInterface):
    """R统计包封装工具"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="r_statistical",
            description="封装常用的R统计分析包功能",
            version="1.0.0",
            tool_type=ToolType.STATISTICAL_ANALYSIS,
            supported_languages=["R", "Python"],
            parameters={
                "analysis_type": "str - 分析类型 (regression, anova, clustering, time_series)",
                "data": "pandas.DataFrame - 分析数据",
                "formula": "str - 统计公式 (如: y ~ x1 + x2)",
                "parameters": "dict - 分析参数"
            },
            returns="dict - 分析结果",
            data_examples=[
                "r_statistical(analysis_type='regression', data=sales_df, formula='sales ~ advertising + price')",
                "r_statistical(analysis_type='clustering', data=customer_df, parameters={'centers': 3})"
            ]
        )
        super().__init__("r_statistical", metadata)
        self.bridge = RBridgeTool()
    
    def validate_parameters(self, **kwargs) -> bool:
        required_params = ['analysis_type', 'data']
        return all(param in kwargs for param in required_params)
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        analysis_type = kwargs['analysis_type']
        data = kwargs['data']
        formula = kwargs.get('formula')
        parameters = kwargs.get('parameters', {})
        
        # 根据分析类型生成相应的R代码
        r_code, return_vars = self._generate_docs_analysis_code(analysis_type, formula, parameters)
        
        # 执行分析
        result = self.bridge.execute(
            r_code=r_code,
            data=data,
            return_variables=return_vars,
            packages=self._get_required_packages(analysis_type)
        )
        
        return {
            'analysis_type': analysis_type,
            'parameters': parameters,
            'result': result
        }
    
    def _generate_docs_analysis_code(self, analysis_type: str, formula: Optional[str], 
                               parameters: Dict[str, Any]) -> tuple:
        """生成分析R代码"""
        if analysis_type == 'regression':
            return self._generate_regression_code(formula, parameters)
        elif analysis_type == 'anova':
            return self._generate_anova_code(formula, parameters)
        elif analysis_type == 'clustering':
            return self._generate_clustering_code(parameters)
        elif analysis_type == 'time_series':
            return self._generate_time_series_code(parameters)
        else:
            raise ValueError(f"不支持的分析类型: {analysis_type}")
    
    def _generate_regression_code(self, formula: str, parameters: Dict[str, Any]) -> tuple:
        """生成回归分析代码"""
        method = parameters.get('method', 'lm')
        r_code = f'''
# 线性回归分析
model <- {method}({formula}, data=data_py)
summary_result <- summary(model)
coefficients <- coef(model)
fitted_values <- fitted(model)
residuals <- residuals(model)
        '''
        return_vars = ['summary_result', 'coefficients', 'fitted_values', 'residuals']
        return r_code, return_vars
    
    def _generate_anova_code(self, formula: str, parameters: Dict[str, Any]) -> tuple:
        """生成方差分析代码"""
        r_code = f'''
# 方差分析
model <- aov({formula}, data=data_py)
anova_result <- anova(model)
summary_result <- summary(model)
        '''
        return_vars = ['anova_result', 'summary_result']
        return r_code, return_vars
    
    def _generate_clustering_code(self, parameters: Dict[str, Any]) -> tuple:
        """生成聚类分析代码"""
        method = parameters.get('method', 'kmeans')
        centers = parameters.get('centers', 3)
        
        r_code = f'''
# 聚类分析
# 选择数值型变量
numeric_data <- data_py[sapply(data_py, is.numeric)]
# 标准化数据
scaled_data <- scale(numeric_data)
# K-means聚类
cluster_result <- kmeans(scaled_data, centers={centers})
cluster_centers <- cluster_result$centers
cluster_assignments <- cluster_result$cluster
        '''
        return_vars = ['cluster_result', 'cluster_centers', 'cluster_assignments']
        return r_code, return_vars
    
    def _generate_time_series_code(self, parameters: Dict[str, Any]) -> tuple:
        """生成时间序列分析代码"""
        frequency = parameters.get('frequency', 12)  # 默认月度数据
        
        r_code = f'''
# 时间序列分析
# 假设第一列是时间序列数据
ts_data <- ts(data_py[,1], frequency={frequency})
# 基本统计
ts_stats <- summary(ts_data)
# 分解
decomp <- decompose(ts_data)
# 简单预测
forecast_result <- predict(HoltWinters(ts_data), n.ahead=12)
        '''
        return_vars = ['ts_stats', 'decomp', 'forecast_result']
        return r_code, return_vars
    
    def _get_required_packages(self, analysis_type: str) -> List[str]:
        """获取所需R包"""
        package_map = {
            'regression': ['stats'],
            'anova': ['stats'],
            'clustering': ['stats'],
            'time_series': ['stats', 'forecast']
        }
        return package_map.get(analysis_type, ['stats'])

# 注册所有R工具
def register_r_tools(registry):
    """注册R工具到工具注册中心"""
    tools = [
        RBridgeTool(),
        RStatisticalPackagesTool()
    ]
    
    for tool in tools:
        registry.register_tool(tool)
    
    return tools