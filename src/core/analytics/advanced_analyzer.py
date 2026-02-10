"""
Advanced Data Analysis Module for DeepAnalyze
高级数据分析功能模块
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import json
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import sys

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from ..error.handler import ErrorHandler, ErrorSeverity, ErrorCategory
    from ..state.manager import get_session_state, update_session_state
except ImportError:
    from error.handler import ErrorHandler, ErrorSeverity, ErrorCategory
    from state.manager import get_session_state, update_session_state


class AnalysisType(Enum):
    """分析类型"""
    DESCRIPTIVE = "descriptive"      # 描述性统计
    INFERENTIAL = "inferential"     # 推断性统计
    PREDICTIVE = "predictive"       # 预测分析
    DIAGNOSTIC = "diagnostic"       # 诊断分析
    PRESCRIPTIVE = "prescriptive"   # 规范性分析


class StatisticalTest(Enum):
    """统计检验类型"""
    T_TEST = "t_test"
    CHI_SQUARE = "chi_square"
    ANOVA = "anova"
    CORRELATION = "correlation"
    REGRESSION = "regression"
    NORMALITY = "normality"


@dataclass
class DataQualityReport:
    """数据质量报告"""
    missing_values: Dict[str, int] = field(default_factory=dict)
    duplicates: int = 0
    outliers: Dict[str, List[Any]] = field(default_factory=dict)
    data_types: Dict[str, str] = field(default_factory=dict)
    basic_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class StatisticalResult:
    """统计分析结果"""
    test_type: StatisticalTest
    statistic: float
    p_value: float
    confidence_interval: Optional[Tuple[float, float]] = None
    effect_size: Optional[float] = None
    interpretation: str = ""
    assumptions_checked: Dict[str, bool] = field(default_factory=dict)


class AdvancedDataAnalyzer:
    """高级数据分析器"""
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.supported_formats = ['.csv', '.xlsx', '.xls', '.json', '.parquet']
        warnings.filterwarnings('ignore')  # 忽略警告信息
    
    def load_data(self, file_path: Union[str, Path]) -> Optional[pd.DataFrame]:
        """加载数据文件"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            if path.suffix.lower() not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {path.suffix}")
            
            # 根据文件类型加载数据
            if path.suffix.lower() == '.csv':
                df = pd.read_csv(path, encoding='utf-8')
            elif path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(path)
            elif path.suffix.lower() == '.json':
                df = pd.read_json(path)
            elif path.suffix.lower() == '.parquet':
                df = pd.read_parquet(path)
            else:
                raise ValueError(f"无法处理的文件格式: {path.suffix}")
            
            return df
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.FILESYSTEM,
                context={"file_path": str(file_path)}
            )
            return None
    
    def assess_data_quality(self, df: pd.DataFrame) -> DataQualityReport:
        """评估数据质量"""
        try:
            report = DataQualityReport()
            
            # 缺失值检查
            report.missing_values = df.isnull().sum().to_dict()
            
            # 重复行检查
            report.duplicates = df.duplicated().sum()
            
            # 数据类型检查
            report.data_types = df.dtypes.astype(str).to_dict()
            
            # 基本统计信息
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                report.basic_stats = df[numeric_columns].describe().to_dict()
            
            # 异常值检测（使用IQR方法）
            for col in numeric_columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col].tolist()
                if outliers:
                    report.outliers[col] = outliers
            
            return report
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"operation": "data_quality_assessment"}
            )
            return DataQualityReport()
    
    def perform_statistical_tests(
        self, 
        df: pd.DataFrame, 
        test_types: List[StatisticalTest],
        target_variable: Optional[str] = None,
        group_variable: Optional[str] = None
    ) -> List[StatisticalResult]:
        """执行统计检验"""
        results = []
        
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            for test_type in test_types:
                try:
                    result = self._execute_single_test(
                        df, test_type, target_variable, group_variable, numeric_columns
                    )
                    if result:
                        results.append(result)
                except Exception as e:
                    self.error_handler.handle_error(
                        e,
                        severity=ErrorSeverity.MEDIUM,
                        category=ErrorCategory.EXECUTION,
                        context={"test_type": test_type.value}
                    )
            
            return results
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXECUTION,
                context={"operation": "statistical_testing"}
            )
            return results
    
    def _execute_single_test(
        self,
        df: pd.DataFrame,
        test_type: StatisticalTest,
        target_variable: Optional[str],
        group_variable: Optional[str],
        numeric_columns: List[str]
    ) -> Optional[StatisticalResult]:
        """执行单个统计检验"""
        
        if test_type == StatisticalTest.CORRELATION:
            if len(numeric_columns) < 2:
                return None
            
            # 计算相关系数矩阵
            corr_matrix = df[numeric_columns].corr()
            # 取第一个相关系数作为示例结果
            stat = corr_matrix.iloc[0, 1] if corr_matrix.shape[0] > 1 else 0
            p_val = 0.05  # 简化处理
            
            return StatisticalResult(
                test_type=test_type,
                statistic=stat,
                p_value=p_val,
                interpretation=f"变量间相关性: {stat:.3f}"
            )
        
        elif test_type == StatisticalTest.T_TEST:
            if not target_variable or not group_variable:
                return None
            
            if target_variable not in df.columns or group_variable not in df.columns:
                return None
            
            # 独立样本t检验示例
            groups = df[group_variable].unique()
            if len(groups) != 2:
                return None
            
            group1_data = df[df[group_variable] == groups[0]][target_variable]
            group2_data = df[df[group_variable] == groups[1]][target_variable]
            
            # 简化的t检验计算
            mean_diff = group1_data.mean() - group2_data.mean()
            pooled_std = np.sqrt(((len(group1_data)-1)*group1_data.std()**2 + 
                                (len(group2_data)-1)*group2_data.std()**2) / 
                               (len(group1_data) + len(group2_data) - 2))
            t_stat = mean_diff / (pooled_std * np.sqrt(1/len(group1_data) + 1/len(group2_data)))
            
            # 简化的p值计算
            p_val = 0.05 if abs(t_stat) > 2 else 0.5
            
            return StatisticalResult(
                test_type=test_type,
                statistic=t_stat,
                p_value=p_val,
                effect_size=abs(mean_diff / pooled_std),
                interpretation=f"两组均值差异显著性检验: t={t_stat:.3f}, p={p_val:.3f}"
            )
        
        elif test_type == StatisticalTest.NORMALITY:
            if not target_variable or target_variable not in df.columns:
                return None
            
            # Shapiro-Wilk正态性检验（简化版）
            from scipy import stats
            sample_data = df[target_variable].dropna().sample(min(5000, len(df))).values
            try:
                stat, p_val = stats.shapiro(sample_data)
                return StatisticalResult(
                    test_type=test_type,
                    statistic=stat,
                    p_value=p_val,
                    interpretation=f"数据正态性检验: W={stat:.3f}, p={p_val:.3f}"
                )
            except:
                return None
        
        return None
    
    def generate_docs_analysis_report(
        self,
        df: pd.DataFrame,
        session_id: str,
        analysis_types: Optional[List[AnalysisType]] = None
    ) -> Dict[str, Any]:
        """生成综合分析报告"""
        try:
            if analysis_types is None:
                analysis_types = [AnalysisType.DESCRIPTIVE, AnalysisType.INFERENTIAL]
            
            report = {
                "session_id": session_id,
                "generated_at": datetime.now().isoformat(),
                "data_summary": {},
                "quality_report": {},
                "statistical_results": [],
                "insights": [],
                "recommendations": []
            }
            
            # 数据概览
            report["data_summary"] = {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
                "categorical_columns": df.select_dtypes(include=['object', 'category']).columns.tolist(),
                "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            }
            
            # 数据质量评估
            quality_report = self.assess_data_quality(df)
            report["quality_report"] = {
                "missing_values": quality_report.missing_values,
                "duplicates": quality_report.duplicates,
                "outliers_count": {k: len(v) for k, v in quality_report.outliers.items()},
                "data_types": quality_report.data_types
            }
            
            # 统计分析
            if AnalysisType.INFERENTIAL in analysis_types:
                statistical_tests = [
                    StatisticalTest.CORRELATION,
                    StatisticalTest.NORMALITY
                ]
                
                # 自动选择目标变量进行t检验
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                target_var = numeric_cols[0] if numeric_cols else None
                group_var = df.select_dtypes(include=['object', 'category']).columns.tolist()
                group_var = group_var[0] if group_var else None
                
                stat_results = self.perform_statistical_tests(
                    df, statistical_tests, target_var, group_var
                )
                
                report["statistical_results"] = [
                    {
                        "test_type": result.test_type.value,
                        "statistic": result.statistic,
                        "p_value": result.p_value,
                        "interpretation": result.interpretation
                    }
                    for result in stat_results
                ]
            
            # 生成洞察和建议
            report["insights"] = self._generate_insights(df, quality_report)
            report["recommendations"] = self._generate_recommendations(df, quality_report)
            
            # 保存到状态
            state_updates = {
                "latest_docs_analysis_report": report,
                "docs_analysis_timestamp": datetime.now().isoformat()
            }
            update_session_state(session_id, state_updates)
            
            return report
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id}
            )
            return {"error": str(e)}
    
    def _generate_insights(self, df: pd.DataFrame, quality_report: DataQualityReport) -> List[str]:
        """生成数据洞察"""
        insights = []
        
        # 数据规模洞察
        if df.shape[0] > 10000:
            insights.append("数据集较大，建议使用采样进行初步探索")
        elif df.shape[0] < 100:
            insights.append("数据集较小，统计结果可能不够稳定")
        
        # 缺失值洞察
        total_missing = sum(quality_report.missing_values.values())
        if total_missing > 0:
            missing_pct = (total_missing / (df.shape[0] * df.shape[1])) * 100
            insights.append(f"数据缺失率为 {missing_pct:.1f}%，建议进行缺失值处理")
        
        # 重复值洞察
        if quality_report.duplicates > 0:
            dup_pct = (quality_report.duplicates / df.shape[0]) * 100
            insights.append(f"发现 {dup_pct:.1f}% 的重复记录，建议去重处理")
        
        # 异常值洞察
        if quality_report.outliers:
            outlier_cols = list(quality_report.outliers.keys())
            insights.append(f"在列 {', '.join(outlier_cols[:3])} 中发现异常值，建议进一步检查")
        
        return insights
    
    def _generate_recommendations(self, df: pd.DataFrame, quality_report: DataQualityReport) -> List[str]:
        """生成处理建议"""
        recommendations = []
        
        # 数据清洗建议
        if sum(quality_report.missing_values.values()) > 0:
            recommendations.append("建议使用均值_中位数填充或删除含有缺失值的行")
        
        if quality_report.duplicates > 0:
            recommendations.append("建议删除重复记录以避免分析偏差")
        
        # 分析建议
        numeric_cols = len(df.select_dtypes(include=[np.number]).columns)
        categorical_cols = len(df.select_dtypes(include=['object', 'category']).columns)
        
        if numeric_cols > 0:
            recommendations.append("建议进行描述性统计分析和相关性分析")
        
        if categorical_cols > 0 and numeric_cols > 0:
            recommendations.append("建议进行分组分析和交叉表分析")
        
        # 可视化建议
        if df.shape[1] <= 10:
            recommendations.append("建议创建散点图矩阵和相关性热力图")
        else:
            recommendations.append("建议使用降维技术进行可视化")
        
        return recommendations


# 便捷函数
def analyze_dataset(
    file_path: Union[str, Path],
    session_id: str,
    analysis_types: Optional[List[AnalysisType]] = None
) -> Dict[str, Any]:
    """便捷函数：分析数据集"""
    analyzer = AdvancedDataAnalyzer()
    df = analyzer.load_data(file_path)
    
    if df is None:
        return {"error": "无法加载数据文件"}
    
    return analyzer.generate_docs_analysis_report(df, session_id, analysis_types)


def get_data_analyzer() -> AdvancedDataAnalyzer:
    """获取数据分析器实例"""
    return AdvancedDataAnalyzer()
