"""测试权重调整工具模块.

验证 weight_utils 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common.weight_utils import (
    adjust_weights_by_p_value,
    adjust_weights_by_auc,
    adjust_weights_by_correlation,
    adjust_weights_by_metric,
)


def test_adjust_weights_by_p_value():
    """测试根据p值调整权重."""
    print("测试 adjust_weights_by_p_value...")
    
    # 测试强显著性
    weights = {"stats_source": 1.0, "other_source": 1.0}
    adjust_weights_by_p_value(weights, 0.005)
    assert weights["stats_source"] == 1.3
    assert weights["other_source"] == 1.0
    
    # 测试弱显著性
    weights = {"stats_source": 1.0, "other_source": 1.0}
    adjust_weights_by_p_value(weights, 0.03)
    assert weights["stats_source"] == 1.1
    assert weights["other_source"] == 1.0
    
    # 测试不显著
    weights = {"stats_source": 1.0, "other_source": 1.0}
    adjust_weights_by_p_value(weights, 0.1)
    assert weights["stats_source"] == 1.0
    assert weights["other_source"] == 1.0
    
    print("  ✓ adjust_weights_by_p_value 测试通过")


def test_adjust_weights_by_auc():
    """测试根据AUC调整权重."""
    print("测试 adjust_weights_by_auc...")
    
    # 测试强AUC
    weights = {"model_source": 1.0, "other_source": 1.0}
    adjust_weights_by_auc(weights, 0.95)
    assert weights["model_source"] == 1.3
    assert weights["other_source"] == 1.0
    
    # 测试弱AUC
    weights = {"model_source": 1.0, "other_source": 1.0}
    adjust_weights_by_auc(weights, 0.85)
    assert weights["model_source"] == 1.1
    assert weights["other_source"] == 1.0
    
    # 测试低AUC
    weights = {"model_source": 1.0, "other_source": 1.0}
    adjust_weights_by_auc(weights, 0.7)
    assert weights["model_source"] == 1.0
    assert weights["other_source"] == 1.0
    
    print("  ✓ adjust_weights_by_auc 测试通过")


def test_adjust_weights_by_correlation():
    """测试根据相关系数调整权重."""
    print("测试 adjust_weights_by_correlation...")
    
    # 测试强相关
    weights = {"correlation_source": 1.0, "other_source": 1.0}
    adjust_weights_by_correlation(weights, 0.9)
    assert weights["correlation_source"] == 1.3
    assert weights["other_source"] == 1.0
    
    # 测试弱相关
    weights = {"correlation_source": 1.0, "other_source": 1.0}
    adjust_weights_by_correlation(weights, 0.7)
    assert weights["correlation_source"] == 1.1
    assert weights["other_source"] == 1.0
    
    # 测试低相关
    weights = {"correlation_source": 1.0, "other_source": 1.0}
    adjust_weights_by_correlation(weights, 0.5)
    assert weights["correlation_source"] == 1.0
    assert weights["other_source"] == 1.0
    
    print("  ✓ adjust_weights_by_correlation 测试通过")


def test_adjust_weights_by_metric():
    """测试通用权重调整函数."""
    print("测试 adjust_weights_by_metric...")
    
    # 测试 higher_is_better 模式
    weights = {"metric_source": 1.0, "other_source": 1.0}
    thresholds = [(0.9, 1.3), (0.8, 1.1)]
    adjust_weights_by_metric(weights, 0.95, "metric", "metric_source", thresholds, "higher_is_better")
    assert weights["metric_source"] == 1.3
    
    # 测试 lower_is_better 模式
    weights = {"metric_source": 1.0, "other_source": 1.0}
    thresholds = [(0.01, 1.3), (0.05, 1.1)]
    adjust_weights_by_metric(weights, 0.005, "metric", "metric_source", thresholds, "lower_is_better")
    assert weights["metric_source"] == 1.3
    
    print("  ✓ adjust_weights_by_metric 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试权重调整工具模块")
    print("=" * 60)
    
    tests = [
        test_adjust_weights_by_p_value,
        test_adjust_weights_by_auc,
        test_adjust_weights_by_correlation,
        test_adjust_weights_by_metric,
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
