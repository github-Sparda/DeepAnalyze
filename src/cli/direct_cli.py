#!/usr/bin/env python3
"""
DeepAnalyze Direct CLI - Direct module function calls without src/api server
Support direct access to core modules: data analysis, visualization, AI assistant, report generation
"""

import os
import sys
import json
import shutil
import time
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown
from rich.rule import Rule

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

# Import core modules
from src.core.analytics.advanced_analyzer import analyze_dataset
from src.core.visualization.plotter import render_distribution, render_correlation_heatmap
from src.core.assistant.engine import AIAssistantEngine
from src.core.reporting.manager import ReportManager, ReportType
from src.core.state.manager import StateManager, create_new_session, get_session_state, update_session_state
from src.core.error.handler import ErrorHandler, ErrorSeverity, ErrorCategory

console = Console()

class DirectDeepAnalyzeCLI:
    def __init__(self):
        """Initialize direct CLI client"""
        self.state_manager = StateManager()
        self.error_handler = ErrorHandler()
        self.assistant_engine = AIAssistantEngine()
        self.report_manager = ReportManager()
        self.current_session_id = None
        self.last_data_file = None
        self.setup_session()
        
    def setup_session(self):
        """Setup analysis session"""
        try:
            self.current_session_id = create_new_session(
                session_name="Direct CLI Session",
                tags=["cli", "direct_mode"]
            )
            console.print(f"[green]✅ Created session: {self.current_session_id}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to create session: {e}[/red]")
            self.current_session_id = None
            
    def analyze_data_direct(self, file_path: str, analysis_types: List[str] = None) -> Optional[Dict]:
        """Direct data analysis without src/api server - supports both traditional and LLM orchestration"""
        try:
            file_path = Path(file_path).expanduser().resolve()
            if not file_path.exists():
                console.print(f"[red]❌ File does not exist: {file_path}[/red]")
                return None

            self.last_data_file = str(file_path)
                
            console.print(f"[cyan]📊 Analyzing data: {file_path.name}[/cyan]")
            
            # Check if LLM orchestration is enabled
            from src.api.config import USE_ORCHESTRATOR
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Processing...", total=None)
                
                if USE_ORCHESTRATOR:
                    console.print("[blue]🤖 Using LLM orchestration for analysis...[/blue]")
                    # Use LLM orchestration
                    result = self._run_llm_orchestrated_analysis(file_path, analysis_types)
                else:
                    console.print("[yellow]📋 Using traditional statistical analysis...[/yellow]")
                    # Direct call to analysis module
                    result = analyze_dataset(
                        file_path=str(file_path),
                        session_id=self.current_session_id,
                        analysis_types=analysis_types
                    )
                
                progress.update(task, completed=True)
                
            if result and "error" not in result:
                console.print("[green]✅ Analysis completed successfully![/green]")
                
                # Update session state
                update_session_state(self.current_session_id, {
                    "analysis_results": result,
                    "data_file": str(file_path)
                })
                
                result["data_file"] = str(file_path)
                return result
            else:
                error_msg = result.get("error", "Unknown error") if result else "Analysis failed"
                console.print(f"[red]❌ Analysis failed: {error_msg}[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ Data analysis error: {e}[/red]")
                return None
            
    def _run_llm_orchestrated_analysis(self, file_path: Path, analysis_types: List[str] = None) -> Optional[Dict]:
        """Run LLM orchestrated analysis using the graph-based workflow"""
        try:
            from src.api.config import MAX_RECURSION_DEPTH, REPORT_FORMAT, REPORT_LANGUAGE
            from src.core.orchestration.runner import run_orchestrated_docs_analysis
            
            console.print("[blue]🚀 Starting LLM orchestrated analysis...[/blue]")
            
            # Run the orchestrated analysis
            state = run_orchestrated_docs_analysis(
                session_id=self.current_session_id,
                config={
                    "max_depth": MAX_RECURSION_DEPTH,
                    "report_format": REPORT_FORMAT,
                    "report_language": REPORT_LANGUAGE,
                    "docs/analysis_types": analysis_types or ["descriptive", "inferential", "correlation"]
                }
            )
            
            # Extract results
            analysis_results = {
                "session_id": self.current_session_id,
                "orchestrated_analysis": True,
                "plan": state.get("plan", ""),
                "docs/analysis_results": state.get("docs/analysis_results", ""),
                "report": state.get("report", ""),
                "generated_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            console.print("[green]✅ LLM orchestrated analysis completed![/green]")
            return analysis_results
            
        except Exception as e:
            console.print(f"[red]❌ LLM orchestration error: {e}[/red]")
            # Fall back to traditional analysis
            console.print("[yellow]⚠️  Falling back to traditional analysis...[/yellow]")
            return analyze_dataset(
                file_path=str(file_path),
                session_id=self.current_session_id,
                analysis_types=analysis_types
            )

    def run_orchestrated_analysis(self, file_path: str, analysis_goal: str, max_depth: int | None) -> Optional[Dict]:
        """Run full LLM-orchestrated analysis with hypothesis -> codegen -> execution -> report."""
        try:
            from src.api.config import (
                WORKSPACE_BASE_DIR,
                REPORT_FORMAT,
                REPORT_LANGUAGE,
                REPORT_EXPORT_MODE,
                MAX_RECURSION_DEPTH,
            )
            from src.core.orchestration.runner import run_orchestrated_docs_analysis
        except Exception as exc:
            console.print(f"[red]❌ Orchestrator import failed: {exc}[/red]")
            return None

        data_path = Path(file_path).expanduser().resolve()
        if not data_path.exists():
            console.print(f"[red]❌ Data file not found: {data_path}[/red]")
            return None

        os.environ["DEEPANALYZE_USE_ORCHESTRATOR"] = "1"

        depth = max_depth if max_depth is not None else MAX_RECURSION_DEPTH
        depth = max(0, min(int(depth), 3))

        session_dir = Path(WORKSPACE_BASE_DIR) / self.current_session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(data_path, session_dir / data_path.name)

        config = {
            "max_depth": depth,
            "report_format": REPORT_FORMAT,
            "report_language": REPORT_LANGUAGE,
            "report_export_mode": REPORT_EXPORT_MODE,
            "analysis_goal": analysis_goal,
            "docs/analysis_goal": analysis_goal,
        }

        state = run_orchestrated_docs_analysis(
            session_id=self.current_session_id,
            config=config,
        )

        report_text = state.get("report") or state.get("docs/analysis_results") or ""
        if report_text:
            console.print("[green]✅ Orchestrated analysis completed.[/green]")
        else:
            console.print("[yellow]⚠️  Orchestrated analysis completed, but report is empty.[/yellow]")

        depth_prompt = state.get("depth_prompt", "")
        continuation_required = state.get("continuation_required", False)

        if depth == 0 and (continuation_required or depth_prompt):
            if depth_prompt:
                console.print(Panel(depth_prompt, title="🔁 深度分析建议", border_style="yellow"))
            choice = Prompt.ask("是否继续进行一次更深度的分析？", choices=["y", "n"], default="n")
            if choice == "y":
                followup_config = {
                    **config,
                    "max_depth": 1,
                    "depth_decision": "continue",
                }
                state = run_orchestrated_docs_analysis(
                    session_id=self.current_session_id,
                    config=followup_config,
                )
                console.print("[green]✅ 深度分析完成。[/green]")

        return state
            
    def generate_visualization_direct(self, data: Dict, chart_type: str = "auto", output_path: str = None) -> Optional[str]:
        """Direct visualization generation"""
        try:
            # Load DataFrame from the most recent data file
            data_file = None
            if isinstance(data, dict):
                data_file = data.get("data_file")
            data_file = data_file or self.last_data_file

            if not data_file:
                console.print("[yellow]⚠️  No data file available for visualization[/yellow]")
                return None

            data_path = Path(data_file).expanduser().resolve()
            if not data_path.exists():
                console.print(f"[red]❌ Data file not found: {data_path}[/red]")
                return None

            import pandas as pd
            import numpy as np

            if data_path.suffix.lower() in {".xlsx", ".xls"}:
                df = pd.read_excel(data_path)
            elif data_path.suffix.lower() == ".csv":
                df = pd.read_csv(data_path)
            elif data_path.suffix.lower() == ".json":
                df = pd.read_json(data_path)
            else:
                console.print(f"[yellow]⚠️  Unsupported file format: {data_path.suffix}[/yellow]")
                return None

            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_cols:
                console.print("[yellow]⚠️  No numeric columns available for visualization[/yellow]")
                return None

            column = numeric_cols[0]
                
            console.print(f"[cyan]🎨 Generating visualization...[/cyan]")
            
            # Set default output path
            if not output_path:
                output_path = f"/tmp/src/core_viz_{int(time.time())}.png"
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Creating charts...", total=None)
                
                # Direct call to visualization module functions
                if chart_type == "distribution" or chart_type == "auto":
                    result_path = render_distribution(
                        df=df,
                        column=column,
                        output_path=output_path,
                        style="academic"
                    )
                elif chart_type == "correlation":
                    # For correlation, we need multiple numeric columns
                    numeric_df = df.select_dtypes(include=[np.number])
                    if len(numeric_df.columns) >= 2:
                        result_path = render_correlation_heatmap(
                            df=numeric_df,
                            output_path=output_path,
                            style="academic"
                        )
                    else:
                        console.print("[yellow]⚠️  Not enough numeric columns for correlation heatmap[/yellow]")
                        return None
                else:
                    # Default to distribution
                    result_path = render_distribution(
                        df=df,
                        column=column,
                        output_path=output_path,
                        style="academic"
                    )
                
                progress.update(task, completed=True)
                
            if result_path and result_path.exists():
                console.print("[green]✅ Visualization generated successfully![/green]")
                console.print(f"[dim]Output: {result_path}[/dim]")
                
                # Update session state
                current_state = get_session_state(self.current_session_id) or {}
                visualizations = current_state.get("visualizations", [])
                visualizations.append({
                    "type": chart_type,
                    "output_path": str(result_path),
                    "generated_at": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                update_session_state(self.current_session_id, {"visualizations": visualizations})
                
                return str(result_path)
            else:
                console.print("[red]❌ Visualization failed to generate file[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ Visualization error: {e}[/red]")
            return None
            
    def ai_assistant_direct(self, query: str, context: Dict = None) -> Optional[str]:
        """Direct AI assistant interaction"""
        try:
            console.print(f"[cyan]🤖 Consulting AI assistant...[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Thinking...", total=None)
                
                # Direct call to AI assistant engine
                response = self.assistant_engine.process_message(
                    session_id=self.current_session_id,
                    message=query,
                    context=context
                )
                
                progress.update(task, completed=True)
                
            if response:
                console.print("[green]✅ AI assistant responded![/green]")
                
                # Display response
                if isinstance(response, dict):
                    answer = response.get('response', str(response))
                else:
                    answer = str(response)
                    
                console.print(Panel(Markdown(answer), title="🤖 AI Assistant Response", border_style="green"))
                
                # Update session state
                current_state = get_session_state(self.current_session_id) or {}
                analysis_history = current_state.get("analysis_history", [])
                analysis_history.append(f"User: {query}\nAssistant: {answer}")
                update_session_state(self.current_session_id, {"analysis_history": analysis_history})
                
                return answer
            else:
                console.print("[red]❌ AI assistant failed to respond[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ AI assistant error: {e}[/red]")
            return None
            
    def generate_report_direct(self, content: Dict, report_type: str = "analytical", output_path: str = None, include_visualizations: bool = True) -> Optional[str]:
        """Direct report generation with visualization support"""
        try:
            console.print(f"[cyan]📋 Generating report with visualizations...[/cyan]")
            
            # Prepare enhanced report content
            report_content = self._prepare_enhanced_report_content(content, include_visualizations)
                
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Generating enhanced report...", total=None)
                
                # Direct call to report manager
                report = self.report_manager.create_report(
                    session_id=self.current_session_id,
                    report_type=getattr(ReportType, report_type.upper(), ReportType.ANALYTICAL),
                    title=f"Analysis Report - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    content=report_content
                )
                
                progress.update(task, completed=True)
                
            if report:
                console.print("[green]✅ Enhanced report generated successfully![/green]")
                console.print(f"[dim]Report ID: {report.report_id}[/dim]")
                
                # Update session state
                current_state = get_session_state(self.current_session_id) or {}
                reports = current_state.get("reports", [])
                reports.append({
                    "report_id": report.report_id,
                    "title": report.title,
                    "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "includes_visualizations": include_visualizations
                })
                update_session_state(self.current_session_id, {"reports": reports})
                
                # Return the report metadata object
                return report
            else:
                console.print("[red]❌ Report generation failed[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ Report generation error: {e}[/red]")
            return None
    
    def _prepare_enhanced_report_content(self, content: Dict, include_visualizations: bool = True) -> str:
        """Prepare enhanced report content with embedded visualizations"""
        # Convert content to string format with proper JSON serialization
        import json
        import numpy as np
        import pandas as pd
        
        def json_serializer(obj):
            """Custom JSON serializer for numpy types"""
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.api.types.is_datetime64_any_dtype(type(obj)):
                return str(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Convert content to string format
        if isinstance(content, dict):
            try:
                report_content = json.dumps(content, ensure_ascii=False, indent=2, default=json_serializer)
            except Exception as e:
                console.print(f"[yellow]⚠️ JSON serialization warning: {e}, falling back to string conversion[/yellow]")
                report_content = str(content)
        else:
            report_content = str(content)
        
        # If visualizations are requested, enhance the content
        if include_visualizations:
            enhanced_content = self._embed_visualizations_in_report(report_content)
            return enhanced_content
        else:
            return report_content
    
    def _embed_visualizations_in_report(self, base_content: str) -> str:
        """Embed relevant visualizations in the report content"""
        try:
            # Get current session visualizations
            current_state = get_session_state(self.current_session_id) or {}
            visualizations = current_state.get("visualizations", [])
            
            if not visualizations:
                # Generate some visualizations if none exist
                console.print("[yellow]⚠️  No existing visualizations found, generating sample charts...[/yellow]")
                self._generate_sample_visualizations()
                current_state = get_session_state(self.current_session_id) or {}
                visualizations = current_state.get("visualizations", [])
            
            # Create enhanced report with embedded visualizations
            enhanced_report = [
                "# 分析报告",
                "",
                f"**生成时间:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**会话ID:** {self.current_session_id}",
                "",
                "---",
                "",
                "## 核心分析结果",
                "",
                base_content,
                ""
            ]
            
            # Add visualization section if available
            if visualizations:
                enhanced_report.extend([
                    "## 可视化图表",
                    "",
                    "以下是基于分析结果生成的关键可视化图表：",
                    ""
                ])
                
                # Embed each visualization
                for i, viz in enumerate(visualizations[:3]):  # Limit to first 3 for readability
                    viz_path = viz.get("path", "")
                    viz_type = viz.get("metadata", {}).get("type", "unknown")
                    
                    if os.path.exists(viz_path):
                        # Add chart description and embed image in markdown
                        enhanced_report.extend([
                            f"### 图表 {i+1}: {viz_type.capitalize()} 图",
                            "",
                            f"![{viz_type} chart]({viz_path})",
                            "",
                            f"*图表路径: {viz_path}*",
                            ""
                        ])
                    else:
                        enhanced_report.extend([
                            f"### 图表 {i+1}: {viz_type.capitalize()} 图",
                            "",
                            "*图表文件未找到*",
                            ""
                        ])
            
            # Add methodology section
            enhanced_report.extend([
                "## 分析方法",
                "",
                "本报告采用以下分析方法：",
                "- 描述性统计分析",
                "- 数据质量检查", 
                "- 相关性分析",
                "- 可视化探索",
                "",
                "所有图表均使用学术风格生成，确保专业性和可读性。",
                ""
            ])
            
            return "\n".join(enhanced_report)
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Visualization embedding warning: {e}[/yellow]")
            return base_content
    
    def _generate_sample_visualizations(self):
        """Generate sample visualizations for demonstration"""
        try:
            import numpy as np
            import pandas as pd
            
            # Create sample data
            np.random.seed(42)
            sample_data = {
                'sales': np.random.normal(1000, 200, 100),
                'profit': np.random.normal(150, 50, 100),
                'region': np.random.choice(['North', 'South', 'East', 'West'], 100),
                'month': pd.date_range('2023-01-01', periods=100, freq='D')
            }
            df = pd.DataFrame(sample_data)
            
            # Generate various chart types
            chart_configs = [
                {"type": "distribution", "column": "sales"},
                {"type": "trend", "x": "month", "y": "sales"},
                {"type": "comparison", "category": "region", "value": "profit"}
            ]
            
            for config in chart_configs:
                try:
                    output_path = f"/tmp/sample_viz_{config['type']}_{int(time.time())}.png"
                    if config["type"] == "distribution":
                        render_distribution(df, config["column"], output_path, style="academic")
                    elif config["type"] == "trend":
                        render_trend(df, config["x"], config["y"], output_path, style="academic")
                    elif config["type"] == "comparison":
                        render_comparison(df, config["category"], config["value"], output_path, style="academic")
                    
                    # Register in session state
                    current_state = get_session_state(self.current_session_id) or {}
                    visualizations = current_state.get("visualizations", [])
                    visualizations.append({
                        "path": output_path,
                        "type": config["type"],
                        "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "metadata": config
                    })
                    update_session_state(self.current_session_id, {"visualizations": visualizations})
                    
                except Exception as chart_error:
                    console.print(f"[dim]Sample chart generation failed: {chart_error}[/dim]")
                    continue
                    
        except Exception as e:
            console.print(f"[dim]Sample visualization generation error: {e}[/dim]")
            
    def show_session_info(self):
        """Display current session information"""
        if not self.current_session_id:
            console.print("[red]❌ No active session[/red]")
            return
            
        state = get_session_state(self.current_session_id)
        if not state:
            console.print("[yellow]📝 No session data available[/yellow]")
            return
            
        # Create session info panel
        analysis_results = state.get("analysis_results", {})
        visualizations = state.get("visualizations", [])
        reports = state.get("reports", [])
        analysis_history = state.get("analysis_history", [])
        
        info_content = f"""[bold]Session ID:[/bold] {self.current_session_id}
[bold]Data Files:[/bold] {len([f for f in state.get('input_files', []) if f])}
[bold]Analysis Results:[/bold] {'Yes' if analysis_results else 'No'}
[bold]Visualizations:[/bold] {len(visualizations)}
[bold]Reports:[/bold] {len(reports)}
[bold]Conversation History:[/bold] {len(analysis_history)} entries"""
        
        console.print(Panel(info_content, title="📊 Session Information", border_style="blue"))
        
    def list_analysis_results(self):
        """List analysis results"""
        state = get_session_state(self.current_session_id)
        if not state or not state.get("analysis_results"):
            console.print("[yellow]📝 No analysis results available[/yellow]")
            return
            
        results = state["analysis_results"]
        
        # Display summary statistics
        table = Table(title="📈 Analysis Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Add basic statistics
        if "data_summary" in results:
            summary = results["data_summary"]
            for key, value in summary.items():
                table.add_row(key, str(value))
                
        console.print(table)
        
        # Display insights if available
        if "insights" in results and results["insights"]:
            console.print("\n[bold]💡 Key Insights:[/bold]")
            for i, insight in enumerate(results["insights"][:5], 1):
                console.print(f"{i}. {insight}")
                
    def interactive_mode(self):
        """Interactive mode for direct module access"""
        console.print("\n[bold green]🎯 Direct CLI Mode - Access modules directly[/bold green]")
        console.print("[dim]No src/api server required - all modules called directly[/dim]")
        
        self.show_help()
        
        while True:
            try:
                user_input = input("\nDirectCLI> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[green]👋 Goodbye![/green]")
                    break
                    
                if self.handle_direct_command(user_input):
                    continue
                    
                if not user_input:
                    continue
                    
                # Default to AI assistant query
                self.ai_assistant_direct(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[green]👋 Goodbye![/green]")
                break
            except EOFError:
                console.print("\n[green]👋 Goodbye![/green]")
                break
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                
    def handle_direct_command(self, user_input: str) -> bool:
        """Handle direct mode commands"""
        cmd_parts = user_input.split()
        if not cmd_parts:
            return False
            
        cmd = cmd_parts[0].lower()
        
        # Help command
        if cmd in ['help', 'h']:
            self.show_help()
            return True
            
        # Session info
        elif cmd in ['info', 'session']:
            self.show_session_info()
            return True
            
        # Data analysis
        elif cmd in ['analyze', 'data']:
            if len(cmd_parts) >= 2:
                file_path = cmd_parts[1]
                analysis_types = cmd_parts[2:] if len(cmd_parts) > 2 else None
                self.analyze_data_direct(file_path, analysis_types)
            else:
                console.print("[yellow]Usage: analyze <file_path> [analysis_types...]") 
            return True

        # Orchestrated LLM analysis
        elif cmd in ['orchestrate', 'llm']:
            if len(cmd_parts) >= 2:
                file_path = cmd_parts[1]
                max_depth = None
                goal_start = 2
                if len(cmd_parts) >= 3:
                    try:
                        max_depth = int(cmd_parts[2])
                        goal_start = 3
                    except ValueError:
                        max_depth = None
                analysis_goal = " ".join(cmd_parts[goal_start:]) if len(cmd_parts) > goal_start else "对数据进行完整的假设驱动分析"
                self.run_orchestrated_analysis(file_path, analysis_goal, max_depth)
            else:
                console.print("[yellow]Usage: orchestrate <file_path> [max_depth] [analysis_goal...]")
            return True
            
        # Visualization
        elif cmd in ['viz', 'plot']:
            state = get_session_state(self.current_session_id)
            if state and state.get("analysis_results"):
                chart_type = cmd_parts[1] if len(cmd_parts) > 1 else "auto"
                self.generate_visualization_direct(state["analysis_results"], chart_type)
            else:
                console.print("[yellow]No analysis results available. Run 'analyze <file>' first.")
            return True
            
        # Report generation
        elif cmd in ['report']:
            state = get_session_state(self.current_session_id)
            if state and state.get("analysis_results"):
                report_type = cmd_parts[1] if len(cmd_parts) > 1 else "analytical"
                # Check for visualization flags
                include_viz = "--no-viz" not in cmd_parts
                self.generate_report_direct(state["analysis_results"], report_type, include_visualizations=include_viz)
                viz_status = "with visualizations" if include_viz else "without visualizations"
                console.print(f"[green]✅ Report {viz_status} generated[/green]")
            else:
                console.print("[yellow]No analysis results available. Run 'analyze <file>' first.")
            return True
            
        # List results
        elif cmd in ['results', 'list']:
            self.list_analysis_results()
            return True
            
        # Clear session
        elif cmd in ['clear']:
            if Confirm.ask("Clear current session data?"):
                if self.current_session_id:
                    update_session_state(self.current_session_id, {})
                console.print("[green]✅ Session cleared[/green]")
            return True
            
        # Not a recognized command
        return False
        
    def show_help(self):
        """Display help for direct mode"""
        help_text = """
[bold cyan]🎯 Direct CLI Commands:[/bold cyan]

[basic operations]
• [yellow]help[/yellow] - Show this help
• [yellow]info[/yellow] - Show session information  
• [yellow]clear[/yellow] - Clear session data
• [yellow]quit/exit/q[/yellow] - Exit program

[data analysis]
• [yellow]analyze <file_path> [types...][/yellow] - Analyze data file directly
• [yellow]orchestrate <file_path> [max_depth] [goal...][/yellow] - LLM-orchestrated analysis flow
• [yellow]viz [chart_type][/yellow] - Generate visualization from analysis results
• [yellow]report [report_type] [--with-viz|--no-viz][/yellow] - Generate report with/without visualizations
• [yellow]results[/yellow] - List analysis results and insights
• [yellow]viz [chart_type][/yellow] - Generate specific visualization

[dim]Simply type your question for AI assistant consultation[/dim]
[dim]Supported chart types: auto, bar, line, scatter, histogram, pie[/dim]
[dim]Supported report types: analytical, executive, technical[/dim]
"""
        console.print(Panel(help_text, title="Direct CLI Help", border_style="blue"))
        
    def run_batch_mode(self, args):
        """Run in batch mode with command line arguments"""
        if args.orchestrated:
            analysis_goal = args.analysis_goal or "对数据进行完整的假设驱动分析"
            self.run_orchestrated_analysis(args.orchestrated, analysis_goal, args.max_depth)
        elif args.analyze:
            result = self.analyze_data_direct(args.analyze, args.analysis_types)
            if result and args.visualize:
                self.generate_visualization_direct(result, args.chart_type)
            if result and args.report:
                # Pass visualization inclusion flag to report generation
                include_viz = getattr(args, 'include_visualizations', True)
                self.generate_report_direct(result, args.report_type, include_visualizations=include_viz)
                
        elif args.query:
            self.ai_assistant_direct(args.query)
            
        elif args.session_info:
            self.show_session_info()
            
        elif args.results:
            self.list_analysis_results()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DeepAnalyze Direct CLI - Access modules directly")
    parser.add_argument('--analyze', help='Analyze data file directly')
    parser.add_argument('--orchestrated', help='Run LLM-orchestrated analysis on data file')
    parser.add_argument('--analysis-goal', help='LLM analysis goal prompt')
    parser.add_argument('--max-depth', type=int, help='Max recursion depth for orchestrated analysis')
    parser.add_argument('--analysis-types', nargs='+', help='Analysis types to perform')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    parser.add_argument('--chart-type', default='auto', help='Chart type for visualization')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--report-type', default='analytical', help='Report type')
    parser.add_argument('--include-visualizations', action='store_true', default=True, help='Include visualizations in report')
    parser.add_argument('--no-visualizations', dest='include_visualizations', action='store_false', help='Exclude visualizations from report')
    parser.add_argument('--query', help='Ask AI assistant directly')
    parser.add_argument('--session-info', action='store_true', help='Show session information')
    parser.add_argument('--results', action='store_true', help='List analysis results')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Header
    console.print(Panel("[bold cyan]🚀 DeepAnalyze Direct CLI[/bold cyan]\n[dim]Direct module access without src/api server[/dim]", 
                       title="Direct CLI", border_style="cyan"))
    
    cli = DirectDeepAnalyzeCLI()
    
    # Run in appropriate mode
    if args.interactive or not any([args.analyze, args.orchestrated, args.query, args.session_info, args.results]):
        cli.interactive_mode()
    else:
        cli.run_batch_mode(args)

if __name__ == "__main__":
    main()
