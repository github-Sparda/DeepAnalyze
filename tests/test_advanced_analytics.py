"""
Advanced Analytics Tests and Examples
高级数据分析功能测试和示例
"""

import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from src.core.analytics.advanced_analyzer import (
    AdvancedDataAnalyzer,
    AnalysisType,
    StatisticalTest,
    analyze_dataset
)


def create_sample_data() -> pd.DataFrame:
    """创建示例数据集"""
    np.random.seed(42)
    
    # 创建示例数据
    data = {
        'age': np.random.normal(35, 10, 1000).astype(int),
        'income': np.random.lognormal(10, 0.5, 1000),
        'education': np.random.choice(['高中', '本科', '硕士', '博士'], 1000),
        'department': np.random.choice(['销售', '技术', '市场', '人事'], 1000),
        'performance_score': np.random.normal(75, 15, 1000),
        'satisfaction': np.random.randint(1, 6, 1000),
        'experience_years': np.random.exponential(5, 1000).astype(int)
    }
    
    # 添加一些缺失值
    df = pd.DataFrame(data)
    for col in ['income', 'performance_score']:
        mask = np.random.random(1000) < 0.05  # 5%缺失值
        df.loc[mask, col] = np.nan
    
    # 添加一些异常值
    outlier_indices = np.random.choice(1000, 10, replace=False)
    df.loc[outlier_indices, 'income'] *= 10
    
    return df


def demo_data_loading():
    """演示数据加载功能"""
    print("=== 数据加载功能演示 ===")
    
    analyzer = AdvancedDataAnalyzer()
    
    # 创建临时CSV文件
    df = create_sample_data()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        temp_file = f.name
    
    # 测试数据加载
    loaded_df = analyzer.load_data(temp_file)
    if loaded_df is not None:
        print(f"成功加载数据: {loaded_df.shape}")
        print(f"列名: {list(loaded_df.columns)}")
        print(f"数据类型: {dict(loaded_df.dtypes)}")
    else:
        print("数据加载失败")
    
    # 清理临时文件
    Path(temp_file).unlink()
    
    return loaded_df


def demo_data_quality_assessment(df: pd.DataFrame):
    """演示数据质量评估"""
    print("\n=== 数据质量评估演示 ===")
    
    if df is None:
        print("跳过数据质量评估（无数据）")
        return
    
    analyzer = AdvancedDataAnalyzer()
    quality_report = analyzer.assess_data_quality(df)
    
    print("数据质量报告:")
    print(f"  缺失值: {quality_report.missing_values}")
    print(f"  重复记录: {quality_report.duplicates}")
    print(f"  异常值列数: {len(quality_report.outliers)}")
    print(f"  数值列统计: {len(quality_report.basic_stats)} 个")
    
    # 显示具体的质量问题
    total_missing = sum(quality_report.missing_values.values())
    if total_missing > 0:
        print(f"  总缺失值: {total_missing}")
    
    if quality_report.outliers:
        print("  异常值详情:")
        for col, outliers in list(quality_report.outliers.items())[:2]:
            print(f"    {col}: {len(outliers)} 个异常值")


def demo_statistical_docs_analysis(df: pd.DataFrame):
    """演示统计分析功能"""
    print("\n=== 统计分析演示 ===")
    
    if df is None:
        print("跳过统计分析（无数据）")
        return
    
    analyzer = AdvancedDataAnalyzer()
    
    # 执行多种统计检验
    test_types = [
        StatisticalTest.CORRELATION,
        StatisticalTest.NORMALITY,
        StatisticalTest.T_TEST
    ]
    
    # 自动选择变量
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    target_var = numeric_cols[0] if numeric_cols else None
    group_var = categorical_cols[0] if categorical_cols else None
    
    print(f"目标变量: {target_var}")
    print(f"分组变量: {group_var}")
    
    results = analyzer.perform_statistical_tests(
        df, test_types, target_var, group_var
    )
    
    print(f"执行了 {len(results)} 个统计检验:")
    for result in results:
        print(f"  {result.test_type.value}:")
        print(f"    统计量: {result.statistic:.4f}")
        print(f"    P值: {result.p_value:.4f}")
        print(f"    解释: {result.interpretation}")


def demo_comprehensive_docs_analysis():
    """演示综合分析报告"""
    print("\n=== 综合分析报告演示 ===")
    
    # 创建示例数据
    df = create_sample_data()
    session_id = "analysis_demo_001"
    
    # 生成综合报告
    analyzer = AdvancedDataAnalyzer()
    report = analyzer.generate_docs_analysis_report(
        df, 
        session_id,
        analysis_types=[AnalysisType.DESCRIPTIVE, AnalysisType.INFERENTIAL]
    )
    
    print("综合分析报告:")
    print(f"  会话ID: {report.get('session_id')}")
    print(f"  生成时间: {report.get('generated_at')}")
    
    # 数据概览
    summary = report.get('data_summary', {})
    print(f"  数据维度: {summary.get('shape')}")
    print(f"  数值列: {len(summary.get('numeric_columns', []))} 个")
    print(f"  分类列: {len(summary.get('categorical_columns', []))} 个")
    
    # 质量报告摘要
    quality = report.get('quality_report', {})
    print(f"  缺失值总计: {sum(quality.get('missing_values', {}).values())}")
    print(f"  重复记录: {quality.get('duplicates', 0)}")
    
    # 统计结果
    stat_results = report.get('statistical_results', [])
    print(f"  统计检验数: {len(stat_results)}")
    
    # 洞察和建议
    insights = report.get('insights', [])
    recommendations = report.get('recommendations', [])
    
    print(f"  发现的洞察: {len(insights)} 条")
    for insight in insights[:3]:
        print(f"    • {insight}")
    
    print(f"  处理建议: {len(recommendations)} 条")
    for rec in recommendations[:3]:
        print(f"    • {rec}")


def demo_error_handling():
    """演示错误处理功能"""
    print("\n=== 错误处理演示 ===")
    
    analyzer = AdvancedDataAnalyzer()
    
    # 测试不存在的文件
    result = analyzer.load_data("nonexistent_file.csv")
    print(f"加载不存在文件: {'成功' if result is not None else '失败（正确）'}")
    
    # 测试不支持的格式
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("这不是CSV格式的内容")
        temp_file = f.name
    
    result = analyzer.load_data(temp_file)
    print(f"加载不支持格式: {'成功' if result is not None else '失败（正确）'}")
    
    Path(temp_file).unlink()


def performance_test():
    """性能测试"""
    print("\n=== 性能测试 ===")
    
    import time
    
    # 测试大数据集
    print("测试大数据集处理性能...")
    large_df = create_sample_data()
    # 扩展到更大的数据集
    large_df = pd.concat([large_df] * 10, ignore_index=True)  # 10000行
    
    analyzer = AdvancedDataAnalyzer()
    session_id = "perf_test_large"
    
    start_time = time.time()
    report = analyzer.generate_docs_analysis_report(large_df, session_id)
    end_time = time.time()
    
    print(f"处理 {len(large_df)} 行数据耗时: {end_time - start_time:.2f} 秒")
    print(f"数据大小: {large_df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    print("DeepAnalyze 高级数据分析功能演示")
    print("=" * 50)
    
    try:
        # 执行所有演示
        df = demo_data_loading()
        demo_data_quality_assessment(df)
        demo_statistical_docs_analysis(df)
        demo_comprehensive_docs_analysis()
        demo_error_handling()
        performance_test()
        
        print("\n" + "=" * 50)
        print("🎉 所有演示完成！")
        print("\n高级数据分析功能特点:")
        print("✅ 多格式数据加载支持")
        print("✅ 全面的数据质量评估")
        print("✅ 多种统计检验方法")
        print("✅ 自动化的洞察生成")
        print("✅ 智能的处理建议")
        print("✅ 完善的错误处理机制")
        print("✅ 性能优化的大数据处理")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
