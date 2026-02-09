#!/usr/bin/env bash
#
# DeepAnalyze 一站式数据分析脚本
# 从数据加载到报告生成的完整流程

set -e

echo "🚀 DeepAnalyze 一站式数据分析"
echo "=============================="
echo ""

# 设置变量
DATA_FILE="../../data/examples/simpson_paradox_docs/analysis/data/Simpson.csv"
CLI_SCRIPT="direct_cli.py"

echo "📂 分析文件: $DATA_FILE"
echo "🔧 使用脚本: $CLI_SCRIPT"
echo ""

# 检查文件是否存在
if [ ! -f "$DATA_FILE" ]; then
    echo "❌ 数据文件不存在: $DATA_FILE"
    exit 1
fi

echo "✅ 开始完整分析流程..."
echo ""

# 一步完成所有分析
echo "📊 执行完整数据分析..."
python "$CLI_SCRIPT" --analyze "$DATA_FILE" \
    --docs/analysis-types descriptive inferential correlation quality \
    --report \
    --report-type analytical \
    --visualize

echo ""
echo "✅ 分析完成！"

echo ""
echo "📋 查看分析结果:"
python "$CLI_SCRIPT" --results

echo ""
echo "ℹ️  查看会话信息:"
python "$CLI_SCRIPT" --session-info

echo ""
echo "🎯 提示:"
echo "- 使用 --interactive 模式获得更多交互体验"
echo "- 分析结果保存在会话目录中"
echo "- 可以随时查询历史分析结果"