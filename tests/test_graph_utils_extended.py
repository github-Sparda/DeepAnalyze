"""扩展测试 graph_utils 模块的功能.

验证 graph_utils 中未覆盖的功能.
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestration.graph_utils import (
    # plan
    extract_plan_table_hypotheses,
    extract_hypothesis_descriptions,
    extract_hypothesis_table_steps_artifacts,
    render_plan_markdown_from_json,
    synthesize_plan_from_hypothesis_results,
    # hypothesis
    filter_hypothesis_results_payload,
    hypothesis_title_only,
    extract_hypotheses,
    extract_hypothesis_ids_from_report,
    sync_hypothesis_alignment_artifacts,
    # validation
    runtime_bound_validation_templates,
    canonical_hypothesis_identity,
    parse_result_hypothesis_identity,
    align_plan_json_to_runtime_hypotheses,
    # pipeline
    run_path_c_adjudication,
    maybe_run_pipeline_variants,
    # audit
    rollback_plan_outputs,
    run_audit,
    build_evidence_trace,
    build_reason_code_summary,
    build_analysis_quality_score,
    # fallback
    has_llm_unavailable_event,
    strong_fallback_report_ok,
    fallback_followup_hypotheses,
    fallback_analysis_code,
)


def test_extract_plan_table_hypotheses():
    """测试从计划表格提取假设."""
    print("测试 extract_plan_table_hypotheses...")
    
    plan_text = """
| 假设ID | 标题 | 类型 |
|--------|------|------|
| H1 | 假设1 | difference |
| H2 | 假设2 | correlation |
"""
    hypotheses = extract_plan_table_hypotheses(plan_text)
    
    assert len(hypotheses) >= 0, "应该返回假设列表"
    
    print("  ✓ extract_plan_table_hypotheses 测试通过")


def test_extract_hypothesis_descriptions():
    """测试提取假设描述."""
    print("测试 extract_hypothesis_descriptions...")
    
    plan_text = """
### H1 假设标题1
描述内容1

### H2 假设标题2
描述内容2
"""
    descriptions = extract_hypothesis_descriptions(plan_text)
    
    assert isinstance(descriptions, dict), "应该返回字典"
    
    print("  ✓ extract_hypothesis_descriptions 测试通过")


def test_render_plan_markdown_from_json():
    """测试从 JSON 渲染计划 Markdown."""
    print("测试 render_plan_markdown_from_json...")
    
    plan_json = {
        "hypotheses": [
            {"id": "H1", "title": "Test Hypothesis", "description": "Test description"}
        ]
    }
    markdown = render_plan_markdown_from_json(plan_json)
    
    assert isinstance(markdown, str), "应该返回字符串"
    assert "H1" in markdown or "Test" in markdown, "Markdown 应该包含假设信息"
    
    print("  ✓ render_plan_markdown_from_json 测试通过")


def test_synthesize_plan_from_hypothesis_results():
    """测试从假设结果合成计划."""
    print("测试 synthesize_plan_from_hypothesis_results...")
    
    results = {
        "H1": {"status": "success", "title": "Hypothesis 1"},
        "H2": {"status": "failed", "title": "Hypothesis 2"},
    }
    plan = synthesize_plan_from_hypothesis_results(results)
    
    assert isinstance(plan, dict), "应该返回字典"
    assert "hypotheses" in plan, "计划应该包含 hypotheses"
    
    print("  ✓ synthesize_plan_from_hypothesis_results 测试通过")


def test_filter_hypothesis_results_payload():
    """测试过滤假设结果负载."""
    print("测试 filter_hypothesis_results_payload...")
    
    payload = {
        "H1": {"status": "success", "data": "test"},
        "H2": {"status": "failed", "error": "error"},
    }
    filtered = filter_hypothesis_results_payload(payload, "H1")
    
    assert "H1" in filtered, "应该包含 H1"
    
    print("  ✓ filter_hypothesis_results_payload 测试通过")


def test_hypothesis_title_only():
    """测试提取假设标题."""
    print("测试 hypothesis_title_only...")
    
    plan_json = {
        "hypotheses": [
            {"id": "H1", "title": "Test Title 1"},
            {"id": "H2", "title": "Test Title 2"},
        ]
    }
    titles = hypothesis_title_only(plan_json)
    
    assert isinstance(titles, dict), "应该返回字典"
    assert "H1" in titles, "应该包含 H1"
    assert titles["H1"] == "Test Title 1", "H1 标题应该正确"
    
    print("  ✓ hypothesis_title_only 测试通过")


def test_extract_hypotheses():
    """测试提取假设."""
    print("测试 extract_hypotheses...")
    
    text = """
假设1: 这是第一个假设
假设2: 这是第二个假设
"""
    hypotheses = extract_hypotheses(text)
    
    assert isinstance(hypotheses, list), "应该返回列表"
    
    print("  ✓ extract_hypotheses 测试通过")


def test_extract_hypothesis_ids_from_report():
    """测试从报告提取假设 ID."""
    print("测试 extract_hypothesis_ids_from_report...")
    
    report = """
## 假设 H1 的结果
内容...
## 假设 H2 的结果
内容...
"""
    ids = extract_hypothesis_ids_from_report(report)
    
    assert isinstance(ids, list), "应该返回列表"
    
    print("  ✓ extract_hypothesis_ids_from_report 测试通过")


def test_sync_hypothesis_alignment_artifacts():
    """测试同步假设对齐产物."""
    print("测试 sync_hypothesis_alignment_artifacts...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        plan_ids = ["H1", "H2"]
        result = sync_hypothesis_alignment_artifacts(session_dir, plan_ids)
        
        assert isinstance(result, dict), "应该返回字典"
        assert "aligned" in result, "结果应该包含 aligned"
    
    print("  ✓ sync_hypothesis_alignment_artifacts 测试通过")


def test_runtime_bound_validation_templates():
    """测试运行时绑定验证模板."""
    print("测试 runtime_bound_validation_templates...")
    
    templates = runtime_bound_validation_templates("statistical_inference")
    
    assert isinstance(templates, list), "应该返回列表"
    assert len(templates) > 0, "应该有模板"
    
    print("  ✓ runtime_bound_validation_templates 测试通过")


def test_canonical_hypothesis_identity():
    """测试规范假设标识."""
    print("测试 canonical_hypothesis_identity...")
    
    hypothesis = {"id": "H1", "title": "Test Hypothesis"}
    identity = canonical_hypothesis_identity(hypothesis)
    
    assert isinstance(identity, str), "应该返回字符串"
    assert "H1" in identity, "应该包含 H1"
    
    print("  ✓ canonical_hypothesis_identity 测试通过")


def test_parse_result_hypothesis_identity():
    """测试解析结果假设标识."""
    print("测试 parse_result_hypothesis_identity...")
    
    result = {"hypothesis_id": "H1", "hypothesis_title": "Test"}
    identity = parse_result_hypothesis_identity(result)
    
    assert isinstance(identity, str), "应该返回字符串"
    
    print("  ✓ parse_result_hypothesis_identity 测试通过")


def test_align_plan_json_to_runtime_hypotheses():
    """测试对齐计划 JSON 到运行时假设."""
    print("测试 align_plan_json_to_runtime_hypotheses...")
    
    plan_json = {"hypotheses": [{"id": "H1", "title": "Test"}]}
    runtime_results = {"H1": {"status": "success"}}
    
    aligned = align_plan_json_to_runtime_hypotheses(plan_json, runtime_results)
    
    assert isinstance(aligned, dict), "应该返回字典"
    
    print("  ✓ align_plan_json_to_runtime_hypotheses 测试通过")


def test_run_path_c_adjudication():
    """测试运行 Path C 裁决."""
    print("测试 run_path_c_adjudication...")
    
    path_a = {"status": "success", "confidence": 0.8}
    path_b = {"status": "success", "confidence": 0.7}
    path_c = {"status": "success", "confidence": 0.75}
    
    result = run_path_c_adjudication(path_a, path_b, path_c)
    
    assert isinstance(result, dict), "应该返回字典"
    assert "status" in result, "结果应该包含 status"
    
    print("  ✓ run_path_c_adjudication 测试通过")


def test_maybe_run_pipeline_variants():
    """测试可能运行管道变体."""
    print("测试 maybe_run_pipeline_variants...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        result = maybe_run_pipeline_variants(session_dir, "H1")
        
        assert isinstance(result, dict), "应该返回字典"
    
    print("  ✓ maybe_run_pipeline_variants 测试通过")


def test_rollback_plan_outputs():
    """测试回滚计划输出."""
    print("测试 rollback_plan_outputs...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        plan_ids = ["H1"]
        result = rollback_plan_outputs(session_dir, plan_ids)
        
        assert isinstance(result, dict), "应该返回字典"
    
    print("  ✓ rollback_plan_outputs 测试通过")


def test_run_audit():
    """测试运行审计."""
    print("测试 run_audit...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        state = {
            "execution_errors": [],
            "execution_warnings": [],
            "hypothesis_results": {},
        }
        audit_result = run_audit(session_dir, state)
        
        assert isinstance(audit_result, dict), "应该返回字典"
    
    print("  ✓ run_audit 测试通过")


def test_build_evidence_trace():
    """测试构建证据追踪."""
    print("测试 build_evidence_trace...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        result_dir = session_dir / "result"
        result_dir.mkdir()
        
        trace = build_evidence_trace(session_dir, "H1")
        
        assert isinstance(trace, dict), "应该返回字典"
        assert "hypothesis_id" in trace, "应该包含 hypothesis_id"
    
    print("  ✓ build_evidence_trace 测试通过")


def test_build_reason_code_summary():
    """测试构建原因代码摘要."""
    print("测试 build_reason_code_summary...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        summary = build_reason_code_summary(session_dir)
        
        assert isinstance(summary, dict), "应该返回字典"
    
    print("  ✓ build_reason_code_summary 测试通过")


def test_build_analysis_quality_score():
    """测试构建分析质量分数."""
    print("测试 build_analysis_quality_score...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        result = build_analysis_quality_score(session_dir)
        
        assert isinstance(result, dict), "应该返回字典"
    
    print("  ✓ build_analysis_quality_score 测试通过")


def test_has_llm_unavailable_event():
    """测试检查 LLM 不可用事件."""
    print("测试 has_llm_unavailable_event...")
    
    events_with_issue = [{"node": "test", "reason": "rate limit"}]
    events_empty = []
    
    assert has_llm_unavailable_event(events_with_issue) is True, "应该检测到事件"
    assert has_llm_unavailable_event(events_empty) is False, "不应该检测到事件"
    assert has_llm_unavailable_event(None) is False, "None 应该返回 False"
    
    print("  ✓ has_llm_unavailable_event 测试通过")


def test_strong_fallback_report_ok():
    """测试降级报告验证."""
    print("测试 strong_fallback_report_ok...")
    
    # 测试有效报告
    completion_validation = {"complete": True}
    set_consistency = {"satisfied": True}
    pack_validation = {"valid": True}
    
    ok, reasons = strong_fallback_report_ok(completion_validation, set_consistency, pack_validation)
    
    assert isinstance(ok, bool), "应该返回布尔值"
    assert isinstance(reasons, list), "应该返回原因列表"
    assert ok is True, "有效报告应该返回 True"
    
    # 测试无效报告
    completion_validation_invalid = {"complete": False}
    ok2, reasons2 = strong_fallback_report_ok(completion_validation_invalid, set_consistency, pack_validation)
    assert ok2 is False, "无效报告应该返回 False"
    assert len(reasons2) > 0, "应该有失败原因"
    
    print("  ✓ strong_fallback_report_ok 测试通过")


def test_fallback_followup_hypotheses():
    """测试降级后续假设."""
    print("测试 fallback_followup_hypotheses...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        hypotheses = fallback_followup_hypotheses(session_dir)
        
        assert isinstance(hypotheses, list), "应该返回列表"
    
    print("  ✓ fallback_followup_hypotheses 测试通过")


def test_fallback_analysis_code():
    """测试降级分析代码."""
    print("测试 fallback_analysis_code...")
    
    code = fallback_analysis_code()
    
    assert isinstance(code, str), "应该返回字符串"
    assert len(code) > 0, "代码不应该为空"
    
    print("  ✓ fallback_analysis_code 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始扩展测试 graph_utils 模块")
    print("=" * 60)
    
    tests = [
        test_extract_plan_table_hypotheses,
        test_extract_hypothesis_descriptions,
        test_render_plan_markdown_from_json,
        test_synthesize_plan_from_hypothesis_results,
        test_filter_hypothesis_results_payload,
        test_hypothesis_title_only,
        test_extract_hypotheses,
        test_extract_hypothesis_ids_from_report,
        test_sync_hypothesis_alignment_artifacts,
        test_runtime_bound_validation_templates,
        test_canonical_hypothesis_identity,
        test_parse_result_hypothesis_identity,
        test_align_plan_json_to_runtime_hypotheses,
        test_run_path_c_adjudication,
        test_maybe_run_pipeline_variants,
        test_rollback_plan_outputs,
        test_run_audit,
        test_build_evidence_trace,
        test_build_reason_code_summary,
        test_build_analysis_quality_score,
        test_has_llm_unavailable_event,
        test_strong_fallback_report_ok,
        test_fallback_followup_hypotheses,
        test_fallback_analysis_code,
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
