#!/usr/bin/env python3
"""
Demo CLI Wrapper - Shows the complete one-command analysis workflow
Usage: python demo_cli_wrapper.py --input <file> --output <report.html>
"""

import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="DeepAnalyze CLI Demo - One-command analysis")
    parser.add_argument("--input", "-i", required=True, help="Input data file path")
    parser.add_argument("--output", "-o", default="analysis_report.html", help="Output report file name")
    
    args = parser.parse_args()
    
    print("🚀 DeepAnalyze CLI Demo")
    print("=" * 50)
    print(f"Input file: {args.input}")
    print(f"Output report: {args.output}")
    print("=" * 50)
    
    # Validate input file exists with proper path resolution
    input_path = Path(args.input).resolve()
    project_root = Path(__file__).resolve().parent.parent
    
    # Check if file exists as absolute path
    if not input_path.exists():
        # Try relative to project root
        input_path = (project_root / args.input).resolve()
        if not input_path.exists():
            print(f"❌ Error: Input file '{args.input}' not found")
            print(f"   Checked paths:")
            print(f"   - {Path(args.input).resolve()}")
            print(f"   - {project_root / args.input}")
            return False
    
    print(f"✅ Found input file: {input_path}")
    
    try:
        # Import and run the complete analysis
        import subprocess
        import os
        
        # Change to project directory
        os.chdir(project_root)
        print(f"📂 Working directory changed to: {project_root}")
        
        # Run the complete analysis using our new pipeline
        print("📊 Running complete analysis with enhanced pipeline...")
        result = subprocess.run([
            "python", "-c", f"""
import sys
sys.path.insert(0, '{project_root}')
from src.core.analysis_pipeline import AnalysisPipeline

pipeline = AnalysisPipeline()
data_file = '{input_path}'
results = pipeline.run_complete_analysis(data_file)
print('Analysis completed successfully!')
print(f'Plan ID: {{results["plan_id"]}}')
print(f'Artifacts generated: {{len(results["artifacts"])}}')
"""
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print("✅ Analysis completed successfully!")
            print(result.stdout)
            
            # Find the latest report
            import glob
            report_files = glob.glob("data/sessions/active/artifacts/*/report/analysis_report.html")
            if report_files:
                latest_report = sorted(report_files)[-1]  # Get most recent
                import shutil
                shutil.copy(latest_report, args.output)
                print(f"📄 Report saved as: {args.output}")
            else:
                print("⚠️  Could not find generated report file")
                return False
                
            print("\n📈 Generated outputs:")
            print("   • HTML Report with interactive visualizations")
            print("   • PNG Charts showing data distributions") 
            print("   • JSON files with analysis results")
            print("   • Complete analysis pipeline execution")
            
            print("\n🎯 Analysis completed! The report includes:")
            print("   ✓ Data overview and quality assessment")
            print("   ✓ Statistical summaries")
            print("   ✓ Distribution visualizations")
            print("   ✓ Correlation analysis")
            print("   ✓ Interactive HTML format")
            print("   ✓ AI-driven hypothesis generation")
            
            return True
        else:
            print(f"❌ Analysis failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)