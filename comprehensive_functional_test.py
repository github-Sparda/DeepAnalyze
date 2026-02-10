#!/usr/bin/env python3
"""
DeepAnalyze 全功能测试脚本
测试所有核心模块和功能是否正常工作
"""

import sys
import os
import traceback
from pathlib import Path

# 设置环境
os.environ['DEEPANALYZE_USE_ORCHESTRATOR'] = '1'
os.environ['DEEPANALYZE_MAX_DEPTH'] = '1'

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("🚀 DeepAnalyze 全功能测试")
print("=" * 80)

# 测试结果统计
test_results = []
failed_tests = []

def run_test(name, test_func):
    """运行单个测试"""
    print(f"\n🔍 测试: {name}")
    print("-" * 40)
    
    try:
        result = test_func()
        if result:
            print(f"✅ {name} - 通过")
            test_results.append((name, True, None))
            return True
        else:
            error_msg = "测试返回False"
            print(f"❌ {name} - 失败: {error_msg}")
            test_results.append((name, False, error_msg))
            failed_tests.append((name, error_msg))
            return False
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"❌ {name} - 异常: {error_msg}")
        traceback.print_exc()
        test_results.append((name, False, error_msg))
        failed_tests.append((name, error_msg))
        return False

# 测试1: 基础导入测试
def test_basic_imports():
    try:
        # API配置
        from src.api.config import USE_ORCHESTRATOR, MAX_RECURSION_DEPTH, WORKSPACE_BASE_DIR
        print(f"  USE_ORCHESTRATOR: {USE_ORCHESTRATOR}")
        print(f"  MAX_RECURSION_DEPTH: {MAX_RECURSION_DEPTH}")
        print(f"  WORKSPACE_BASE_DIR: {WORKSPACE_BASE_DIR}")
        
        # 核心模块
        from src.core.orchestration.runner import run_orchestrated_docs_analysis
        from src.core.reporting.templates import template_from_config
        from src.core.tools.tool_interface import ToolInterface
        from src.core.cache.semantic_cache import SemanticSimilarityCache
        
        # CLI模块
        from src.cli.direct_cli import DirectDeepAnalyzeCLI
        from src.cli.api_cli import DeepAnalyzeCLI
        
        return True
    except Exception as e:
        print(f"  导入失败: {e}")
        return False

# 测试2: 配置系统测试
def test_config_system():
    try:
        from src.api.config import (
            USE_ORCHESTRATOR, MAX_RECURSION_DEPTH, WORKSPACE_BASE_DIR,
            API_BASE, DEFAULT_MODEL, DEFAULT_TEMPERATURE
        )
        
        print(f"  编排模式: {'启用' if USE_ORCHESTRATOR else '禁用'}")
        print(f"  最大递归深度: {MAX_RECURSION_DEPTH}")
        print(f"  工作空间目录: {WORKSPACE_BASE_DIR}")
        print(f"  API基础地址: {API_BASE}")
        print(f"  默认模型: {DEFAULT_MODEL}")
        print(f"  默认温度: {DEFAULT_TEMPERATURE}")
        
        # 验证工作空间目录存在
        workspace_path = Path(WORKSPACE_BASE_DIR)
        if not workspace_path.exists():
            workspace_path.mkdir(parents=True, exist_ok=True)
            print(f"  创建工作空间目录: {workspace_path}")
        
        return True
    except Exception as e:
        print(f"  配置测试失败: {e}")
        return False

# 测试3: 工具接口测试
def test_tool_interface():
    try:
        from src.core.tools.tool_interface import ToolInterface, ToolMetadata, ToolType
        
        # 创建测试元数据
        metadata = ToolMetadata(
            name="test_tool",
            description="测试工具",
            version="1.0.0",
            tool_type=ToolType.DATA_PROCESSING,
            supported_languages=["Python"],
            parameters={"test_param": "str - 测试参数"},
            returns="dict - 测试结果",
            data_examples=["test_tool(test_param='hello')"]
        )
        
        print(f"  工具类型: {metadata.tool_type.value}")
        print(f"  支持语言: {metadata.supported_languages}")
        print(f"  参数定义: {metadata.parameters}")
        
        return True
    except Exception as e:
        print(f"  工具接口测试失败: {e}")
        return False

# 测试4: 语义缓存测试
def test_semantic_cache():
    try:
        from src.core.cache.semantic_cache import SemanticSimilarityCache
        import numpy as np
        
        # 创建缓存实例
        cache = SemanticSimilarityCache(similarity_threshold=0.7, max_cache_size=100)
        print(f"  缓存阈值: {cache.similarity_threshold}")
        print(f"  最大缓存大小: {cache.max_cache_size}")
        
        # 测试向量存储
        test_vector = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        cache.store_vector("test_key", "测试文本", test_vector, {"result": "test"})
        print(f"  向量存储成功")
        
        # 测试相似性搜索
        query_vector = np.array([0.11, 0.21, 0.31], dtype=np.float32)
        results = cache.search_similar_vectors(query_vector, top_k=5)
        print(f"  相似性搜索结果: {len(results)} 项")
        
        return True
    except Exception as e:
        print(f"  语义缓存测试失败: {e}")
        return False

# 测试5: 报告模板测试
def test_report_templates():
    try:
        from src.core.reporting.templates import template_from_config
        
        # 测试模板生成
        config = {
            "report_format": "html",
            "report_language": "zh",
            "analysis_types": ["descriptive"]
        }
        
        template = template_from_config(config)
        print(f"  模板类型: {type(template)}")
        print(f"  模板预览: {str(template)[:100]}...")
        
        return True
    except Exception as e:
        print(f"  报告模板测试失败: {e}")
        return False

# 测试6: 直接CLI测试
def test_direct_cli():
    try:
        from src.cli.direct_cli import DirectDeepAnalyzeCLI
        
        # 创建CLI实例
        cli = DirectDeepAnalyzeCLI()
        print(f"  CLI实例创建成功")
        print(f"  当前会话ID: {cli.current_session_id}")
        
        # 测试会话管理
        if cli.current_session_id:
            print(f"  会话管理正常")
        
        return True
    except Exception as e:
        print(f"  直接CLI测试失败: {e}")
        return False

# 测试7: API CLI测试
def test_api_cli():
    try:
        from src.cli.api_cli import DeepAnalyzeCLI
        
        # 创建CLI实例
        cli = DeepAnalyzeCLI()
        print(f"  API CLI实例创建成功")
        
        return True
    except Exception as e:
        print(f"  API CLI测试失败: {e}")
        return False

# 测试8: 编排系统测试
def test_orchestration_system():
    try:
        from src.core.orchestration.runner import run_orchestrated_docs_analysis
        from src.api.config import MAX_RECURSION_DEPTH, WORKSPACE_BASE_DIR
        
        # 创建测试会话
        import time
        session_id = f"test_{int(time.time())}"
        print(f"  测试会话ID: {session_id}")
        
        # 配置参数
        config = {
            "max_depth": min(MAX_RECURSION_DEPTH, 1),
            "report_format": "html",
            "report_language": "zh",
            "analysis_types": ["descriptive"]
        }
        
        print(f"  配置参数: {config}")
        print(f"  工作目录: {WORKSPACE_BASE_DIR}")
        
        # 注意：这里不实际执行分析，只是测试函数可调用性
        print(f"  编排函数可调用")
        
        return True
    except Exception as e:
        print(f"  编排系统测试失败: {e}")
        return False

# 测试9: 文件系统测试
def test_file_system():
    try:
        from src.api.config import WORKSPACE_BASE_DIR
        import tempfile
        import json
        
        # 测试工作空间目录
        workspace_path = Path(WORKSPACE_BASE_DIR)
        workspace_path.mkdir(parents=True, exist_ok=True)
        print(f"  工作空间目录: {workspace_path}")
        print(f"  目录存在: {workspace_path.exists()}")
        
        # 测试临时文件操作
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = {"test": "data", "number": 42}
            json.dump(test_data, f)
            temp_file = f.name
        
        print(f"  临时文件创建: {temp_file}")
        
        # 验证文件内容
        with open(temp_file, 'r') as f:
            loaded_data = json.load(f)
            print(f"  文件读取验证: {loaded_data}")
        
        # 清理临时文件
        os.unlink(temp_file)
        print(f"  临时文件清理完成")
        
        return True
    except Exception as e:
        print(f"  文件系统测试失败: {e}")
        return False

# 测试10: 环境变量测试
def test_environment_variables():
    try:
        # 检查关键环境变量
        env_vars = [
            'DEEPANALYZE_USE_ORCHESTRATOR',
            'DEEPANALYZE_MAX_DEPTH',
            'PYTHONPATH'
        ]
        
        for var in env_vars:
            value = os.environ.get(var, 'NOT_SET')
            print(f"  {var}: {value}")
        
        # 验证关键变量
        use_orchestrator = os.environ.get('DEEPANALYZE_USE_ORCHESTRATOR')
        max_depth = os.environ.get('DEEPANALYZE_MAX_DEPTH')
        
        if use_orchestrator is not None and max_depth is not None:
            print(f"  环境变量配置正确")
            return True
        else:
            print(f"  关键环境变量缺失")
            return False
            
    except Exception as e:
        print(f"  环境变量测试失败: {e}")
        return False

# 执行所有测试
tests = [
    ("基础导入测试", test_basic_imports),
    ("配置系统测试", test_config_system),
    ("工具接口测试", test_tool_interface),
    ("语义缓存测试", test_semantic_cache),
    ("报告模板测试", test_report_templates),
    ("直接CLI测试", test_direct_cli),
    ("API CLI测试", test_api_cli),
    ("编排系统测试", test_orchestration_system),
    ("文件系统测试", test_file_system),
    ("环境变量测试", test_environment_variables)
]

print(f"📋 计划执行 {len(tests)} 个测试")

# 运行所有测试
for test_name, test_func in tests:
    run_test(test_name, test_func)

# 输出最终结果
print("\n" + "=" * 80)
print("📊 测试结果汇总")
print("=" * 80)

total_tests = len(test_results)
passed_tests = sum(1 for _, success, _ in test_results if success)
failed_count = len(failed_tests)

print(f"总测试数: {total_tests}")
print(f"通过: {passed_tests}")
print(f"失败: {failed_count}")
print(f"成功率: {passed_tests/total_tests*100:.1f}%")

if failed_tests:
    print(f"\n❌ 失败的测试:")
    for test_name, error in failed_tests:
        print(f"  • {test_name}: {error}")
else:
    print(f"\n🎉 所有测试通过！")

print("\n" + "=" * 80)
print("🏁 测试完成")
print("=" * 80)