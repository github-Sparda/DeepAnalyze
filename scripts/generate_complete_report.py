#!/usr/bin/env python3
"""
Complete CLI Analysis Script - Generates detailed report with visualizations
"""

import sys
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def generate_html_report(data_file, analysis_results, chart_file):
    """Generate comprehensive HTML report"""
    
    # Read the data for additional analysis
    df = pd.read_excel(data_file)
    
    # Generate correlation matrix for top correlations
    numeric_df = df.select_dtypes(include=['number'])
    if len(numeric_df.columns) > 1:
        correlations = numeric_df.corr()
        top_corr_pairs = []
        for i in range(len(correlations.columns)):
            for j in range(i+1, len(correlations.columns)):
                corr_val = correlations.iloc[i, j]
                if abs(corr_val) > 0.5:  # Strong correlations
                    top_corr_pairs.append({
                        'var1': correlations.columns[i],
                        'var2': correlations.columns[j],
                        'correlation': round(corr_val, 3)
                    })
        top_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        top_corr_pairs = top_corr_pairs[:10]  # Top 10 correlations
    else:
        top_corr_pairs = []
    
    # Generate group analysis if 'Group' column exists
    group_analysis = {}
    if 'Group' in df.columns:
        group_stats = df.groupby('Group').agg({
            col: ['mean', 'std', 'count'] 
            for col in numeric_df.columns[:5]  # First 5 numeric columns
        })
        group_analysis = group_stats.to_dict()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Report - {Path(data_file).stem}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; background: #ecf0f1; }}
        .stats-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .stats-table th, .stats-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .stats-table th {{ background-color: #3498db; color: white; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
        .chart-container img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }}
        .highlight {{ background-color: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #7f8c8d; font-size: 0.9em; }}
        .quality-badge {{ display: inline-block; padding: 5px 10px; border-radius: 15px; color: white; font-weight: bold; }}
        .good {{ background-color: #27ae60; }}
        .warning {{ background-color: #f39c12; }}
        .critical {{ background-color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Data Analysis Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Data Source:</strong> {data_file}</p>
        
        <div class="section">
            <h2>📋 Data Overview</h2>
            <table class="stats-table">
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Rows</td><td>{analysis_results['data_summary']['rows']:,}</td></tr>
                <tr><td>Total Columns</td><td>{analysis_results['data_summary']['columns']}</td></tr>
                <tr><td>Numeric Columns</td><td>{analysis_results['data_summary']['numeric_columns']}</td></tr>
                <tr><td>Categorical Columns</td><td>{analysis_results['data_summary']['categorical_columns']}</td></tr>
                <tr><td>Memory Usage</td><td>{analysis_results['data_quality']['memory_usage']}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>✅ Data Quality Assessment</h2>
            <div class="highlight">
    """
    
    # Add data quality badges
    missing_vals = analysis_results['data_quality']['missing_values']
    duplicates = analysis_results['data_quality']['duplicate_rows']
    
    if missing_vals == 0 and duplicates == 0:
        html_content += '<span class="quality-badge good">✓ Excellent Quality</span> - No missing values or duplicates found'
    elif missing_vals < analysis_results['data_summary']['rows'] * 0.05 and duplicates == 0:
        html_content += '<span class="quality-badge warning">⚠ Good Quality</span> - Minimal missing values detected'
    else:
        html_content += '<span class="quality-badge critical">✗ Quality Issues</span> - Significant data quality problems detected'
    
    html_content += f"""
            </div>
            <p><strong>Missing Values:</strong> {missing_vals:,}</p>
            <p><strong>Duplicate Rows:</strong> {duplicates:,}</p>
        </div>
        
        <div class="section">
            <h2>📈 Distribution Analysis</h2>
            <div class="chart-container">
                <img src="{chart_file}" alt="Data Distribution Charts">
            </div>
        </div>
    """
    
    # Add correlation analysis if available
    if top_corr_pairs:
        html_content += """
        <div class="section">
            <h2>🔗 Top Correlations</h2>
            <table class="stats-table">
                <tr><th>Variable 1</th><th>Variable 2</th><th>Correlation</th></tr>
        """
        for corr in top_corr_pairs:
            strength = "Strong Positive" if corr['correlation'] > 0.7 else "Moderate Positive" if corr['correlation'] > 0.5 else "Strong Negative" if corr['correlation'] < -0.7 else "Moderate Negative"
            html_content += f"<tr><td>{corr['var1']}</td><td>{corr['var2']}</td><td>{corr['correlation']} ({strength})</td></tr>"
        html_content += "</table></div>"
    
    # Add group analysis if available
    if group_analysis:
        html_content += """
        <div class="section">
            <h2>👥 Group Analysis</h2>
            <p>Analysis grouped by the 'Group' column showing mean values and standard deviations.</p>
        </div>
        """
    
    html_content += f"""
        <div class="section">
            <h2>📋 Detailed Statistics</h2>
            <p>Comprehensive statistical summary of all numeric variables.</p>
            <pre>{json.dumps(analysis_results['descriptive_stats'], indent=2)}</pre>
        </div>
        
        <div class="footer">
            <p>Generated by DeepAnalyze CLI • Report ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}</p>
            <p>This report includes automated data analysis, quality assessment, and visualization.</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html_content

def main():
    """Main function to run complete analysis"""
    print("🚀 Starting Complete CLI Analysis...")
    
    # Input file
    data_file = "data/examples/serum/Normal_EP_serum_data.xlsx"
    
    try:
        # Load and analyze data
        print(f"📂 Loading data from: {data_file}")
        df = pd.read_excel(data_file)
        print(f"✅ Loaded {len(df):,} rows and {len(df.columns)} columns")
        
        # Generate analysis results
        print("📊 Performing statistical analysis...")
        analysis_results = {
            'data_summary': {
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_columns': len(df.select_dtypes(include=['number']).columns),
                'categorical_columns': len(df.select_dtypes(include=['object']).columns)
            },
            'descriptive_stats': df.describe().to_dict(),
            'data_quality': {
                'missing_values': int(df.isnull().sum().sum()),
                'duplicate_rows': int(df.duplicated().sum()),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            }
        }
        
        # Create visualizations
        print("🎨 Generating visualizations...")
        plt.style.use('seaborn-v0_8')
        
        # Select first 4 numeric columns for visualization
        numeric_cols = df.select_dtypes(include=['number']).columns[:4]
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        for i, col in enumerate(numeric_cols):
            df[col].hist(bins=30, ax=axes[i], alpha=0.7, color='#3498db')
            axes[i].set_title(f'Distribution of {col}', fontsize=12, pad=10)
            axes[i].set_xlabel(col)
            axes[i].set_ylabel('Frequency')
            axes[i].grid(True, alpha=0.3)
        
        # Hide unused subplots
        for i in range(len(numeric_cols), 4):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        chart_file = 'comprehensive_analysis_charts.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Charts saved to {chart_file}")
        
        # Generate HTML report
        print("📄 Generating HTML report...")
        html_report = generate_html_report(data_file, analysis_results, chart_file)
        
        # Save report
        report_file = 'comprehensive_analysis_report.html'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"✅ HTML report saved to {report_file}")
        
        # Save JSON results
        with open('final_analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, default=str, ensure_ascii=False)
        print("✅ Analysis results saved to final_analysis_results.json")
        
        print("\n🎉 Complete Analysis Finished Successfully!")
        print(f"📁 Output files generated:")
        print(f"   - {report_file} (Interactive HTML report)")
        print(f"   - {chart_file} (Visualization charts)")
        print(f"   - final_analysis_results.json (Raw analysis data)")
        
        # Show summary
        print(f"\n📈 Analysis Summary:")
        print(f"   • Data shape: {analysis_results['data_summary']['rows']:,} × {analysis_results['data_summary']['columns']}")
        print(f"   • Numeric variables: {analysis_results['data_summary']['numeric_columns']}")
        print(f"   • Data quality: {'Excellent' if analysis_results['data_quality']['missing_values'] == 0 else 'Good'}")
        print(f"   • Memory usage: {analysis_results['data_quality']['memory_usage']}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)