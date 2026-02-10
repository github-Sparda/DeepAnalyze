# 高级数据分析功能使用文档

## 概述
DeepAnalyze高级数据分析模块提供了全面的数据分析能力，包括数据质量评估、统计检验、洞察生成等功能。

## 核心特性

### 1. 多格式数据支持
- CSV、Excel、JSON、Parquet等多种格式
- 自动数据类型识别和转换
- 编码自动处理

### 2. 数据质量评估
- 缺失值检测和统计
- 重复记录识别
- 异常值检测（IQR方法）
- 数据类型验证
- 基本统计信息生成

### 3. 统计分析功能
- 相关性分析
- t检验
- 正态性检验
- 方差分析（ANOVA）
- 卡方检验
- 回归分析

### 4. 智能洞察生成
- 自动识别数据问题
- 生成处理建议
- 提供分析指导

## 使用方法

### 基本数据分析

```python
from src/core.analytics.advanced_analyzer import analyze_dataset, AnalysisType

# 简单数据分析
report = analyze_dataset(
    file_path="data/sales.csv",
    session_id="docs/analysis_session_001",
    docs/analysis_types=[AnalysisType.DESCRIPTIVE, AnalysisType.INFERENTIAL]
)

print(f"数据形状: {report['data_summary']['shape']}")
print(f"发现的洞察: {len(report['insights'])} 条")
```

### 详细分析流程

```python
from src/core.analytics.advanced_analyzer import (
    AdvancedDataAnalyzer,
    StatisticalTest,
    DataQualityReport
)
import pandas as pd

# 创建分析器
analyzer = AdvancedDataAnalyzer()

# 1. 加载数据
df = analyzer.load_data("customer_data.xlsx")
if df is None:
    print("数据加载失败")
    exit()

# 2. 数据质量评估
quality_report = analyzer.assess_data_quality(df)
print(f"缺失值总数: {sum(quality_report.missing_values.values())}")
print(f"重复记录数: {quality_report.duplicates}")

# 3. 执行统计检验
stat_results = analyzer.perform_statistical_tests(
    df,
    test_types=[
        StatisticalTest.CORRELATION,
        StatisticalTest.T_TEST,
        StatisticalTest.NORMALITY
    ],
    target_variable="sales_amount",
    group_variable="region"
)

for result in stat_results:
    print(f"{result.test_type.value}: p={result.p_value:.4f}")
```

### 数据质量报告详解

```python
# 数据质量报告结构
quality_report = {
    "missing_values": {"column1": count1, "column2": count2},
    "duplicates": 15,
    "outliers": {
        "sales": [100000, 120000, 95000],
        "age": [85, 92, 78]
    },
    "data_types": {
        "name": "object",
        "age": "int64",
        "salary": "float64"
    },
    "basic_stats": {
        "age": {
            "count": 1000.0,
            "mean": 35.2,
            "std": 8.7,
            "min": 18.0,
            "max": 65.0
        }
    }
}
```

## 统计检验说明

### 相关性分析 (CORRELATION)
```python
results = analyzer.perform_statistical_tests(
    df,
    [StatisticalTest.CORRELATION]
)
# 返回变量间的皮尔逊相关系数矩阵
```

### t检验 (T_TEST)
```python
results = analyzer.perform_statistical_tests(
    df,
    [StatisticalTest.T_TEST],
    target_variable="performance_score",
    group_variable="training_group"
)
# 比较两个组的均值差异
```

### 正态性检验 (NORMALITY)
```python
results = analyzer.perform_statistical_tests(
    df,
    [StatisticalTest.NORMALITY],
    target_variable="measurement"
)
# 检验数据是否符合正态分布
```

## 分析类型说明

### 描述性分析 (DESCRIPTIVE)
```python
report = analyze_dataset(
    file_path="data.csv",
    session_id="session_001",
    docs/analysis_types=[AnalysisType.DESCRIPTIVE]
)
# 包含：数据概览、基本统计、分布特征
```

### 推断性分析 (INFERENTIAL)
```python
report = analyze_dataset(
    file_path="data.csv",
    session_id="session_001",
    docs/analysis_types=[AnalysisType.INFERENTIAL]
)
# 包含：统计检验、假设验证、显著性分析
```

### 预测分析 (PREDICTIVE)
```python
# 预留接口，未来版本支持
```

## 输出报告结构

```python
report = {
    "session_id": "docs/analysis_session_001",
    "generated_at": "2026-02-07T23:29:27.719729",
    "data_summary": {
        "shape": [1000, 7],
        "columns": ["col1", "col2", ...],
        "numeric_columns": ["age", "income", ...],
        "categorical_columns": ["gender", "region", ...],
        "memory_usage": "1.85 MB"
    },
    "quality_report": {
        "missing_values": {...},
        "duplicates": 0,
        "outliers_count": {...},
        "data_types": {...}
    },
    "statistical_results": [
        {
            "test_type": "correlation",
            "statistic": -0.0268,
            "p_value": 0.05,
            "interpretation": "变量间相关性: -0.027"
        }
    ],
    "insights": [
        "数据缺失率为 1.5%，建议进行缺失值处理",
        "在列 age, income 中发现异常值，建议进一步检查"
    ],
    "recommendations": [
        "建议使用均值/中位数填充或删除含有缺失值的行",
        "建议进行描述性统计分析和相关性分析"
    ]
}
```

## 最佳实践

### 1. 数据准备
```python
# 确保数据格式正确
# CSV文件应包含标题行
# 数值型数据避免混杂文本
# 日期格式保持一致

# 推荐的数据结构
df = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=1000),
    'sales': np.random.normal(1000, 200, 1000),
    'region': np.random.choice(['North', 'South', 'East', 'West'], 1000),
    'customer_type': np.random.choice(['VIP', 'Regular'], 1000)
})
```

### 2. 分析策略
```python
# 根据数据特点选择分析类型
if df.shape[0] < 100:
    # 小数据集：重点关注描述性分析
    docs/analysis_types = [AnalysisType.DESCRIPTIVE]
elif df.select_dtypes(include=[np.number]).shape[1] > 5:
    # 多变量：增加相关性分析
    docs/analysis_types = [AnalysisType.DESCRIPTIVE, AnalysisType.INFERENTIAL]
else:
    # 标准分析
    docs/analysis_types = [AnalysisType.DESCRIPTIVE, AnalysisType.INFERENTIAL]
```

### 3. 结果解释
```python
# 正确解释统计结果
def interpret_results(report):
    for result in report['statistical_results']:
        if result['p_value'] < 0.05:
            print(f"{result['test_type']} 显示显著差异")
        else:
            print(f"{result['test_type']} 未显示显著差异")
    
    # 关注效应大小，不仅仅是p值
    # 考虑实际意义而非仅仅统计显著性
```

## 错误处理

### 常见错误及解决方案

```python
# 文件不存在
try:
    df = analyzer.load_data("nonexistent.csv")
except FileNotFoundError:
    print("请检查文件路径是否正确")

# 不支持的文件格式
try:
    df = analyzer.load_data("data.txt")
except ValueError as e:
    print(f"文件格式错误: {e}")

# 数据质量问题
quality_report = analyzer.assess_data_quality(df)
if sum(quality_report.missing_values.values()) > len(df) * 0.1:
    print("缺失值过多，建议数据清洗后再分析")
```

## 性能优化

### 大数据集处理
```python
# 对于大型数据集的优化策略
if len(df) > 100000:
    # 采样分析
    sample_df = df.sample(10000)
    report = analyzer.generate_docs/analysis_report(sample_df, session_id)
    
    # 分批处理
    batch_size = 50000
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i+batch_size]
        # 处理批次数据
```

### 内存优化
```python
# 优化内存使用
df = pd.read_csv("large_file.csv", 
                 dtype={'id': 'int32', 'value': 'float32'},
                 nrows=100000)  # 限制行数
```

## API参考

### 主要类和方法

#### AdvancedDataAnalyzer
- `load_data()`: 加载数据文件
- `assess_data_quality()`: 评估数据质量
- `perform_statistical_tests()`: 执行统计检验
- `generate_docs/analysis_report()`: 生成综合分析报告

#### 枚举类型
- `AnalysisType`: 分析类型枚举
- `StatisticalTest`: 统计检验类型枚举

#### 数据类
- `DataQualityReport`: 数据质量报告
- `StatisticalResult`: 统计分析结果

---
*文档版本: 1.0*
*最后更新: 2026-02-07*