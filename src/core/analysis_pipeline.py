#!/usr/bin/env python3
"""
Complete Analysis Pipeline - 符合OpenSpec规范的完整分析流水线
集成假设规划、代码生成、执行、分析和报告生成
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 导入核心组件
from src.core.session_manager import SessionManager
from src.core.enhanced_hypothesis_planner import EnhancedHypothesisPlanner
from src.core.orchestration.llm import LLMClient

class AnalysisPipeline:
    """完整的分析流水线"""
    
    def __init__(self):
        # 初始化核心组件
        self.session_manager = SessionManager()
        self.llm_client = None
        self.hypothesis_planner = EnhancedHypothesisPlanner()
        self.hypothesis_planner.set_session_manager(self.session_manager)
        
        # 尝试初始化LLM客户端
        try:
            self.llm_client = LLMClient()
            self.hypothesis_planner.llm_client = self.llm_client
            print("✅ LLM客户端初始化成功")
        except Exception as e:
            print(f"⚠️ LLM客户端初始化失败: {e}")
            print("将继续使用默认假设生成功能")
    
    def load_and_analyze_data(self, data_file: str) -> Dict[str, Any]:
        """加载并初步分析数据"""
        print(f"📂 加载数据文件: {data_file}")
        
        try:
            # 根据文件扩展名选择读取方法
            if data_file.endswith('.xlsx') or data_file.endswith('.xls'):
                df = pd.read_excel(data_file)
            elif data_file.endswith('.csv'):
                df = pd.read_csv(data_file)
            elif data_file.endswith('.json'):
                df = pd.read_json(data_file)
            else:
                raise ValueError(f"不支持的文件格式: {data_file}")
            
            print(f"✅ 数据加载成功: {len(df)} 行 × {len(df.columns)} 列")
            
            # 生成数据摘要
            data_summary = {
                'data_source': data_file,
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_columns': len(df.select_dtypes(include=['number']).columns),
                'categorical_columns': len(df.select_dtypes(include=['object', 'category']).columns),
                'missing_values': int(df.isnull().sum().sum()),
                'duplicate_rows': int(df.duplicated().sum()),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            }
            
            # 获取数据样本用于LLM分析
            data_sample = df.head(10).to_string()
            
            return {
                'dataframe': df,
                'summary': data_summary,
                'sample': data_sample
            }
            
        except Exception as e:
            raise Exception(f"数据加载失败: {e}")
    
    def generate_analysis_plan(self, data_info: Dict[str, Any]) -> str:
        """生成分析计划并保存"""
        print("🧠 生成分析假设和计划...")
        
        # 使用增强版假设规划器
        plan_data = self.hypothesis_planner.create_analysis_plan(
            data_info['summary'], 
            data_info['sample']
        )
        
        # 保存计划到会话管理器
        plan_id = self.session_manager.create_plan_record(
            plan_data['datasource'],
            [h['description'] for h in plan_data['hypothesis_list']],
            plan_data['validation_steps']
        )
        
        print(f"✅ 分析计划生成完成，plan_id: {plan_id}")
        print(f"📊 生成了 {len(plan_data['hypothesis_list'])} 个假设")
        print(f"📋 规划了 {len(plan_data['validation_steps'])} 个验证步骤")
        
        return plan_id
    
    def execute_analysis_steps(self, plan_id: str, data_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析步骤"""
        print("⚙️ 开始执行分析步骤...")
        
        results = {
            'plan_id': plan_id,
            'data_summary': data_info['summary'],
            'analysis_results': {},
            'artifacts': []
        }
        
        df = data_info['dataframe']
        
        # 步骤1: 数据质量检查
        print("1️⃣ 执行数据质量检查...")
        quality_report = self._perform_data_quality_check(df)
        quality_artifact = self.session_manager.register_artifact(
            plan_id, 'quality_check', 'data_quality_report.json', 'json'
        )
        self._save_json_artifact(quality_artifact, quality_report)
        results['artifacts'].append(str(quality_artifact))
        results['analysis_results']['data_quality'] = quality_report
        
        # 步骤2: 描述性统计
        print("2️⃣ 生成描述性统计...")
        desc_stats = df.describe().to_dict()
        stats_artifact = self.session_manager.register_artifact(
            plan_id, 'descriptive_stats', 'descriptive_statistics.json', 'json'
        )
        self._save_json_artifact(stats_artifact, desc_stats)
        results['artifacts'].append(str(stats_artifact))
        results['analysis_results']['descriptive_stats'] = desc_stats
        
        # 步骤3: 相关性分析（如果有数值变量）
        if data_info['summary']['numeric_columns'] > 1:
            print("3️⃣ 计算变量相关性...")
            correlations = df.select_dtypes(include=['number']).corr().to_dict()
            corr_artifact = self.session_manager.register_artifact(
                plan_id, 'correlation', 'correlation_matrix.json', 'json'
            )
            self._save_json_artifact(corr_artifact, correlations)
            results['artifacts'].append(str(corr_artifact))
            results['analysis_results']['correlations'] = correlations
        
        # 步骤4: 生成可视化图表
        print("4️⃣ 生成可视化图表...")
        chart_paths = self._generate_visualizations(plan_id, df)
        results['artifacts'].extend(chart_paths)
        
        print("✅ 所有分析步骤执行完成")
        return results
    
    def _perform_data_quality_check(self, df: pd.DataFrame) -> Dict[str, Any]:
        """执行数据质量检查"""
        quality_report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_rows': int(df.duplicated().sum()),
            'data_types': df.dtypes.astype(str).to_dict(),
            'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
        }
        return quality_report
    
    def _generate_visualizations(self, plan_id: str, df: pd.DataFrame) -> List[str]:
        """生成基础可视化图表"""
        import matplotlib.pyplot as plt
        plt.style.use('seaborn-v0_8')
        
        chart_paths = []
        
        # 生成数值变量分布图
        numeric_cols = df.select_dtypes(include=['number']).columns[:4]  # 限制前4个
        if len(numeric_cols) > 0:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            axes = axes.flatten()
            
            for i, col in enumerate(numeric_cols):
                df[col].hist(bins=30, ax=axes[i], alpha=0.7)
                axes[i].set_title(f'{col} 分布')
                axes[i].set_xlabel(col)
                axes[i].set_ylabel('频次')
            
            # 隐藏多余的子图
            for i in range(len(numeric_cols), 4):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            chart_path = self.session_manager.register_artifact(
                plan_id, 'visualization', 'distribution_charts.png', 'image'
            )
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            chart_paths.append(str(chart_path))
        
        return chart_paths
    
    def _save_json_artifact(self, path: Path, data: Any):
        """保存JSON格式的产物"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    
    def generate_final_report(self, results: Dict[str, Any]) -> str:
        """生成最终分析报告"""
        print("📄 生成最终分析报告...")
        
        plan_id = results['plan_id']
        
        # 创建HTML报告
        html_content = self._generate_html_report(results)
        
        # 保存报告
        report_path = self.session_manager.register_artifact(
            plan_id, 'report', 'analysis_report.html', 'report'
        )
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ 报告生成完成: {report_path}")
        return str(report_path)
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """生成HTML格式报告"""
        data_summary = results['data_summary']
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据分析报告 - {data_summary['data_source']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; background: #ecf0f1; }}
        .stats-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .stats-table th, .stats-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .stats-table th {{ background-color: #3498db; color: white; }}
        .highlight {{ background-color: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 数据分析报告</h1>
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>数据源:</strong> {data_summary['data_source']}</p>
        
        <div class="section">
            <h2>📋 数据概览</h2>
            <table class="stats-table">
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>总行数</td><td>{data_summary['rows']:,}</td></tr>
                <tr><td>总列数</td><td>{data_summary['columns']}</td></tr>
                <tr><td>数值变量</td><td>{data_summary['numeric_columns']}</td></tr>
                <tr><td>分类变量</td><td>{data_summary['categorical_columns']}</td></tr>
                <tr><td>缺失值</td><td>{data_summary['missing_values']:,}</td></tr>
                <tr><td>重复行</td><td>{data_summary['duplicate_rows']:,}</td></tr>
                <tr><td>内存占用</td><td>{data_summary['memory_usage']}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>✅ 分析结果</h2>
            <div class="highlight">
                <p>本次分析已完成数据质量检查、描述性统计、相关性分析和可视化图表生成。</p>
                <p>所有分析产物已按照OpenSpec规范保存到相应的会话目录中。</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📁 产物清单</h2>
            <ul>
        """
        
        for artifact in results['artifacts']:
            html_content += f"<li>{artifact}</li>\n"
        
        html_content += """
            </ul>
        </div>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def run_complete_analysis(self, data_file: str) -> Dict[str, Any]:
        """运行完整的分析流程"""
        print("🚀 启动完整的AI驱动数据分析流程")
        print("=" * 50)
        
        try:
            # 步骤1: 加载和分析数据
            data_info = self.load_and_analyze_data(data_file)
            
            # 步骤2: 生成分析计划
            plan_id = self.generate_analysis_plan(data_info)
            
            # 步骤3: 执行分析步骤
            analysis_results = self.execute_analysis_steps(plan_id, data_info)
            
            # 步骤4: 生成最终报告
            report_path = self.generate_final_report(analysis_results)
            analysis_results['final_report'] = report_path
            
            print("=" * 50)
            print("🎉 完整分析流程执行成功!")
            print(f"📋 Plan ID: {plan_id}")
            print(f"📄 最终报告: {report_path}")
            print(f"📁 产物数量: {len(analysis_results['artifacts'])}")
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ 分析流程执行失败: {e}")
            raise

# 使用示例
if __name__ == "__main__":
    # 创建分析流水线
    pipeline = AnalysisPipeline()
    
    # 对血清数据进行完整分析
    data_file = "data/examples/serum/Normal_EP_serum_data.xlsx"
    results = pipeline.run_complete_analysis(data_file)
    
    print("\n分析完成!")