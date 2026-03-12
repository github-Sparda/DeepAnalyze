"""测试 graph_utils 模块的功能.

验证 graph_utils 中的工具函数是否按预期执行.
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestration.graph_utils import (
    # json_utils
    extract_json_candidates,
    safe_json_any,
    safe_json_load,
    load_json_if_exists,
    # config
    load_analysis_runtime_config,
    # fallback
    is_llm_unavailable_error,
    record_llm_degradation,
    has_llm_unavailable_event,
    strong_fallback_plan_ok,
    strong_fallback_report_ok,
    fallback_followup_hypotheses,
    fallback_report_outline,
    fallback_analysis_code,
    # plan
    parse_plan_markdown,
    extract_plan_table_hypotheses,
    extract_hypothesis_descriptions,
    extract_hypothesis_table_steps_artifacts,
    normalize_plan_json,
    render_plan_markdown_from_json,
    synthesize_plan_from_hypothesis_results,
    # hypothesis
    extract_hypothesis_id_from_label,
    active_hypothesis_ids_from_plan,
    filter_hypothesis_results_payload,
    hypothesis_title_only,
    extract_hypotheses,
    extract_hypothesis_ids_from_report,
    sync_hypothesis_alignment_artifacts,
    # validation
    infer_method_family,
    runtime_bound_validation_templates,
    canonical_hypothesis_identity,
    parse_result_hypothesis_identity,
    align_plan_json_to_runtime_hypotheses,
    default_validation_paths,
    merge_validation_paths,
    # pipeline
    variant_method_family,
    pick_path_c_variant,
    status_vote,
    run_path_c_adjudication,
    maybe_run_pipeline_variants,
    # audit
    telemetry_context,
    cleanup_dir_contents,
    rollback_plan_outputs,
    run_audit,
    build_evidence_trace,
    build_reason_code_summary,
    build_analysis_quality_score,
    quality_consistency_errors,
    build_completion_validation,
)


def test_extract_json_candidates():
    """测试 JSON 候选提取功能."""
    print("测试 extract_json_candidates...")
    
    # 测试代码块中的 JSON
    text_with_code = '''
    ```json
    {"key": "value", "number": 123}
    ```
    '''
    candidates = extract_json_candidates(text_with_code)
    assert len(candidates) > 0, "应该提取到 JSON 候选"
    
    # 测试普通 JSON 对象
    text_with_json = '前缀 {"name": "test"} 后缀'
    candidates = extract_json_candidates(text_with_json)
    assert '{"name": "test"}' in candidates, "应该提取普通 JSON 对象"
    
    print("  ✓ extract_json_candidates 测试通过")


def test_safe_json_any():
    """测试安全 JSON 解析功能."""
    print("测试 safe_json_any...")
    
    # 测试正常 JSON
    result = safe_json_any('{"key": "value"}')
    assert result == {"key": "value"}, "应该正确解析 JSON"
    
    # 测试无效 JSON
    result = safe_json_any("不是 JSON")
    assert result == {}, "无效 JSON 应该返回空字典"
    
    print("  ✓ safe_json_any 测试通过")


def test_safe_json_load():
    """测试安全 JSON 加载功能."""
    print("测试 safe_json_load...")
    
    # 测试正常 JSON
    result = safe_json_load('{"key": "value"}')
    assert result == {"key": "value"}, "应该正确加载 JSON"
    
    # 测试数组 JSON（应该返回空字典）
    result = safe_json_load('[1, 2, 3]')
    assert result == {}, "数组 JSON 应该返回空字典"
    
    print("  ✓ safe_json_load 测试通过")


def test_load_json_if_exists():
    """测试条件 JSON 加载功能."""
    print("测试 load_json_if_exists...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"
        test_file.write_text('{"key": "value"}', encoding="utf-8")
        
        # 测试存在的文件
        result = load_json_if_exists(test_file)
        assert result == {"key": "value"}, "应该加载存在的文件"
        
        # 测试不存在的文件
        result = load_json_if_exists(Path(tmpdir) / "not_exist.json")
        assert result == {}, "不存在的文件应该返回空字典"
    
    print("  ✓ load_json_if_exists 测试通过")


def test_load_analysis_runtime_config():
    """测试分析运行时配置加载功能."""
    print("测试 load_analysis_runtime_config...")
    
    # 测试默认配置
    config = load_analysis_runtime_config()
    assert "required_result_artifacts" in config, "应该包含必需的产物列表"
    assert isinstance(config["required_result_artifacts"], list), "产物列表应该是列表"
    
    print("  ✓ load_analysis_runtime_config 测试通过")


def test_is_llm_unavailable_error():
    """测试 LLM 不可用错误检测功能."""
    print("测试 is_llm_unavailable_error...")
    
    # 测试 rate limit 错误
    assert is_llm_unavailable_error("rate limit exceeded") is True, "应该检测到 rate limit 错误"
    
    # 测试正常错误
    assert is_llm_unavailable_error("some other error") is False, "不应该检测到正常错误"
    
    print("  ✓ is_llm_unavailable_error 测试通过")


def test_record_llm_degradation():
    """测试 LLM 降级记录功能."""
    print("测试 record_llm_degradation...")
    
    state = {"llm_degradation_events": []}
    events = record_llm_degradation(state, "test_node", "retry", "rate limit", "delayed")
    
    assert len(events) == 1, "应该记录一个事件"
    assert events[0]["node"] == "test_node", "事件应该包含节点名称"
    
    print("  ✓ record_llm_degradation 测试通过")


def test_strong_fallback_plan_ok():
    """测试降级计划验证功能."""
    print("测试 strong_fallback_plan_ok...")
    
    # 测试有效计划
    valid_plan = {
        "hypotheses": [
            {"id": "H1", "title": "Test 1", "hypothesis_type": "difference", "steps": ["step1"], "validation_paths": [{}, {}]},
            {"id": "H2", "title": "Test 2", "hypothesis_type": "difference", "steps": ["step1"], "validation_paths": [{}, {}]},
            {"id": "H3", "title": "Test 3", "hypothesis_type": "difference", "steps": ["step1"], "validation_paths": [{}, {}]},
        ]
    }
    ok, reason = strong_fallback_plan_ok(valid_plan)
    assert ok is True, "有效计划应该通过验证"
    
    # 测试无效计划（假设数量不足）
    invalid_plan = {"hypotheses": [{"id": "H1", "title": "Test 1"}]}
    ok, reason = strong_fallback_plan_ok(invalid_plan)
    assert ok is False, "无效计划不应该通过验证"
    
    print("  ✓ strong_fallback_plan_ok 测试通过")


def test_fallback_report_outline():
    """测试降级报告大纲生成功能."""
    print("测试 fallback_report_outline...")
    
    state = {
        "plan_json": {
            "hypotheses": [
                {"id": "H1", "title": "Test Hypothesis"},
            ]
        }
    }
    outline = fallback_report_outline(state)
    
    assert "# 报告大纲" in outline, "大纲应该包含标题"
    assert "H1" in outline, "大纲应该包含假设 ID"
    
    print("  ✓ fallback_report_outline 测试通过")


def test_parse_plan_markdown():
    """测试计划 Markdown 解析功能."""
    print("测试 parse_plan_markdown...")
    
    plan_text = """### H1 假设1
1. 步骤1
2. 步骤2
- 输出: result.json

### H2 假设2
1. 步骤A
"""
    result = parse_plan_markdown(plan_text)
    
    assert "hypotheses" in result, "结果应该包含 hypotheses"
    assert len(result["hypotheses"]) == 2, "应该解析出 2 个假设"
    
    print("  ✓ parse_plan_markdown 测试通过")


def test_normalize_plan_json():
    """测试计划 JSON 规范化功能."""
    print("测试 normalize_plan_json...")
    
    plan = {
        "hypotheses": [
            {"id": "H1", "title": "Test", "hypothesis_type": "difference"},
        ]
    }
    normalized = normalize_plan_json(plan)
    
    assert "hypotheses" in normalized, "规范化结果应该包含 hypotheses"
    assert len(normalized["hypotheses"]) == 1, "应该有一个假设"
    assert "steps" in normalized["hypotheses"][0], "假设应该包含 steps"
    
    print("  ✓ normalize_plan_json 测试通过")


def test_extract_hypothesis_id_from_label():
    """测试假设 ID 提取功能."""
    print("测试 extract_hypothesis_id_from_label...")
    
    # 测试正常情况
    hid = extract_hypothesis_id_from_label("H1 假设标题")
    assert hid == "H1", "应该提取 H1"
    
    # 测试小写
    hid = extract_hypothesis_id_from_label("h2 假设标题")
    assert hid == "H2", "应该提取 H2 并转为大写"
    
    # 测试无 ID
    hid = extract_hypothesis_id_from_label("没有 ID")
    assert hid == "", "没有 ID 应该返回空字符串"
    
    print("  ✓ extract_hypothesis_id_from_label 测试通过")


def test_active_hypothesis_ids_from_plan():
    """测试活跃假设 ID 提取功能."""
    print("测试 active_hypothesis_ids_from_plan...")
    
    plan = {
        "hypotheses": [
            {"id": "H1", "title": "Test 1"},
            {"id": "H2", "title": "Test 2"},
        ]
    }
    ids = active_hypothesis_ids_from_plan(plan)
    
    assert "H1" in ids, "应该包含 H1"
    assert "H2" in ids, "应该包含 H2"
    
    print("  ✓ active_hypothesis_ids_from_plan 测试通过")


def test_infer_method_family():
    """测试方法家族推断功能."""
    print("测试 infer_method_family...")
    
    # 测试统计推断
    family = infer_method_family("使用 t-test 进行分析")
    assert family == "statistical_inference", "应该识别为统计推断"
    
    # 测试机器学习
    family = infer_method_family("使用 random forest 进行分类")
    assert family == "machine_learning", "应该识别为机器学习"
    
    # 测试相关性
    family = infer_method_family("计算 pearson 相关系数")
    assert family == "correlation", "应该识别为相关性分析"
    
    print("  ✓ infer_method_family 测试通过")


def test_default_validation_paths():
    """测试默认验证路径获取功能."""
    print("测试 default_validation_paths...")
    
    paths = default_validation_paths("difference")
    assert len(paths) > 0, "应该有验证路径"
    assert "path" in paths[0], "路径应该包含 path 字段"
    
    print("  ✓ default_validation_paths 测试通过")


def test_merge_validation_paths():
    """测试验证路径合并功能."""
    print("测试 merge_validation_paths...")
    
    base = [{"path": "path_a", "priority": 1, "method": "method_a"}]
    override = [{"path": "path_a", "method": "method_b"}]
    
    merged = merge_validation_paths(base, override)
    
    assert len(merged) == 1, "应该有一个路径"
    assert merged[0]["method"] == "method_b", "方法应该被覆盖"
    
    print("  ✓ merge_validation_paths 测试通过")


def test_variant_method_family():
    """测试变体方法家族获取功能."""
    print("测试 variant_method_family...")
    
    family = variant_method_family("path_a")
    assert family == "statistical_inference", "path_a 应该是统计推断"
    
    family = variant_method_family("path_b")
    assert family == "machine_learning", "path_b 应该是机器学习"
    
    print("  ✓ variant_method_family 测试通过")


def test_status_vote():
    """测试状态投票功能."""
    print("测试 status_vote...")
    
    results = [
        {"status": "success"},
        {"status": "success"},
        {"status": "failed"},
    ]
    vote = status_vote(results)
    
    assert vote["status"] == "success", "success 应该获胜"
    assert vote["confidence"] > 0.5, "置信度应该大于 0.5"
    
    print("  ✓ status_vote 测试通过")


def test_pick_path_c_variant():
    """测试 Path C 变体选择功能."""
    print("测试 pick_path_c_variant...")
    
    # 测试需要 Path C 的情况（效应方向冲突）
    path_a = {"status": "success", "confidence": 0.8, "effect_size": 0.5}
    path_b = {"status": "success", "confidence": 0.8, "effect_size": -0.5}
    
    result = pick_path_c_variant(path_a, path_b)
    assert result["need_path_c"] is True, "应该需要 Path C"
    
    # 测试不需要 Path C 的情况
    path_a = {"status": "success", "confidence": 0.9, "effect_size": 0.5}
    path_b = {"status": "success", "confidence": 0.7, "effect_size": 0.4}
    
    result = pick_path_c_variant(path_a, path_b)
    assert result["need_path_c"] is False, "不应该需要 Path C"
    
    print("  ✓ pick_path_c_variant 测试通过")


def test_telemetry_context():
    """测试遥测上下文生成功能."""
    print("测试 telemetry_context...")
    
    state = {"depth": 2, "iteration_count": 5, "session_id": "test_session"}
    context = telemetry_context("test_node", state)
    
    assert context["node"] == "test_node", "应该包含节点名称"
    assert context["depth"] == 2, "应该包含深度"
    assert "timestamp" in context, "应该包含时间戳"
    
    print("  ✓ telemetry_context 测试通过")


def test_cleanup_dir_contents():
    """测试目录内容清理功能."""
    print("测试 cleanup_dir_contents...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test"
        test_dir.mkdir()
        
        # 创建测试文件
        (test_dir / "file1.txt").write_text("test")
        (test_dir / "file2.txt").write_text("test")
        
        # 清理
        deleted = cleanup_dir_contents(test_dir, keep_files=["file1.txt"])
        
        assert deleted == 1, "应该删除 1 个文件"
        assert (test_dir / "file1.txt").exists(), "保留的文件应该存在"
        assert not (test_dir / "file2.txt").exists(), "删除的文件应该不存在"
    
    print("  ✓ cleanup_dir_contents 测试通过")


def test_quality_consistency_errors():
    """测试质量一致性错误检查功能."""
    print("测试 quality_consistency_errors...")
    
    # 测试无错误
    state = {"execution_errors": []}
    errors = quality_consistency_errors(state)
    assert len(errors) == 0, "应该没有错误"
    
    # 测试有错误
    state = {"execution_errors": ["error1", "error2"], "execution_retry_exhausted": True}
    errors = quality_consistency_errors(state)
    assert len(errors) == 3, "应该有 3 个错误"
    
    print("  ✓ quality_consistency_errors 测试通过")


def test_build_completion_validation():
    """测试完成态验证构建功能."""
    print("测试 build_completion_validation...")
    
    # 测试完整状态（使用非空值）
    state = {
        "plan_json": {"hypotheses": []},
        "hypothesis_results": {"H1": {}},
        "hypothesis_evidence": {"H1": []},
    }
    result = build_completion_validation(state)
    assert result["complete"] is True, "完整状态应该返回 complete=True"
    
    # 测试缺少字段
    state = {"plan_json": {"hypotheses": []}}
    result = build_completion_validation(state)
    assert result["complete"] is False, "缺少字段应该返回 complete=False"
    
    print("  ✓ build_completion_validation 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试 graph_utils 模块")
    print("=" * 60)
    
    tests = [
        test_extract_json_candidates,
        test_safe_json_any,
        test_safe_json_load,
        test_load_json_if_exists,
        test_load_analysis_runtime_config,
        test_is_llm_unavailable_error,
        test_record_llm_degradation,
        test_strong_fallback_plan_ok,
        test_fallback_report_outline,
        test_parse_plan_markdown,
        test_normalize_plan_json,
        test_extract_hypothesis_id_from_label,
        test_active_hypothesis_ids_from_plan,
        test_infer_method_family,
        test_default_validation_paths,
        test_merge_validation_paths,
        test_variant_method_family,
        test_status_vote,
        test_pick_path_c_variant,
        test_telemetry_context,
        test_cleanup_dir_contents,
        test_quality_consistency_errors,
        test_build_completion_validation,
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
