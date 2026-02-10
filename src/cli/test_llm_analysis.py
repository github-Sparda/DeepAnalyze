#!/usr/bin/env python3
"""
测试LLM分析是否正确触发
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "cli"))

# 设置环境变量
os.environ['DEEPANALYZE_USE_ORCHESTRATOR'] = '1'
os.environ['DEEPANALYZE_MAX_DEPTH'] = '3'

# 重新导入配置
import importlib
sys.path.insert(0, str(project_root / "src"))
import api.config
importlib.reload(api.config)

from src.api.config import USE_ORCHESTRATOR, MAX_RECURSION_DEPTH

import pytest
try:
    from direct_cli import DirectDeepAnalyzeCLI
except ModuleNotFoundError:
    pytest.skip("Direct CLI dependencies not available (rich missing)", allow_module_level=True)

print("=== LLM分析测试 ===")
print(f"USE_ORCHESTRATOR: {USE_ORCHESTRATOR}")
print(f"MAX_RECURSION_DEPTH: {MAX_RECURSION_DEPTH}")

# 创建CLI实例
cli = DirectDeepAnalyzeCLI()

# 测试数据文件
test_file = "../../data/examples/simpson_paradox_analysis/data/Simpson.csv"
test_file_path = Path(test_file).resolve()

print(f"\n测试文件: {test_file_path}")
print(f"文件存在: {test_file_path.exists()}")

# 执行分析
print("\n开始分析...")
result = cli.analyze_data_direct(str(test_file_path), ["descriptive"])

print(f"\n分析结果: {type(result)}")
if result:
    print("分析成功完成!")
    if "orchestrated_analysis" in result:
        print("✅ 使用了LLM编排分析")
        print(f"分析计划: {result.get('plan', 'N/A')[:100]}...")
        print(f"分析结果: {result.get('docs/analysis_results', 'N/A')[:100]}...")
    else:
        print("⚠️  使用了传统统计分析")
else:
    print("❌ 分析失败")
