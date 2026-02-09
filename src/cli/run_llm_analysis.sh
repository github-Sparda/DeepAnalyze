#!/usr/bin/env bash
#
# DeepAnalyze LLM驱动的完整数据分析脚本
# 启用完整的AI分析流程：假设生成→自主编程→执行分析→迭代优化

set -e

echo "🚀 DeepAnalyze LLM驱动数据分析"
echo "==============================="
echo ""

# 设置环境变量启用LLM编排
export DEEPANALYZE_USE_ORCHESTRATOR=1
export DEEPANALYZE_MAX_DEPTH=3

# 设置变量
DATA_FILE="../../data/examples/simpson_paradox_analysis/data/Simpson.csv"
CLI_SCRIPT="direct_cli.py"

echo "📂 分析文件: $DATA_FILE"
echo "🔧 使用脚本: $CLI_SCRIPT"
echo "🤖 AI编排模式: 已启用"
echo "🔄 最大递归深度: 3"
echo ""

# 检查文件是否存在
if [ ! -f "$DATA_FILE" ]; then
    echo "❌ 数据文件不存在: $DATA_FILE"
    exit 1
fi

echo "✅ 开始LLM驱动的完整分析流程..."
echo ""

# 一步完成所有分析
echo "🧠 执行LLM驱动的智能数据分析..."
python "$CLI_SCRIPT" --analyze "$DATA_FILE" \
    --docs/analysis-types descriptive inferential correlation quality predictive \
    --report \
    --report-type analytical \
    --visualize

echo ""
echo "✅ LLM分析完成！"

echo ""
echo "📋 查看分析结果:"
python "$CLI_SCRIPT" --results

echo ""
echo "ℹ️  查看会话信息:"
python "$CLI_SCRIPT" --session-info

echo ""
echo "🎯 LLM分析特点:"
echo "- 自动生成研究假设和分析计划"
echo "- 自主编程实现复杂的统计分析"
echo "- 智能解读分析结果和发现洞见"
echo "- 迭代优化分析策略"
echo "- 生成专业的AI驱动分析报告"
