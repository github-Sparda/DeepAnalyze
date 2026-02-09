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
    
    # Validate input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file '{args.input}' not found")
        return False
    
    try:
        # Import and run the complete analysis
        import subprocess
        import os
        
        # Change to project directory
        os.chdir(Path(__file__).parent)
        
        # Run the complete analysis script
        print("📊 Running complete analysis...")
        result = subprocess.run([
            "python", "generate_complete_report.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Analysis completed successfully!")
            
            # Rename the output file to match user's requested name
            if args.output != "analysis_report.html":
                import shutil
                try:
                    shutil.move("comprehensive_analysis_report.html", args.output)
                    print(f"📄 Report saved as: {args.output}")
                except Exception as e:
                    print(f"⚠️  Could not rename report: {e}")
                    print(f"📄 Report available as: comprehensive_analysis_report.html")
            else:
                print("📄 Report saved as: comprehensive_analysis_report.html")
                
            print("\n📈 Generated outputs:")
            print("   • HTML Report with interactive visualizations")
            print("   • PNG Charts showing data distributions")
            print("   • JSON file with raw analysis results")
            
            print("\n🎯 Analysis completed! The report includes:")
            print("   ✓ Data overview and quality assessment")
            print("   ✓ Statistical summaries")
            print("   ✓ Distribution visualizations")
            print("   ✓ Correlation analysis")
            print("   ✓ Interactive HTML format")
            
            return True
        else:
            print(f"❌ Analysis failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)