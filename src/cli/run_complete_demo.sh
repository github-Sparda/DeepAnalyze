#!/usr/bin/env bash
#
# DeepAnalyze CLI 完整演示脚本
# 展示从数据质量检查到报告生成的完整流程

set -e  # 遇到错误立即退出

echo "🚀 DeepAnalyze CLI 完整演示"
echo "==========================="
echo ""

# 设置变量
DATA_FILE="../../data/examples/simpson_paradox_docs/analysis/data/Simpson.csv"
OUTPUT_DIR="./demo_output"
CLI_SCRIPT="direct_cli.py"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "📋 步骤1: 数据质量检查"
echo "------------------------"
python "$CLI_SCRIPT" quality \
    --data-file "$DATA_FILE" \
    --output-file "$OUTPUT_DIR/quality_report.json"

echo ""
echo "📊 步骤2: 描述性统计分析"
echo "------------------------"
python "$CLI_SCRIPT" analyze \
    --data-file "$DATA_FILE" \
    --type descriptive \
    --output-format json \
    --output-file "$OUTPUT_DIR/descriptive_docs/analysis.json"

echo ""
echo "🔗 步骤3: 相关性分析"
echo "-------------------"
python "$CLI_SCRIPT" analyze \
    --data-file "$DATA_FILE" \
    --type correlation \
    --output-file "$OUTPUT_DIR/correlation_docs/analysis.json"

echo ""
echo "🛠️ 步骤4: 查看可用工具"
echo "---------------------"
python "$CLI_SCRIPT" tools --list

echo ""
echo "📁 输出文件列表:"
echo "---------------"
ls -la "$OUTPUT_DIR/"

echo ""
echo "✅ 演示完成！"
echo "输出文件保存在: $OUTPUT_DIR/"
echo ""
echo "💡 提示:"
echo "- 查看质量报告: cat $OUTPUT_DIR/quality_report.json | python -m json.tool"
echo "- 查看分析结果: cat $OUTPUT_DIR/descriptive_docs/analysis.json | python -m json.tool"