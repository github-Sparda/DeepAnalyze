"""测试计划工具模块.

验证 graph_utils/plan 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestration.graph_utils.plan import (
    extract_hypothesis_table_steps_artifacts,
    normalize_plan_json,
    render_plan_markdown_from_json,
    synthesize_plan_from_hypothesis_results,
)


def test_extract_hypothesis_table_steps_artifacts():
    """测试提取假设步骤和产物."""
    print("测试 extract_hypothesis_table_steps_artifacts...")
    
    plan_text = """
### H1 假设标题1
1. 步骤1描述
2. 步骤2描述
- 输出: result1.json, result2.csv

### H2 假设标题2
1. 步骤A
- 输出: output.txt
"""
    
    steps_map, artifacts_map = extract_hypothesis_table_steps_artifacts(plan_text)
    
    assert "H1" in steps_map, "应该包含 H1"
    assert "H2" in steps_map, "应该包含 H2"
    assert len(steps_map["H1"]) == 2, "H1 应该有2个步骤"
    assert len(steps_map["H2"]) == 1, "H2 应该有1个步骤"
    assert len(artifacts_map["H1"]) == 2, "H1 应该有2个产物"
    assert len(artifacts_map["H2"]) == 1, "H2 应该有1个产物"
    
    print("  ✓ extract_hypothesis_table_steps_artifacts 测试通过")


def test_normalize_plan_json():
    """测试规范化计划 JSON."""
    print("测试 normalize_plan_json...")
    
    # 测试正常情况
    plan_json = {
        "hypotheses": [
            {"id": "H1", "title": "Test 1", "hypothesis_type": "difference"},
            {"id": "H2", "title": "Test 2", "hypothesis_type": "correlation"},
        ]
    }
    result = normalize_plan_json(plan_json)
    assert len(result["hypotheses"]) == 2
    assert result["hypotheses"][0]["id"] == "H1"
    
    # 测试空列表
    result = normalize_plan_json({"hypotheses": []})
    assert result["hypotheses"] == []
    
    # 测试非字典输入
    result = normalize_plan_json("invalid")
    assert result["hypotheses"] == []
    
    # 测试非列表 hypotheses
    result = normalize_plan_json({"hypotheses": "not_a_list"})
    assert result["hypotheses"] == []
    
    # 测试缺少 id 的假设
    plan_json = {"hypotheses": [{"title": "No ID"}]}
    result = normalize_plan_json(plan_json)
    assert len(result["hypotheses"]) == 0
    
    print("  ✓ normalize_plan_json 测试通过")


def test_render_plan_markdown_from_json():
    """测试从 JSON 渲染计划 Markdown."""
    print("测试 render_plan_markdown_from_json...")
    
    plan_json = {
        "hypotheses": [
            {
                "id": "H1",
                "title": "Test Hypothesis",
                "description": "Test description",
                "hypothesis_type": "difference"
            }
        ]
    }
    
    markdown = render_plan_markdown_from_json(plan_json)
    assert "H1" in markdown, "应该包含 H1"
    assert "Test Hypothesis" in markdown, "应该包含标题"
    assert "Test description" in markdown, "应该包含描述"
    
    # 测试空计划
    markdown = render_plan_markdown_from_json({"hypotheses": []})
    assert "# 分析计划" in markdown, "应该包含标题"  # 中文标题
    
    print("  ✓ render_plan_markdown_from_json 测试通过")


def test_synthesize_plan_from_hypothesis_results():
    """测试从假设结果合成计划."""
    print("测试 synthesize_plan_from_hypothesis_results...")
    
    # 函数期望的输入格式是 {"hypotheses": [...]}
    # 注意：只有 status == "rejected" 的假设会被过滤
    results = {
        "hypotheses": [
            {"hypothesis_id": "H1", "status": "success", "title": "Hypothesis 1"},
            {"hypothesis_id": "H2", "status": "rejected", "title": "Hypothesis 2"},
            {"hypothesis_id": "H3", "status": "failed", "title": "Hypothesis 3"},  # failed 不会被过滤
        ]
    }
    
    plan = synthesize_plan_from_hypothesis_results(results)
    
    assert "hypotheses" in plan, "应该包含 hypotheses"
    # 只有 rejected 会被过滤
    assert len(plan["hypotheses"]) == 2, "应该有2个假设（H1和H3）"
    ids = {h["id"] for h in plan["hypotheses"]}
    assert "H1" in ids
    assert "H3" in ids
    assert "H2" not in ids  # rejected 被过滤
    
    print("  ✓ synthesize_plan_from_hypothesis_results 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试计划工具模块")
    print("=" * 60)
    
    tests = [
        test_extract_hypothesis_table_steps_artifacts,
        test_normalize_plan_json,
        test_render_plan_markdown_from_json,
        test_synthesize_plan_from_hypothesis_results,
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
