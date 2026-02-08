#!/usr/bin/env python3
"""
DeepAnalyze Direct CLI - Direct Module Access Command Line Interface
直接调用各个模块功能的命令行工具
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
import importlib

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

console = Console()

class DeepAnalyzeDirectCLI:
    """直接调用模块功能的CLI"""
    
    def __init__(self):
        self.modules = {}
        self.current_session = None
        
    def load_modules(self):
        """加载核心模块"""
        try:
            # 数据分析模块
            from deepanalyze.analytics.advanced_analyzer import analyze_dataset, AnalysisType
            self.modules['analytics'] = {
                'analyze_dataset': analyze_dataset,
                'AnalysisType': AnalysisType
            }
            
            # 状态管理模块
            from deepanalyze.state.manager import create_new_session, get_session_state, update_session_state
            self.modules['state'] = {
                'create_new_session': create_new_session,
                'get_session_state': get_session_state,
                'update_session_state': update_session_state
            }
            
            # 报告生成模块
            from deepanalyze.reporting.manager import ReportManager, ReportType
            self.modules['reporting'] = {
                'ReportManager': ReportManager,
                'ReportType': ReportType
            }
            
            # AI助手模块
            from deepanalyze.assistant.engine import AIAssistantEngine
            self.modules['assistant'] = {
                'AIAssistantEngine': AIAssistantEngine
            }
            
            # 可视化模块
            from deepanalyze.visualization import plotter
            self.modules['visualization'] = {
                'plotter': plotter
            }
            
            console.print("[green]✅ 所有模块加载成功[/green]")
            return True
            
        except ImportError as e:
            console.print(f"[red]❌ 模块加载失败: {e}[/red]")
            return False
    
    def create_session(self, session_name: str = None) -> str:
        """创建新会话"""
        if 'state' not in self.modules:
            console.print("[red]❌ 状态管理模块未加载[/red]")
            return None
            
        session_name = session_name or f"cli_session_{int(time.time())}"
        session_id = self.modules['state']['create_new_session'](session_name=session_name)
        self.current_session = session_id
        console.print(f"[green]✅ 会话创建成功: {session_id}[/green]")
        return session_id
    
    def analyze_data(self, file_path: str, analysis_types: List[str] = None):
        """直接数据分析"""
        if 'analytics' not in self.modules:
            console.print("[red]❌ 数据分析模块未加载[/red]")
            return None
            
        if not self.current_session:
            session_id = self.create_session("数据分析会话")
        else:
            session_id = self.current_session
            
        # 转换分析类型
        if analysis_types:
            analysis_enum_types = []
            type_mapping = {
                'descriptive': self.modules['analytics']['AnalysisType'].DESCRIPTIVE,
                'inferential': self.modules['analytics']['AnalysisType'].INFERENTIAL,
                'predictive': self.modules['analytics']['AnalysisType'].PREDICTIVE,
                'diagnostic': self.modules['analytics']['AnalysisType'].DIAGNOSTIC,
                'prescriptive': self.modules['analytics']['AnalysisType'].PRESCRIPTIVE
            }
            
            for atype in analysis_types:
                if atype.lower() in type_mapping:
                    analysis_enum_types.append(type_mapping[atype.lower()])
        else:
            analysis_enum_types = None
            
        console.print(f"[cyan]🔍 开始分析文件: {file_path}[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="正在分析数据...", total=None)
            result = self.modules['analytics']['analyze_dataset'](
                file_path=file_path,
                session_id=session_id,
                analysis_types=analysis_enum_types
            )
        
        if result and "error" not in result:
            console.print("[green]✅ 数据分析完成[/green]")
            
            # 显示结果摘要
            if "data_summary" in result:
                summary = result["data_summary"]
                table = Table(title="数据摘要")
                table.add_column("指标", style="cyan")
                table.add_column("值", style="magenta")
                
                for key, value in summary.items():
                    table.add_row(key, str(value))
                
                console.print(table)
                
            if "insights" in result and result["insights"]:
                console.print("\n[bold]💡 主要洞察:[/bold]")
                for i, insight in enumerate(result["insights"][:5], 1):
                    console.print(f"  {i}. {insight}")
                    
        else:
            error_msg = result.get("error", "未知错误") if result else "分析失败"
            console.print(f"[red]❌ 数据分析失败: {error_msg}[/red]")
            
        return result
    
    def generate_report(self, title: str, content: str):
        """生成报告"""
        if 'reporting' not in self.modules:
            console.print("[red]❌ 报告模块未加载[/red]")
            return None
            
        if not self.current_session:
            session_id = self.create_session("报告生成会话")
        else:
            session_id = self.current_session
            
        report_manager = self.modules['reporting']['ReportManager']()
        
        console.print(f"[cyan]📄 生成报告: {title}[/cyan]")
        
        report = report_manager.create_report(
            session_id=session_id,
            title=title,
            content=content,
            report_type=self.modules['reporting']['ReportType'].ANALYTICAL,
            metadata={"author": "CLI用户"}
        )
        
        if report:
            console.print(f"[green]✅ 报告生成成功: {report.report_id}[/green]")
            return report
        else:
            console.print("[red]❌ 报告生成失败[/red]")
            return None
    
    def chat_with_assistant(self, message: str):
        """与AI助手对话"""
        if 'assistant' not in self.modules:
            console.print("[red]❌ AI助手模块未加载[/red]")
            return None
            
        if not self.current_session:
            session_id = self.create_session("AI助手会话")
        else:
            session_id = self.current_session
            
        assistant = self.modules['assistant']['AIAssistantEngine']()
        
        console.print(f"[cyan]🤖 AI助手处理中...[/cyan]")
        
        response = assistant.process_message(session_id, message)
        
        if response and response.get('response'):
            console.print("[green]✅ AI助手响应:[/green]")
            console.print(Panel(response['response'], title="AI助手回复"))
            return response
        else:
            console.print("[red]❌ AI助手响应失败[/red]")
            return None
    
    def visualize_data(self, file_path: str, chart_types: List[str] = None):
        """数据可视化"""
        if 'visualization' not in self.modules:
            console.print("[red]❌ 可视化模块未加载[/red]")
            return None
            
        if not self.current_session:
            session_id = self.create_session("可视化会话")
        else:
            session_id = self.current_session
            
        # 使用 plotter 模块的函数
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            
            console.print(f"[cyan]🎨 生成可视化图表: {file_path}[/cyan]")
            
            # 显示数值列供选择
            numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
            console.print(f"[dim]数值列: {', '.join(numeric_columns)}[/dim]")
            
            # 生成分布图示例
            if numeric_columns:
                output_path = f"/tmp/visualization_{int(time.time())}.png"
                result_path = self.modules['visualization']['plotter'].render_distribution(
                    df, numeric_columns[0], output_path, style="academic"
                )
                console.print(f"[green]✅ 分布图已生成: {result_path}[/green]")
                
            console.print("[green]✅ 可视化功能执行完成[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 可视化失败: {e}[/red]")
            return None
    
    def show_modules(self):
        """显示可用模块"""
        table = Table(title="可用模块")
        table.add_column("模块", style="cyan")
        table.add_column("功能", style="magenta")
        table.add_column("状态", style="green")
        
        module_info = {
            'analytics': '数据分析、统计分析',
            'state': '会话管理、状态跟踪',
            'reporting': '报告生成、文档导出',
            'assistant': 'AI助手、自然语言处理',
            'visualization': '数据可视化、图表生成'
        }
        
        for module_name, description in module_info.items():
            status = "[green]✓ 加载[/green]" if module_name in self.modules else "[red]✗ 未加载[/red]"
            table.add_row(module_name, description, status)
            
        console.print(table)
    
    def interactive_mode(self):
        """交互模式"""
        console.print(Panel.fit("[bold green]DeepAnalyze 直接CLI[/bold green]\n直接调用模块功能的命令行工具", 
                               border_style="blue"))
        
        self.show_modules()
        
        if not self.current_session:
            self.create_session("交互会话")
        
        while True:
            try:
                command = Prompt.ask("\n[bold cyan]>>>[/bold cyan]", default="")
                
                if command.lower() in ['quit', 'exit', '退出']:
                    console.print("[green]👋 再见![/green]")
                    break
                    
                elif command.lower() in ['help', '帮助']:
                    self.show_help()
                    
                elif command.lower() in ['modules', '模块']:
                    self.show_modules()
                    
                elif command.lower() in ['session', '会话']:
                    console.print(f"[cyan]当前会话: {self.current_session or '无'}[/cyan]")
                    
                elif command.startswith('analyze '):
                    file_path = command[8:].strip()
                    if file_path:
                        self.analyze_data(file_path)
                        
                elif command.startswith('report '):
                    parts = command[7:].split(' ', 1)
                    if len(parts) == 2:
                        title, content = parts
                        self.generate_report(title, content)
                        
                elif command.startswith('chat '):
                    message = command[5:].strip()
                    if message:
                        self.chat_with_assistant(message)
                        
                elif command.startswith('visualize '):
                    file_path = command[10:].strip()
                    if file_path:
                        self.visualize_data(file_path)
                        
                elif command:
                    console.print("[yellow]❓ 未知命令，输入 'help' 查看帮助[/yellow]")
                    
            except KeyboardInterrupt:
                console.print("\n[green]👋 再见![/green]")
                break
            except Exception as e:
                console.print(f"[red]❌ 错误: {e}[/red]")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
[bold cyan]📋 可用命令:[/bold cyan]

[basic commands]
• [yellow]help[/yellow] - 显示此帮助信息
• [yellow]quit/exit[/yellow] - 退出程序
• [yellow]modules[/yellow] - 显示可用模块
• [yellow]session[/yellow] - 显示当前会话

[data analysis]
• [yellow]analyze <file_path>[/yellow] - 分析数据文件
• [yellow]visualize <file_path>[/yellow] - 生成可视化图表

[ai assistant]
• [yellow]chat <message>[/yellow] - 与AI助手对话

[reporting]
• [yellow]report <title> <content>[/yellow] - 生成报告

[dim]示例:
  analyze data/sales.csv
  chat "分析这份销售数据的主要趋势"
  report "销售分析报告" "这是报告内容"
  visualize data/chart_data.csv[/dim]
"""
        console.print(help_text)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DeepAnalyze Direct CLI")
    parser.add_argument('--file', '-f', help='要分析的数据文件')
    parser.add_argument('--analyze', '-a', action='store_true', help='执行数据分析')
    parser.add_argument('--types', '-t', nargs='+', help='分析类型 (descriptive, inferential, predictive)')
    parser.add_argument('--chat', '-c', help='与AI助手对话')
    parser.add_argument('--report-title', help='报告标题')
    parser.add_argument('--report-content', help='报告内容')
    parser.add_argument('--visualize', '-v', help='生成可视化图表')
    parser.add_argument('--interactive', '-i', action='store_true', help='进入交互模式')
    
    args = parser.parse_args()
    
    cli = DeepAnalyzeDirectCLI()
    
    # 加载模块
    if not cli.load_modules():
        console.print("[red]❌ 无法加载必要模块，退出程序[/red]")
        return 1
    
    # 根据参数执行相应操作
    if args.interactive or not any([args.file, args.chat, args.report_title, args.visualize]):
        # 进入交互模式
        cli.interactive_mode()
        
    else:
        # 批量执行命令
        session_id = cli.create_session("批处理会话")
        
        if args.file and args.analyze:
            cli.analyze_data(args.file, args.types)
            
        if args.chat:
            cli.chat_with_assistant(args.chat)
            
        if args.report_title and args.report_content:
            cli.generate_report(args.report_title, args.report_content)
            
        if args.visualize:
            cli.visualize_data(args.visualize)
    
    return 0


if __name__ == "__main__":
    import time
    sys.exit(main())