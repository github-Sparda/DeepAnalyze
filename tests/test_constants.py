"""测试常量模块.

验证 constants 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common import (
    ANALYTICS_TOOLKIT_MODULES,
    MODEL_OUTPUT_FILES,
    STATS_OUTPUT_FILES,
    HYPOTHESIS_TYPE_MAP,
    METHOD_FAMILY_KEYWORDS,
)


def test_analytics_toolkit_modules():
    """测试分析工具包模块列表."""
    print("测试 ANALYTICS_TOOLKIT_MODULES...")
    
    assert isinstance(ANALYTICS_TOOLKIT_MODULES, list)
    assert "data_profile" in ANALYTICS_TOOLKIT_MODULES
    assert "data_quality" in ANALYTICS_TOOLKIT_MODULES
    assert "stats_tests" in ANALYTICS_TOOLKIT_MODULES
    assert "correlation" in ANALYTICS_TOOLKIT_MODULES
    assert "feature_selection" in ANALYTICS_TOOLKIT_MODULES
    
    print("  ✓ ANALYTICS_TOOLKIT_MODULES 测试通过")


def test_model_output_files():
    """测试模型输出文件列表."""
    print("测试 MODEL_OUTPUT_FILES...")
    
    assert isinstance(MODEL_OUTPUT_FILES, list)
    assert "model_results.json" in MODEL_OUTPUT_FILES
    assert "roc_curve.png" in MODEL_OUTPUT_FILES
    assert "pr_curve.png" in MODEL_OUTPUT_FILES
    
    print("  ✓ MODEL_OUTPUT_FILES 测试通过")


def test_stats_output_files():
    """测试统计输出文件列表."""
    print("测试 STATS_OUTPUT_FILES...")
    
    assert isinstance(STATS_OUTPUT_FILES, list)
    assert "stats_results.json" in STATS_OUTPUT_FILES
    assert "top_features.json" in STATS_OUTPUT_FILES
    
    print("  ✓ STATS_OUTPUT_FILES 测试通过")


def test_hypothesis_type_map():
    """测试假设类型映射."""
    print("测试 HYPOTHESIS_TYPE_MAP...")
    
    assert isinstance(HYPOTHESIS_TYPE_MAP, dict)
    assert "difference" in HYPOTHESIS_TYPE_MAP
    assert "correlation" in HYPOTHESIS_TYPE_MAP
    assert "causal" in HYPOTHESIS_TYPE_MAP
    
    # 验证值是列表
    for key, value in HYPOTHESIS_TYPE_MAP.items():
        assert isinstance(value, list)
        assert len(value) > 0
    
    print("  ✓ HYPOTHESIS_TYPE_MAP 测试通过")


def test_method_family_keywords():
    """测试方法家族关键词."""
    print("测试 METHOD_FAMILY_KEYWORDS...")
    
    assert isinstance(METHOD_FAMILY_KEYWORDS, dict)
    assert "correlation" in METHOD_FAMILY_KEYWORDS
    assert "machine_learning" in METHOD_FAMILY_KEYWORDS
    assert "statistical_inference" in METHOD_FAMILY_KEYWORDS
    
    # 验证值是列表
    for key, value in METHOD_FAMILY_KEYWORDS.items():
        assert isinstance(value, list)
        assert len(value) > 0
    
    print("  ✓ METHOD_FAMILY_KEYWORDS 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试常量模块")
    print("=" * 60)
    
    tests = [
        test_analytics_toolkit_modules,
        test_model_output_files,
        test_stats_output_files,
        test_hypothesis_type_map,
        test_method_family_keywords,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
