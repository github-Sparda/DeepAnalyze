"""测试验证工具模块.

验证 graph_utils/validation 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestration.graph_utils.validation import (
    infer_method_family,
    runtime_bound_validation_templates,
    canonical_hypothesis_identity,
    parse_result_hypothesis_identity,
    align_plan_json_to_runtime_hypotheses,
)


def test_infer_method_family():
    """测试推断方法家族."""
    print("测试 infer_method_family...")
    
    # 测试相关性分析
    assert infer_method_family("correlation analysis") == "correlation"
    assert infer_method_family("spearman test") == "correlation"
    assert infer_method_family("pearson coefficient") == "correlation"
    
    # 测试机器学习
    assert infer_method_family("random forest model") == "machine_learning"
    assert infer_method_family("neural network classifier") == "machine_learning"
    assert infer_method_family("svm prediction") == "machine_learning"
    
    # 测试嵌入分析
    assert infer_method_family("pca embedding") == "embedding"
    assert infer_method_family("tsne visualization") == "embedding"
    assert infer_method_family("umap cluster") == "embedding"
    
    # 测试生存分析
    assert infer_method_family("cox regression survival") == "survival"
    assert infer_method_family("kaplan-meier curve") == "survival"
    
    # 测试时间序列
    assert infer_method_family("time series arima") == "time_series"
    assert infer_method_family("seasonal trend analysis") == "time_series"
    
    # 测试因果推断
    assert infer_method_family("causal inference propensity") == "causal_inference"
    assert infer_method_family("instrumental variable matching") == "causal_inference"
    
    # 测试统计推断（默认）
    assert infer_method_family("t-test analysis") == "statistical_inference"
    assert infer_method_family("general statistics") == "statistical_inference"
    
    print("  ✓ infer_method_family 测试通过")


def test_runtime_bound_validation_templates():
    """测试运行时绑定验证模板."""
    print("测试 runtime_bound_validation_templates...")
    
    # 测试统计推断模板
    templates = runtime_bound_validation_templates("statistical_inference")
    assert len(templates) == 3
    assert any(t["profile_key"] == "statistical_significance" for t in templates)
    assert any(t["profile_key"] == "effect_size" for t in templates)
    
    # 测试相关性模板
    templates = runtime_bound_validation_templates("correlation")
    assert len(templates) == 3
    assert any(t["profile_key"] == "correlation_strength" for t in templates)
    
    # 测试机器学习模板
    templates = runtime_bound_validation_templates("machine_learning")
    assert len(templates) == 3
    assert any(t["profile_key"] == "model_performance" for t in templates)
    
    # 测试未知类型（应该返回默认模板）
    templates = runtime_bound_validation_templates("unknown_type")
    assert len(templates) >= 1
    
    print("  ✓ runtime_bound_validation_templates 测试通过")


def test_canonical_hypothesis_identity():
    """测试规范假设标识."""
    print("测试 canonical_hypothesis_identity...")
    
    # 测试正常情况
    hypothesis = {"id": "H1", "title": "Test Hypothesis"}
    identity = canonical_hypothesis_identity(hypothesis)
    assert "H1" in identity
    assert "Test Hypothesis" in identity
    
    # 测试缺少标题
    hypothesis = {"id": "H2"}
    identity = canonical_hypothesis_identity(hypothesis)
    assert "H2" in identity
    
    # 测试空字典
    hypothesis = {}
    identity = canonical_hypothesis_identity(hypothesis)
    assert identity == "" or "None" in identity
    
    print("  ✓ canonical_hypothesis_identity 测试通过")


def test_parse_result_hypothesis_identity():
    """测试解析结果假设标识."""
    print("测试 parse_result_hypothesis_identity...")
    
    # 测试正常情况（使用 title 字段）
    result = {"hypothesis_id": "H1", "title": "Test"}
    identity = parse_result_hypothesis_identity(result)
    assert "H1" in identity
    assert "Test" in identity
    
    # 测试使用 hypothesis 字段作为备选
    result = {"hypothesis_id": "H2", "hypothesis": "Test 2"}
    identity = parse_result_hypothesis_identity(result)
    assert "H2" in identity
    assert "Test 2" in identity
    
    # 测试空结果
    result = {}
    identity = parse_result_hypothesis_identity(result)
    assert identity == "" or "None" in identity
    
    print("  ✓ parse_result_hypothesis_identity 测试通过")


def test_align_plan_json_to_runtime_hypotheses():
    """测试对齐计划 JSON 到运行时假设."""
    print("测试 align_plan_json_to_runtime_hypotheses...")
    
    plan_json = {
        "hypotheses": [
            {"id": "H1", "title": "Test 1"},
            {"id": "H2", "title": "Test 2"},
        ]
    }
    
    runtime_results = {
        "H1": {"status": "success"},
        "H2": {"status": "failed"},
    }
    
    aligned = align_plan_json_to_runtime_hypotheses(plan_json, runtime_results)
    
    assert isinstance(aligned, dict)
    assert "aligned" in aligned or "hypotheses" in aligned
    
    # 测试空输入
    aligned = align_plan_json_to_runtime_hypotheses({}, {})
    assert isinstance(aligned, dict)
    
    print("  ✓ align_plan_json_to_runtime_hypotheses 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试验证工具模块")
    print("=" * 60)
    
    tests = [
        test_infer_method_family,
        test_runtime_bound_validation_templates,
        test_canonical_hypothesis_identity,
        test_parse_result_hypothesis_identity,
        test_align_plan_json_to_runtime_hypotheses,
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
