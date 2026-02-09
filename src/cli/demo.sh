#!/usr/bin/env bash
#
# DeepAnalyze CLI 演示脚本
# 展示两种CLI模式的使用方法

echo "🚀 DeepAnalyze CLI 模式演示"
echo "==========================="
echo ""

# 检查测试数据文件
if [ ! -f "test_data.csv" ]; then
    echo "❌ 未找到测试数据文件 test_data.csv"
    exit 1
fi

echo "📋 可用的CLI模式:"
echo "1. 统一CLI模式 - python unified_cli.py"
echo "2. src/api模式 - python api_cli.py (需要运行服务器)"
echo "3. 直接模式 - python direct_cli.py (无需服务器)"
echo ""

echo "🎯 直接模式演示:"
echo "---------------"

echo "1. 批处理数据分析:"
echo "   python direct_cli.py --analyze test_data.csv --results"
echo ""
python direct_cli.py --analyze test_data.csv --results

echo ""
echo "2. 生成可视化:"
echo "   python direct_cli.py --analyze test_data.csv --visualize"
echo ""
python direct_cli.py --analyze test_data.csv --visualize

echo ""
echo "3. 生成报告:"
echo "   python direct_cli.py --analyze test_data.csv --report"
echo ""
python direct_cli.py --analyze test_data.csv --report

echo ""
echo "4. 交互模式:"
echo "   python direct_cli.py --interactive"
echo "   (在交互模式中输入: analyze test_data.csv)"
echo "   (然后输入: viz 和 report)"

echo ""
echo "✅ 演示完成!"
echo ""
echo "💡 使用建议:"
echo "- 开发测试时使用直接模式，无需启动服务器"
echo "- 生产环境使用src/api模式，获得完整功能"
echo "- 统一模式便于切换和比较两种方式"