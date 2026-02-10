#!/usr/bin/env python3
"""
DeepAnalyze 配置检查和修改工具
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import requests

console = Console()

def check_llm_config():
    """检查LLM配置状态"""
    console.print(Panel("[bold cyan]🔍 LLM配置检查[/bold cyan]", border_style="cyan"))
    
    # 导入配置
    try:
        from src.api.config import DEEPANALYZE_VLLM_API_KEY, VLLM_BASE_URL, MODEL_PATH
    except ImportError as e:
        console.print(f"[red]❌ 配置导入失败: {e}[/red]")
        return False
    
    # 显示配置信息
    console.print(f"[green]✓[/green] API密钥: {DEEPANALYZE_VLLM_API_KEY[:15]}..." if DEEPANALYZE_VLLM_API_KEY else "[red]✗ 未设置API密钥[/red]")
    console.print(f"[green]✓[/green] Base URL: {VLLM_BASE_URL}")
    console.print(f"[green]✓[/green] 模型路径: {MODEL_PATH}")
    
    # 测试连接
    if DEEPANALYZE_VLLM_API_KEY and VLLM_BASE_URL:
        try:
            headers = {
                'Authorization': f'Bearer {DEEPANALYZE_VLLM_API_KEY}',
                'Content-Type': 'application/json'
            }
            response = requests.get(f'{VLLM_BASE_URL}/models', headers=headers, timeout=10)
            if response.status_code == 200:
                console.print("[green]✓ LLM API连接成功[/green]")
                models = response.json()
                available_models = [m.get("id") for m in models.get("data", [])[:5]]
                console.print(f"[dim]可用模型: {', '.join(available_models)}[/dim]")
                return True
            else:
                console.print(f"[red]✗ LLM API连接失败: {response.status_code}[/red]")
                console.print(f"[dim]响应: {response.text[:100]}[/dim]")
                return False
        except Exception as e:
            console.print(f"[red]✗ 连接测试异常: {e}[/red]")
            return False
    else:
        console.print("[yellow]⚠️  LLM配置不完整[/yellow]")
        return False

def check_ai_orchestration_config():
    """检查AI编排配置"""
    console.print(Panel("[bold blue]⚙️  AI编排配置检查[/bold blue]", border_style="blue"))
    
    try:
        from src.api.config import USE_ORCHESTRATOR, MAX_RECURSION_DEPTH
    except ImportError as e:
        console.print(f"[red]❌ 配置导入失败: {e}[/red]")
        return
    
    status = "启用" if USE_ORCHESTRATOR else "禁用"
    status_color = "green" if USE_ORCHESTRATOR else "yellow"
    console.print(f"[{status_color}]✓[/] 编排系统: {status}")
    console.print(f"[green]✓[/] 最大递归深度: {MAX_RECURSION_DEPTH}")
    
    if USE_ORCHESTRATOR:
        console.print("[green]✓ 完整AI分析流程已启用[/green]")
        console.print("[dim]系统将自动执行假设生成→自主编程→执行分析→迭代优化的完整流程[/dim]")
    else:
        console.print("[yellow]⚠️  完整AI分析流程已禁用[/yellow]")
        console.print("[dim]系统处于交互式模式，需要用户手动触发各分析环节[/dim]")

def show_current_config():
    """显示当前关键配置"""
    console.print(Panel("[bold purple]📋 当前配置概览[/bold purple]", border_style="purple"))
    
    config_items = [
        ("DEEPANALYZE_USE_ORCHESTRATOR", "AI编排开关"),
        ("DEEPANALYZE_MAX_DEPTH", "最大递归深度"),
        ("DEEPANALYZE_MODEL_PATH", "模型路径"),
        ("DEEPANALYZE_REPORT_FORMAT", "报告格式"),
        ("DEEPANALYZE_VISUAL_STYLE", "可视化风格"),
        ("DEEPANALYZE_CODEGEN_CONCURRENCY", "代码生成并发"),
        ("DEEPANALYZE_EXECUTION_CONCURRENCY", "执行并发数"),
    ]
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("配置项", style="cyan")
    table.add_column("当前值", style="green")
    table.add_column("说明", style="dim")
    
    for env_var, description in config_items:
        value = os.getenv(env_var, "未设置")
        table.add_row(env_var, value, description)
    
    console.print(table)

def modify_config():
    """交互式修改配置"""
    console.print(Panel("[bold orange]🔧 配置修改向导[/bold orange]", border_style="orange"))
    
    env_file = project_root / ".env"
    if not env_file.exists():
        console.print("[red]❌ .env文件不存在[/red]")
        return
    
    # 读取现有配置
    config_lines = env_file.read_text(encoding='utf-8').splitlines()
    config_dict = {}
    
    for line in config_lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            config_dict[key.strip()] = value.strip()
    
    # 提供修改选项
    options = [
        ("1", "启用完整AI分析流程", "DEEPANALYZE_USE_ORCHESTRATOR=1"),
        ("2", "禁用完整AI分析流程", "DEEPANALYZE_USE_ORCHESTRATOR=0"),
        ("3", "设置最大递归深度为3", "DEEPANALYZE_MAX_DEPTH=3"),
        ("4", "设置最大递归深度为1", "DEEPANALYZE_MAX_DEPTH=1"),
        ("5", "启用调试模式", "DEEPANALYZE_DEBUG_STREAM=1"),
        ("6", "禁用调试模式", "DEEPANALYZE_DEBUG_STREAM=0"),
        ("7", "自定义配置项", "CUSTOM"),
        ("0", "退出", "EXIT")
    ]
    
    while True:
        console.print("\n[bold]请选择要修改的配置:[/bold]")
        for option, desc, _ in options:
            console.print(f"[yellow]{option}[/yellow] - {desc}")
        
        choice = input("\n请输入选项编号: ").strip()
        
        if choice == "0":
            break
        elif choice == "7":
            # 自定义配置
            key = input("请输入配置项名称: ").strip()
            value = input("请输入配置项值: ").strip()
            if key and value:
                config_dict[key] = value
                console.print(f"[green]✓ 已设置 {key}={value}[/green]")
        else:
            # 预设选项
            selected_option = next((opt for opt in options if opt[0] == choice), None)
            if selected_option:
                key, value = selected_option[2].split('=')
                config_dict[key] = value
                console.print(f"[green]✓ {selected_option[1]}[/green]")
            else:
                console.print("[red]无效选项[/red]")
                continue
        
        # 询问是否保存
        save = input("\n是否保存更改到 .env 文件? (y/n): ").strip().lower()
        if save == 'y':
            # 重新构建配置文件
            new_lines = []
            for line in config_lines:
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                    key = line_stripped.split('=', 1)[0].strip()
                    if key in config_dict:
                        new_lines.append(f"{key}={config_dict[key]}")
                        del config_dict[key]
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # 添加剩余的新配置项
            for key, value in config_dict.items():
                new_lines.append(f"{key}={value}")
            
            # 写入文件
            env_file.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
            console.print("[green]✓ 配置已保存到 .env 文件[/green]")
            
            # 询问是否重启服务
            restart = input("是否重启服务使配置生效? (y/n): ").strip().lower()
            if restart == 'y':
                console.print("[yellow]正在重启服务...[/yellow]")
                os.system("./scripts/restart_services.sh")
            break

def main():
    """主函数"""
    console.print(Panel("[bold]DeepAnalyze 配置管理工具[/bold]", border_style="blue"))
    
    # 检查LLM配置
    llm_ok = check_llm_config()
    
    # 检查AI编排配置
    check_ai_orchestration_config()
    
    # 显示当前配置
    show_current_config()
    
    if not llm_ok:
        console.print("\n[red]⚠️  LLM配置存在问题，请检查src/api密钥和网络连接[/red]")
    
    # 询问是否修改配置
    modify = input("\n是否要修改配置? (y/n): ").strip().lower()
    if modify == 'y':
        modify_config()
    
    console.print("\n[green]✅ 配置检查完成[/green]")

if __name__ == "__main__":
    main()
