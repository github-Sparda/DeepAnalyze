#!/usr/bin/env python3
"""
DeepAnalyze AI自主分析CLI
实现完整的AI驱动数据分析流程：
假设生成 → 自主编程 → 执行分析 → 结果分析 → 迭代优化 → 分项结论 → 最终报告
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from orchestration.graph import build_graph
from orchestration.state import OrchestrationState
from state.manager import StateManager, create_new_session
from orchestration.llm import LLMClient
from error.handler import ErrorHandler

class AIAutonomousAnalyzerCLI:
    """AI自主分析CLI工具"""
    
    def __init__(self):
        self.parser = self._create_parser()
        self.state_manager = StateManager()
        self.error_handler = ErrorHandler()
        
    def _create_parser(self):
        """创建命令行参数解析器"""
        parser = argparse.ArgumentParser(
            description="DeepAnalyze AI自主分析CLI - 完整的AI驱动数据分析流程",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
AI自主分析流程:
  1. 假设生成 - AI基于数据提出可验证假设
  2. 自主编程 - AI生成分析代码
  3. 执行分析 - 安全执行生成的代码
  4. 结果分析 - AI分析执行结果
  5. 迭代优化 - 必要时调整假设和方法
  6. 分项结论 - 生成各部分分析结论
  7. 最终报告 - 整合所有发现生成完整报告

使用示例:
  %(prog)s --data-file data.csv --analysis-goal "分析销售趋势"
  %(prog)s --data-file data.csv --interactive
  %(prog)s --session-id existing_session_123 --continue
            """
        )
        
        # 主要功能参数
        parser.add_argument('--data-file', help='数据文件路径')
        parser.add_argument('--analysis-goal', help='分析目标/问题')
        parser.add_argument('--max-depth', type=int, default=3, help='最大递归深度')
        parser.add_argument('--language', choices=['zh', 'en'], default='zh', help='报告语言')
        
        # 运行模式
        parser.add_argument('--interactive', '-i', action='store_true', help='交互式模式')
        parser.add_argument('--session-id', help='继续现有会话')
        parser.add_argument('--continue', action='store_true', dest='continue_session', help='继续会话')
        
        # 输出控制
        parser.add_argument('--output-dir', help='输出目录')
        parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
        parser.add_argument('--no-visualization', action='store_true', help='跳过可视化生成')
        
        return parser
    
    def run_autonomous_analysis(self, args):
        """运行AI自主分析流程"""
        print("🚀 启动DeepAnalyze AI自主分析")
        print("=" * 50)
        
        # 创建或恢复会话
        if args.session_id and args.continue_session:
            session_id = args.session_id
            print(f"🔄 继续会话: {session_id}")
        else:
            session_name = f"AI分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session_id = create_new_session(
                session_name=session_name,
                tags=["ai_autonomous", "full_process"]
            )
            print(f"🆕 创建新会话: {session_id}")
        
        # 准备初始状态
        initial_state: OrchestrationState = {
            "session_id": session_id,
            "run_id": f"run_{int(datetime.now().timestamp())}",
            "data_sessions_active_dir": str(self.state_manager._get_session_path(session_id)),
            "input_files": [args.data_file] if args.data_file else [],
            "config": {
                "report_language": args.language,
                "max_depth": args.max_depth,
                "analysis_goal": args.analysis_goal or "探索数据中的模式和洞察",
                "generate_visualizations": not args.no_visualization
            }
        }
        
        # 如果有数据文件，添加到状态
        if args.data_file:
            data_path = Path(args.data_file).resolve()
            if not data_path.exists():
                print(f"❌ 数据文件不存在: {data_path}")
                return False
            initial_state["input_files"] = [str(data_path)]
            print(f"📂 分析文件: {data_path.name}")
        
        if args.analysis_goal:
            print(f"🎯 分析目标: {args.analysis_goal}")
        
        print(f"🧠 最大递归深度: {args.max_depth}")
        print(f"🌐 报告语言: {'中文' if args.language == 'zh' else 'English'}")
        print("")
        
        try:
            # 构建分析图
            print("🏗️  构建分析流程图...")
            graph = build_graph(LLMClient(), {})
            
            # 执行分析流程
            print("⚡ 开始AI自主分析流程...")
            print("-" * 30)
            
            final_state = graph.invoke(initial_state)
            
            # 显示结果
            self._display_results(final_state, args)
            
            # 保存会话
            self.state_manager.update_session_state(session_id, final_state)
            
            print("\n✅ AI自主分析完成!")
            print(f"📁 会话ID: {session_id}")
            print(f"📂 工作目录: {initial_state['data_sessions_active_dir']}")
            
            return True
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity="high",
                category="execution",
                context={"session_id": session_id}
            )
            print(f"\n❌ 分析过程中出现错误: {error_info}")
            return False
    
    def _display_results(self, state: OrchestrationState, args):
        """显示分析结果"""
        print("\n📊 分析结果摘要")
        print("=" * 30)
        
        # 基本信息
        print(f"会话ID: {state.get('session_id', 'N/A')}")
        print(f"运行ID: {state.get('run_id', 'N/A')}")
        
        # 假设信息
        hypotheses = state.get('hypotheses', [])
        if hypotheses:
            print(f"\n💭 生成假设 ({len(hypotheses)}个):")
            for i, hypo in enumerate(hypotheses[:5], 1):
                print(f"  {i}. {hypo}")
            if len(hypotheses) > 5:
                print(f"  ... 还有 {len(hypotheses) - 5} 个假设")
        
        # 分析结果
        analysis_result = state.get('analysis_results', '')
        if analysis_result:
            print(f"\n🔍 主要发现:")
            # 提取关键发现（简化处理）
            lines = analysis_result.split('\n')
            for line in lines[:10]:
                if line.strip() and not line.startswith('#'):
                    print(f"  {line.strip()}")
            if len(lines) > 10:
                print("  ... (更多内容请查看完整报告)")
        
        # 工件信息
        artifacts = state.get('artifacts', [])
        if artifacts:
            print(f"\n📎 生成工件 ({len(artifacts)}个):")
            for artifact in artifacts[:10]:
                print(f"  - {artifact.get('name', 'Unknown')}")
        
        # 可视化
        visualizations = state.get('visualizations', [])
        if visualizations:
            print(f"\n🎨 生成可视化 ({len(visualizations)}个):")
            for viz in visualizations:
                print(f"  - {viz.get('name', 'Unknown')}")
        
        # 报告
        report = state.get('report', '')
        if report:
            print(f"\n📄 报告生成: 完成")
            print(f"  字数: {len(report)} 字符")
        
        # 错误信息
        errors = state.get('errors', [])
        if errors:
            print(f"\n⚠️  警告/错误 ({len(errors)}个):")
            for error in errors[:3]:
                print(f"  - {error}")
    
    def interactive_mode(self, args):
        """交互式模式"""
        print("🎮 进入交互式AI分析模式")
        print("=" * 40)
        print("支持的命令:")
        print("  analyze <file> [goal]  - 分析指定文件")
        print("  session info          - 查看当前会话信息")
        print("  session list          - 列出所有会话")
        print("  continue <session_id> - 继续指定会话")
        print("  help                  - 显示帮助")
        print("  quit                  - 退出")
        print("")
        
        current_session = None
        
        while True:
            try:
                command = input("_src/core> ").strip()
                if not command:
                    continue
                
                if command.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break
                
                if command.lower() == 'help':
                    print("支持的命令:")
                    print("  analyze data.csv \"分析目标\"")
                    print("  session info")
                    print("  session list")
                    print("  continue session_123")
                    print("  help")
                    print("  quit")
                    continue
                
                if command.startswith('analyze '):
                    parts = command.split(' ', 2)
                    if len(parts) >= 2:
                        data_file = parts[1]
                        goal = parts[2] if len(parts) > 2 else None
                        
                        # 更新参数并运行分析
                        args.data_file = data_file
                        args.analysis_goal = goal
                        if self.run_autonomous_analysis(args):
                            print("✅ 分析完成!")
                        else:
                            print("❌ 分析失败!")
                    else:
                        print("用法: analyze <文件路径> [分析目标]")
                
                elif command == 'session info':
                    if current_session:
                        state = self.state_manager.get_session_state(current_session)
                        if state:
                            self._display_results(state, args)
                        else:
                            print("❌ 无法获取会话信息")
                    else:
                        print("ℹ️  当前没有活跃会话")
                
                elif command == 'session list':
                    sessions = self.state_manager.list_sessions()
                    if sessions:
                        print("📋 会话列表:")
                        for session in sessions[:10]:  # 显示最近10个
                            print(f"  - {session['session_id']}: {session.get('session_name', 'Unnamed')}")
                    else:
                        print("📭 没有找到会话")
                
                elif command.startswith('continue '):
                    session_id = command.split(' ', 1)[1]
                    args.session_id = session_id
                    args.continue_session = True
                    if self.run_autonomous_analysis(args):
                        current_session = session_id
                        print(f"✅ 继续会话: {session_id}")
                    else:
                        print("❌ 继续会话失败!")
                
                else:
                    print(f"❓ 未知命令: {command}")
                    print("输入 'help' 查看可用命令")
                    
            except KeyboardInterrupt:
                print("\n\n👋 收到中断信号，再见!")
                break
            except Exception as e:
                print(f"❌ 命令执行错误: {e}")
    
    def run(self):
        """运行CLI工具"""
        args = self.parser.parse_args()
        
        if args.interactive:
            self.interactive_mode(args)
        elif args.data_file or (args.session_id and args.continue_session):
            success = self.run_autonomous_analysis(args)
            sys.exit(0 if success else 1)
        else:
            self.parser.print_help()
            print("\n💡 提示:")
            print("  使用 --interactive 进入交互模式")
            print("  或者提供 --data-file 进行批处理分析")

def main():
    """主函数"""
    cli = AIAutonomousAnalyzerCLI()
    cli.run()

if __name__ == "__main__":
    main()
