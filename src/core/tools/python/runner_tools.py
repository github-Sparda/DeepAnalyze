"""
Python Analytics Runner工具集合

提供高级分析算法的统一入口工具，供LLM Agent发现和使用。
这些工具封装了常用的分析算法，LLM可根据分析目标自主选择使用。
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional
from ..tool_interface import ToolInterface, ToolMetadata, ToolType


class ClusteringRunnerTool(ToolInterface):
    """聚类分析Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="clustering_analysis",
            description="聚类分析统一入口，支持kmeans/hierarchical/dbscan/gmm/spectral/birch等算法，自动选择最佳聚类数和评估指标",
            version="1.0.0",
            tool_type=ToolType.MACHINE_LEARNING,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame或numpy.ndarray - 输入数据",
                "method": "str - 聚类算法: kmeans/hierarchical/dbscan/gmm/spectral/birch/auto",
                "n_clusters": "int - 聚类数(可选，auto时自动估计)"
            },
            returns="dict - 包含labels、centers、metrics(轮廓系数等)的字典",
            data_examples=[
                "clustering_analysis(data=df, method='kmeans', n_clusters=3)",
                "clustering_analysis(data=X, method='auto')"
            ]
        )
        super().__init__("clustering_analysis", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import ClusteringRunner
        runner = ClusteringRunner()
        return runner.run(
            data=kwargs['data'],
            method=kwargs.get('method', 'auto'),
            n_clusters=kwargs.get('n_clusters')
        )


class DimReductionRunnerTool(ToolInterface):
    """降维分析Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="dimension_reduction",
            description="降维算法统一入口，支持PCA/LDA/ICA/Factor/TruncatedSVD，自动标准化和方差解释",
            version="1.0.0",
            tool_type=ToolType.MACHINE_LEARNING,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame或numpy.ndarray - 输入数据",
                "method": "str - 降维算法: pca/lda/ica/factor/truncated_svd/auto",
                "n_components": "int - 目标维度数(默认自动)"
            },
            returns="dict - 包含transformed_data、explained_variance_ratio、components的字典",
            data_examples=[
                "dimension_reduction(data=df, method='pca', n_components=5)",
                "dimension_reduction(data=X, method='auto')"
            ]
        )
        super().__init__("dimension_reduction", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import DimReductionRunner
        runner = DimReductionRunner()
        return runner.run(
            data=kwargs['data'],
            method=kwargs.get('method', 'auto'),
            n_components=kwargs.get('n_components')
        )


class ManifoldRunnerTool(ToolInterface):
    """流形学习Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="manifold_learning",
            description="流形学习统一入口，支持Isomap/LLE/MDS/t-SNE/谱嵌入等非线性降维",
            version="1.0.0",
            tool_type=ToolType.MACHINE_LEARNING,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame或numpy.ndarray - 输入数据",
                "method": "str - 算法: isomap/lle/mds/tsne/spectral_embedding/auto",
                "n_components": "int - 目标维度(默认2)"
            },
            returns="dict - 包含embedding、reconstruction_error的字典",
            data_examples=[
                "manifold_learning(data=df, method='tsne', n_components=2)",
                "manifold_learning(data=X, method='isomap')"
            ]
        )
        super().__init__("manifold_learning", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import ManifoldRunner
        runner = ManifoldRunner()
        return runner.run(
            data=kwargs['data'],
            method=kwargs.get('method', 'auto'),
            n_components=kwargs.get('n_components', 2)
        )


class DiscriminativeMLRunnerTool(ToolInterface):
    """判别式机器学习Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="discriminative_ml",
            description="判别式ML统一入口，支持逻辑回归/SVM/随机森林/XGBoost/LightGBM/MLP，自动计算AUC/F1等评估指标",
            version="1.0.0",
            tool_type=ToolType.MACHINE_LEARNING,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame或numpy.ndarray - 输入特征",
                "y": "numpy.ndarray - 标签",
                "method": "str - 算法: logistic_regression/svm/random_forest/gradient_boosting/xgboost/lightgbm/mlp/auto"
            },
            returns="dict - 包含预测结果、特征重要性、交叉验证指标(cv_accuracy/f1等)的字典",
            data_examples=[
                "discriminative_ml(data=df, y=labels, method='random_forest')",
                "discriminative_ml(data=X, y=y, method='xgboost')"
            ]
        )
        super().__init__("discriminative_ml", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs and 'y' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import DiscriminativeRunner
        runner = DiscriminativeRunner()
        return runner.run(
            data=kwargs['data'],
            y=kwargs['y'],
            method=kwargs.get('method', 'auto')
        )


class RegressionRunnerTool(ToolInterface):
    """回归分析Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="regression_analysis",
            description="回归分析统一入口，支持线性/岭/lasso/弹性网络/随机森林/GBDT/SVR/MLP，自动计算R2/RMSE/MAE",
            version="1.0.0",
            tool_type=ToolType.STATISTICAL_ANALYSIS,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame或numpy.ndarray - 输入特征",
                "y": "numpy.ndarray - 目标变量",
                "method": "str - 算法: linear/ridge/lasso/elastic_net/polynomial/random_forest/gradient_boosting/svr/mlp/auto"
            },
            returns="dict - 包含系数/特征重要性、R2/RMSE/MAE、交叉验证指标的字典",
            data_examples=[
                "regression_analysis(data=df, y=target, method='linear')",
                "regression_analysis(data=X, y=y, method='random_forest')"
            ]
        )
        super().__init__("regression_analysis", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs and 'y' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import RegressionRunner
        runner = RegressionRunner()
        return runner.run(
            data=kwargs['data'],
            y=kwargs['y'],
            method=kwargs.get('method', 'auto')
        )


class StatisticsRunnerTool(ToolInterface):
    """统计分析Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="statistical_analysis",
            description="统计分析统一入口，支持描述统计/t检验/方差分析/相关性分析/多重比较校正(FDR/Bonferroni)，自动计算效应量",
            version="1.0.0",
            tool_type=ToolType.STATISTICAL_ANALYSIS,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame - 输入数据",
                "analysis_type": "str - 分析类型: descriptive/ttest/anova/correlation/multiple_testing/full",
                "group_col": "str - 分组列名(用于t检验/方差分析)",
                "correction": "str - 多重比较校正方法: fdr/bonferroniholm/sidak/scheffe(默认fdr)"
            },
            returns="dict - 包含统计结果、p值、效应量、校正后p值的字典",
            data_examples=[
                "statistical_analysis(data=df, analysis_type='descriptive')",
                "statistical_analysis(data=df, analysis_type='ttest', group_col='group')",
                "statistical_analysis(data=df, analysis_type='multiple_testing', correction='fdr')"
            ]
        )
        super().__init__("statistical_analysis", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs and 'analysis_type' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import StatisticsRunner
        runner = StatisticsRunner()
        analysis_type = kwargs.get('analysis_type', 'descriptive')

        if analysis_type == 'descriptive':
            return runner.run_descriptive(kwargs['data'])
        elif analysis_type == 'ttest':
            return runner.run_ttest(kwargs['data'], kwargs.get('group_col'))
        elif analysis_type == 'anova':
            return runner.run_anova(kwargs['data'], kwargs.get('group_col'))
        elif analysis_type == 'correlation':
            return runner.run_correlation(kwargs['data'])
        elif analysis_type == 'multiple_testing':
            return runner.run_multiple_testing_correction(kwargs['data'], kwargs.get('correction', 'fdr'))
        elif analysis_type == 'full':
            return runner.run_full_analysis(kwargs['data'], kwargs.get('group_col'))
        else:
            return {"status": "error", "message": f"Unknown analysis_type: {analysis_type}"}


class GenerativeMLRunnerTool(ToolInterface):
    """生成式机器学习Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="generative_ml",
            description="生成式ML统一入口，支持VAE/GMM/PCA/Factor/NMF，可生成新样本和学习隐变量表示",
            version="1.0.0",
            tool_type=ToolType.MACHINE_LEARNING,
            supported_languages=["Python"],
            parameters={
                "data": "pandas.DataFrame或numpy.ndarray - 输入数据",
                "method": "str - 算法: vae/gmm/pca/factor_analysis/nmf/auto",
                "n_components": "int - 隐变量/成分数"
            },
            returns="dict - 包含embedding、generated_samples、reconstruction_error的字典",
            data_examples=[
                "generative_ml(data=df, method='pca', n_components=5)",
                "generative_ml(data=X, method='gmm', n_components=3)"
            ]
        )
        super().__init__("generative_ml", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'data' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import GenerativeRunner
        runner = GenerativeRunner()
        return runner.run(
            data=kwargs['data'],
            method=kwargs.get('method', 'auto'),
            n_components=kwargs.get('n_components')
        )


class OptimizationRunnerTool(ToolInterface):
    """优化算法Runner工具"""

    def __init__(self):
        metadata = ToolMetadata(
            name="optimization",
            description="优化算法统一入口，支持梯度下降/牛顿法/遗传算法/粒子群/模拟退火/贝叶斯优化",
            version="1.0.0",
            tool_type=ToolType.UTILITY,
            supported_languages=["Python"],
            parameters={
                "func": "callable - 目标函数",
                "x0": "numpy.ndarray - 初始点",
                "method": "str - 算法: gradient_descent/newton/genetic/particle_swarm/simulated_annealing/bayesian/auto",
                "bounds": "tuple - 变量边界 ((min,max), ...)"
            },
            returns="dict - 包含optimal_x、optimal_y、history、converged的字典",
            data_examples=[
                "optimization(func=objective, x0=np.array([0,0]), method='gradient_descent')",
                "optimization(func=obj, x0=init, method='genetic', bounds=((-10,10),(-10,10)))"
            ]
        )
        super().__init__("optimization", metadata)

    def validate_parameters(self, **kwargs) -> bool:
        return 'func' in kwargs and 'x0' in kwargs

    def execute(self, **kwargs) -> Dict[str, Any]:
        from src.core.analytics.toolkit import OptimizationRunner
        runner = OptimizationRunner()
        return runner.run(
            func=kwargs['func'],
            x0=kwargs['x0'],
            method=kwargs.get('method', 'auto'),
            bounds=kwargs.get('bounds')
        )


def register_runner_tools(registry):
    """注册所有Runner工具到工具注册中心"""
    tools = [
        ClusteringRunnerTool(),
        DimReductionRunnerTool(),
        ManifoldRunnerTool(),
        DiscriminativeMLRunnerTool(),
        RegressionRunnerTool(),
        StatisticsRunnerTool(),
        GenerativeMLRunnerTool(),
        OptimizationRunnerTool(),
    ]

    for tool in tools:
        registry.register_tool(tool)

    return tools
