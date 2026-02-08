#!/usr/bin/env python3
"""
DeepAnalyze Direct CLI - Direct module function calls without API server
Support direct access to core modules: data analysis, visualization, AI assistant, report generation
"""

import os
import sys
import json
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

# Import core modules
from deepanalyze.analytics.advanced_analyzer import analyze_dataset
from deepanalyze.visualization.plotter import render_distribution, render_correlation_heatmap
from deepanalyze.assistant.engine import AIAssistantEngine
from deepanalyze.reporting.manager import ReportManager, ReportType
from deepanalyze.state.manager import StateManager, create_new_session, get_session_state, update_session_state
from deepanalyze.error.handler import ErrorHandler, ErrorSeverity, ErrorCategory

console = Console()

class DirectDeepAnalyzeCLI:
    def __init__(self):
        """Initialize direct CLI client"""
        self.state_manager = StateManager()
        self.error_handler = ErrorHandler()
        self.assistant_engine = AIAssistantEngine()
        self.report_manager = ReportManager()
        self.current_session_id = None
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
        """Direct data analysis without API server"""
        try:
            file_path = Path(file_path).expanduser().resolve()
            if not file_path.exists():
                console.print(f"[red]❌ File does not exist: {file_path}[/red]")
                return None
                
            console.print(f"[cyan]📊 Analyzing data: {file_path.name}[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Processing...", total=None)
                
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
                
                return result
            else:
                error_msg = result.get("error", "Unknown error") if result else "Analysis failed"
                console.print(f"[red]❌ Analysis failed: {error_msg}[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ Data analysis error: {e}[/red]")
            return None
            
    def generate_visualization_direct(self, data: Dict, chart_type: str = "auto", output_path: str = None) -> Optional[str]:
        """Direct visualization generation"""
        try:
            # Extract DataFrame from analysis results
            if isinstance(data, dict) and "data_summary" in data:
                # Try to get DataFrame from session state or recreate from summary
                import pandas as pd
                import numpy as np
                
                # Create sample data for demonstration
                sample_data = {
                    'values': np.random.normal(100, 15, 100),
                    'categories': np.random.choice(['A', 'B', 'C'], 100)
                }
                df = pd.DataFrame(sample_data)
                column = 'values'
            else:
                console.print("[yellow]⚠️  No suitable data for visualization[/yellow]")
                return None
                
            console.print(f"[cyan]🎨 Generating visualization...[/cyan]")
            
            # Set default output path
            if not output_path:
                output_path = f"/tmp/deepanalyze_viz_{int(time.time())}.png"
            
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
            
    def generate_report_direct(self, content: Dict, report_type: str = "analytical", output_path: str = None) -> Optional[str]:
        """Direct report generation"""
        try:
            console.print(f"[cyan]📋 Generating report...[/cyan]")
            
            # Prepare report content
            if isinstance(content, dict):
                report_content = json.dumps(content, ensure_ascii=False, indent=2)
            else:
                report_content = str(content)
                
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Generating report...", total=None)
                
                # Direct call to report manager
                report = self.report_manager.create_report(
                    session_id=self.current_session_id,
                    report_type=getattr(ReportType, report_type.upper(), ReportType.ANALYTICAL),
                    title=f"Analysis Report - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    content=report_content,
                    output_path=output_path
                )
                
                progress.update(task, completed=True)
                
            if report:
                console.print("[green]✅ Report generated successfully![/green]")
                console.print(f"[dim]Report ID: {getattr(report, 'report_id', 'N/A')}[/dim]")
                
                # Update session state
                current_state = get_session_state(self.current_session_id) or {}
                reports = current_state.get("reports", [])
                reports.append({
                    "report_id": getattr(report, 'report_id', 'N/A'),
                    "title": getattr(report, 'title', 'Untitled'),
                    "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                update_session_state(self.current_session_id, {"reports": reports})
                
                return getattr(report, 'file_path', None)
            else:
                console.print("[red]❌ Report generation failed[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ Report generation error: {e}[/red]")
            return None
            
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
        console.print("[dim]No API server required - all modules called directly[/dim]")
        
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
                self.generate_report_direct(state["analysis_results"], report_type)
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
• [yellow]viz [chart_type][/yellow] - Generate visualization from analysis results
• [yellow]report [report_type][/yellow] - Generate report from analysis results
• [yellow]results[/yellow] - List analysis results and insights

[dim]Simply type your question for AI assistant consultation[/dim]
[dim]Supported chart types: auto, bar, line, scatter, histogram, pie[/dim]
[dim]Supported report types: analytical, executive, technical[/dim]
"""
        console.print(Panel(help_text, title="Direct CLI Help", border_style="blue"))
        
    def run_batch_mode(self, args):
        """Run in batch mode with command line arguments"""
        if args.analyze:
            result = self.analyze_data_direct(args.analyze, args.analysis_types)
            if result and args.visualize:
                self.generate_visualization_direct(result, args.chart_type)
            if result and args.report:
                self.generate_report_direct(result, args.report_type)
                
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
    parser.add_argument('--analysis-types', nargs='+', help='Analysis types to perform')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    parser.add_argument('--chart-type', default='auto', help='Chart type for visualization')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--report-type', default='analytical', help='Report type')
    parser.add_argument('--query', help='Ask AI assistant directly')
    parser.add_argument('--session-info', action='store_true', help='Show session information')
    parser.add_argument('--results', action='store_true', help='List analysis results')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Header
    console.print(Panel("[bold cyan]🚀 DeepAnalyze Direct CLI[/bold cyan]\n[dim]Direct module access without API server[/dim]", 
                       title="Direct CLI", border_style="cyan"))
    
    cli = DirectDeepAnalyzeCLI()
    
    # Run in appropriate mode
    if args.interactive or not any([args.analyze, args.query, args.session_info, args.results]):
        cli.interactive_mode()
    else:
        cli.run_batch_mode(args)

if __name__ == "__main__":
    main()