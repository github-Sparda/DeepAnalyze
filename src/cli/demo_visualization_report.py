#!/usr/bin/env python3
"""
DeepAnalyze CLI 演示脚本 - 展示带可视化的报告生成功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
import time

console = Console()

def demonstrate_visualization_reporting():
    """演示带可视化的报告生成功能"""
    
    console.print(Panel("[bold cyan]📊 DeepAnalyze 可视化报告演示[/bold cyan]", 
                       title="功能演示", border_style="cyan"))
    
    # 模拟数据分析结果
    sample_analysis_results = {
        "data_summary": {
            "总样本数": 1000,
            "平均值": 1025.3,
            "标准差": 198.7,
            "最小值": 567.2,
            "最大值": 1892.4,
            "缺失值": 0
        },
        "key_metrics": {
            "增长率": "12.5%",
            "置信区间": "[987.3, 1063.3]",
            "显著性水平": "p < 0.05"
        },
        "insights": [
            "销售额呈现稳定上升趋势",
            "不同地区间存在显著差异",
            "季节性波动特征明显",
            "客户满意度与复购率正相关"
        ]
    }
    
    # 创建临时数据文件用于演示
    demo_data_path = "/tmp/demo_sales_data.csv"
    
    import pandas as pd
    import numpy as np
    
    # 生成演示数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    regions = ['North', 'South', 'East', 'West']
    
    demo_data = pd.DataFrame({
        'date': dates,
        'sales': np.random.normal(1000, 200, 100),
        'profit': np.random.normal(150, 50, 100),
        'region': np.random.choice(regions, 100),
        'customer_satisfaction': np.random.uniform(3.5, 5.0, 100)
    })
    
    demo_data.to_csv(demo_data_path, index=False)
    console.print(f"[green]✅ 已创建演示数据文件: {demo_data_path}[/green]")
    
    # 演示不同的报告生成选项
    demo_scenarios = [
        {
            "name": "基础报告（无可视化）",
            "command": f"python direct_cli.py --analyze {demo_data_path} --report --no-visualizations",
            "description": "生成纯文本分析报告，不含图表"
        },
        {
            "name": "增强报告（含可视化）",
            "command": f"python direct_cli.py --analyze {demo_data_path} --visualize --report --include-visualizations",
            "description": "生成包含图表的完整分析报告"
        },
        {
            "name": "交互模式演示",
            "command": "python direct_cli.py --interactive",
            "description": "进入交互模式，手动控制分析流程"
        }
    ]
    
    console.print("\n[bold]🎯 演示场景:[/bold]")
    for i, scenario in enumerate(demo_scenarios, 1):
        console.print(f"\n{i}. [cyan]{scenario['name']}[/cyan]")
        console.print(f"   [dim]{scenario['description']}[/dim]")
        console.print(f"   [yellow]命令: {scenario['command']}[/yellow]")
    
    # 实际执行演示
    console.print("\n[bold green]🚀 开始执行演示...[/bold green]")
    
    try:
        # 导入CLI类
        from direct_cli import DirectDeepAnalyzeCLI
        
        # 创建CLI实例
        cli = DirectDeepAnalyzeCLI()
        
        console.print("[cyan]1. 分析演示数据...[/cyan]")
        analysis_result = cli.analyze_data_direct(demo_data_path, ["descriptive"])
        
        if analysis_result:
            console.print("[green]✅ 数据分析完成[/green]")
            
            console.print("[cyan]2. 生成可视化图表...[/cyan]")
            viz_result = cli.generate_visualization_direct(analysis_result, "auto")
            if viz_result:
                console.print("[green]✅ 可视化图表生成完成[/green]")
            
            console.print("[cyan]3. 生成带可视化的增强报告...[/cyan]")
            report_result = cli.generate_report_direct(
                analysis_result,
                "analytical", 
                include_visualizations=True
            )
            
            if report_result:
                console.print(f"[green]✅ 增强报告生成成功: {report_result}[/green]")
                
                # 显示报告内容预览
                try:
                    with open(report_result, 'r', encoding='utf-8') as f:
                        content = f.read()
                        preview_lines = content.split('\n')[:20]
                        console.print("\n[bold]📋 报告内容预览:[/bold]")
                        for line in preview_lines:
                            console.print(f"[dim]{line}[/dim]")
                        if len(content.split('\n')) > 20:
                            console.print("[dim]... (内容截断)[/dim]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ 无法读取报告内容: {e}[/yellow]")
            else:
                console.print("[red]❌ 报告生成失败[/red]")
        else:
            console.print("[red]❌ 数据分析失败[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ 演示执行出错: {e}[/red]")
        console.print("[yellow]提示: 请确保在 src/cli 目录下运行此脚本[/yellow]")
    
    # 总结
    console.print("\n" + "="*60)
    console.print("[bold green]✨ 演示总结[/bold green]")
    console.print("""
[bold]新增功能特性:[/bold]
• 📊 报告中自动嵌入相关可视化图表
• 🎨 支持多种图表类型（分布图、趋势图、对比图等）
• 📝 自动生成分析方法和结论部分
• ⚙️  可灵活控制是否包含可视化内容
• 🖼️  图表路径直接嵌入报告内容

[bold]使用方式:[/bold]
1. 命令行模式: 添加 --include-visualizations 参数
2. 交互模式: 使用 'report analytical --no-viz' 命令
3. 批量处理: 在脚本中调用增强的 generate_report_direct 方法

[bold]技术实现:[/bold]
• 修改了 generate_report_direct 方法，添加可视化支持
• 新增 _prepare_enhanced_report_content 和 _embed_visualizations_in_report 方法
• 扩展了命令行参数和交互命令支持
• 完善了会话状态管理，跟踪可视化文件
    """)

if __name__ == "__main__":
    demonstrate_visualization_reporting()
