#!/usr/bin/env python3
"""
DeepAnalyze Unified CLI - Choose between API mode and Direct mode
Unified entry point for both API-based and direct module access modes
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def show_welcome():
    """Display welcome message"""
    welcome_text = """[bold cyan]🚀 DeepAnalyze Unified CLI[/bold cyan]

Choose your preferred mode:
• [green]API Mode[/green] - Connect to running API server for full features
• [blue]Direct Mode[/blue] - Direct module access without server (local only)

[dim]Use --help for detailed usage information[/dim]"""
    
    console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

def main():
    parser = argparse.ArgumentParser(
        description="DeepAnalyze Unified CLI - Choose between API and Direct modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # API Mode - requires running server
  python unified_cli.py --api-mode
  python unified_cli.py --api-mode --upload data.csv
  
  # Direct Mode - no server required  
  python unified_cli.py --direct-mode
  python unified_cli.py --direct-mode --analyze data.csv --visualize --report
  
  # Interactive modes
  python unified_cli.py --api-mode --interactive
  python unified_cli.py --direct-mode --interactive
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--api-mode', '-a', action='store_true', 
                           help='Use API mode (requires running server)')
    mode_group.add_argument('--direct-mode', '-d', action='store_true',
                           help='Use direct mode (no server required)')
    
    # API mode specific arguments
    api_group = parser.add_argument_group('API Mode Options')
    api_group.add_argument('--upload', help='Upload file in API mode')
    api_group.add_argument('--chat', help='Send message in API mode')
    api_group.add_argument('--api-interactive', action='store_true', 
                          help='Interactive API mode')
    
    # Direct mode specific arguments  
    direct_group = parser.add_argument_group('Direct Mode Options')
    direct_group.add_argument('--analyze', help='Analyze data file directly')
    direct_group.add_argument('--analysis-types', nargs='+', help='Analysis types')
    direct_group.add_argument('--visualize', action='store_true', help='Generate visualization')
    direct_group.add_argument('--chart-type', default='auto', help='Chart type')
    direct_group.add_argument('--report', action='store_true', help='Generate report')
    direct_group.add_argument('--report-type', default='analytical', help='Report type')
    direct_group.add_argument('--query', help='Ask AI assistant directly')
    direct_group.add_argument('--direct-interactive', action='store_true',
                             help='Interactive direct mode')
    direct_group.add_argument('--session-info', action='store_true', help='Show session info')
    direct_group.add_argument('--results', action='store_true', help='List results')
    
    # Common arguments
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--version', action='version', version='DeepAnalyze CLI 1.0')
    
    args = parser.parse_args()
    
    # Show welcome
    if not any([args.upload, args.chat, args.analyze, args.query, 
                args.api_interactive, args.direct_interactive, args.session_info, args.results]):
        show_welcome()
    
    try:
        if args.api_mode:
            # Run API mode
            run_api_mode(args)
        elif args.direct_mode:
            # Run direct mode  
            run_direct_mode(args)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def run_api_mode(args):
    """Run API mode CLI"""
    api_cli_path = Path(__file__).parent / "api_cli.py"
    
    if not api_cli_path.exists():
        console.print("[red]❌ API CLI module not found[/red]")
        sys.exit(1)
        
    # Build command arguments
    cmd_args = ['python', str(api_cli_path)]
    
    if args.upload:
        cmd_args.extend(['--upload', args.upload])
    if args.chat:
        cmd_args.extend(['--chat', args.chat])
    if args.api_interactive:
        cmd_args.append('--interactive')
    if args.verbose:
        cmd_args.append('--verbose')
        
    # If no specific action, run interactive mode
    if not any([args.upload, args.chat, args.api_interactive]):
        cmd_args.append('--interactive')
        
    # Execute API CLI
    import subprocess
    try:
        subprocess.run(cmd_args, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ API CLI execution failed with code {e.returncode}[/red]")
        sys.exit(e.returncode)

def run_direct_mode(args):
    """Run direct mode CLI"""
    direct_cli_path = Path(__file__).parent / "direct_cli.py"
    
    if not direct_cli_path.exists():
        console.print("[red]❌ Direct CLI module not found[/red]")
        sys.exit(1)
        
    # Build command arguments
    cmd_args = ['python', str(direct_cli_path)]
    
    if args.analyze:
        cmd_args.extend(['--analyze', args.analyze])
        if args.analysis_types:
            cmd_args.extend(['--analysis-types'] + args.analysis_types)
        if args.visualize:
            cmd_args.append('--visualize')
        if args.chart_type:
            cmd_args.extend(['--chart-type', args.chart_type])
        if args.report:
            cmd_args.append('--report')
        if args.report_type:
            cmd_args.extend(['--report-type', args.report_type])
            
    if args.query:
        cmd_args.extend(['--query', args.query])
    if args.session_info:
        cmd_args.append('--session-info')
    if args.results:
        cmd_args.append('--results')
    if args.direct_interactive:
        cmd_args.append('--interactive')
    if args.verbose:
        cmd_args.append('--verbose')
        
    # If no specific action, run interactive mode
    if not any([args.analyze, args.query, args.session_info, args.results, args.direct_interactive]):
        cmd_args.append('--interactive')
        
    # Execute Direct CLI
    import subprocess
    try:
        subprocess.run(cmd_args, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Direct CLI execution failed with code {e.returncode}[/red]")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
