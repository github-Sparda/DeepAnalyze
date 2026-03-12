"""常量定义模块.

存放项目中重复使用的常量，减少代码重复.
"""

# 分析工具包模块列表
ANALYTICS_TOOLKIT_MODULES = [
    "data_profile",
    "data_quality",
    "stats_tests",
    "correlation",
    "feature_selection",
]

# 模型相关输出文件列表
MODEL_OUTPUT_FILES = [
    "model_results.json",
    "model_eval.json",
    "model_performance_comparison.csv",
    "roc_curve.png",
    "pr_curve.png",
]

# 统计分析输出文件列表
STATS_OUTPUT_FILES = [
    "stats_results.json",
    "multiple_testing.json",
    "stats_summary.json",
    "top_features.json",
    "differential_features_table.csv",
]

# 假设类型映射
HYPOTHESIS_TYPE_MAP = {
    "difference": ["difference", "diff", "compare", "comparison"],
    "correlation": ["correlation", "correlate", "association", "associate"],
    "causal": ["causal", "causality", "cause", "effect"],
    "predictive": ["predictive", "prediction", "predict", "forecast"],
    "exploratory": ["exploratory", "explore", "discovery"],
}

# 方法家族关键词映射
METHOD_FAMILY_KEYWORDS = {
    "correlation": ["correlation", "spearman", "pearson", "kendall"],
    "machine_learning": ["random forest", "neural network", "svm", "classifier", "regression"],
    "embedding": ["pca", "tsne", "umap", "embedding"],
    "survival": ["cox", "kaplan-meier", "survival"],
    "time_series": ["time series", "arima", "seasonal", "trend"],
    "causal_inference": ["causal", "propensity", "instrumental variable"],
    "statistical_inference": ["t-test", "anova", "chi-square", "mann-whitney"],
}
