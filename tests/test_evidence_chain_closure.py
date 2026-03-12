from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.orchestration.closure import evaluate_phase_closure, closure_completion_summary, load_phase_closure_map
from src.core.orchestration.depth_research import build_research_digest, select_depth_focus, build_depth_delta
from src.core.orchestration.hypothesis_engine import _build_hypothesis_evidence, _build_hypothesis_contrast


def test_evidence_chain_completeness():
    """测试证据链的完整性"""
    # 创建临时会话目录
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # 创建必要的目录结构
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        (session_dir / "plots").mkdir(parents=True, exist_ok=True)
        
        # 创建基本的分析计划
        plan_json = {
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "差异检验",
                    "hypothesis": "组间存在显著差异标志物",
                    "validation_paths": ["path_a", "path_b"]
                },
                {
                    "id": "H2",
                    "title": "预测模型",
                    "hypothesis": "多特征组合具备诊断预测力",
                    "validation_paths": ["path_a", "path_b"]
                },
                {
                    "id": "H3",
                    "title": "相关性分析",
                    "hypothesis": "变量间存在结构化相关网络",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        
        # 写入分析计划
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 写入分析计划Markdown文件
        (session_dir / "plan" / "analysis_plan.md").write_text(
            "# 分析计划\n\n### 1. 假设列表\n\n#### 假设 1：差异检验\n- 验证路径 A：统计检验\n- 验证路径 B：多重校正\n\n#### 假设 2：预测模型\n- 验证路径 A：模型训练\n- 验证路径 B：交叉验证\n\n#### 假设 3：相关性分析\n- 验证路径 A：相关性计算\n- 验证路径 B：网络分析\n\n### 2. 详细分析步骤\n- 数据预处理\n- 统计检验\n- 特征选择\n- 模型训练\n- 模型评估\n- 相关性分析\n- 可视化生成\n- 报告生成\n",
            encoding="utf-8"
        )
        
        # 创建基本的结果文件
        stats_results = [
            {"feature": "feature1", "p_value": 0.01, "mean_diff": 1.5},
            {"feature": "feature2", "p_value": 0.03, "mean_diff": 0.8}
        ]
        (session_dir / "result" / "stats_results.json").write_text(
            json.dumps(stats_results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        model_eval = {
            "metrics": {
                "auc": 0.85,
                "accuracy": 0.80
            }
        }
        (session_dir / "result" / "model_eval.json").write_text(
            json.dumps(model_eval, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        correlation = {
            "feature1": {"feature2": 0.75},
            "feature2": {"feature1": 0.75}
        }
        (session_dir / "result" / "correlation.json").write_text(
            json.dumps(correlation, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试证据构建
        hypothesis_payload = {
            "hypotheses": [
                {
                    "hypothesis": "H1: 差异检验",
                    "missing": [],
                    "steps": {"stats_tests": {"status": "ok"}}
                },
                {
                    "hypothesis": "H2: 预测模型",
                    "missing": [],
                    "steps": {"model_train": {"status": "ok"}}
                }
            ]
        }
        
        evidence = _build_hypothesis_evidence(session_dir, hypothesis_payload)
        assert len(evidence.get("hypotheses", [])) == 3  # H1-H3 (与计划一致)
        
        # 测试证据对比
        contrast = _build_hypothesis_contrast(evidence, session_dir)
        assert len(contrast.get("hypotheses", [])) == 3
        
        # 测试深度研究摘要
        state = {"plan_json": plan_json}
        digest = build_research_digest(session_dir, state)
        assert digest.get("summary", {}).get("total_hypotheses") == 3  # 只包含计划中定义的假设
        
        # 测试深度焦点选择
        focus = select_depth_focus(digest)
        assert focus.get("mode") in ["closure_followup", "escalated_research", "stop"]
        
        # 测试阶段闭合评估
        merged_state = {"plan_json": plan_json}
        plan_closure = evaluate_phase_closure("plan_analysis", session_dir, merged_state)
        assert plan_closure is not None
        assert plan_closure.get("status") == "success"
        
        # 测试完成摘要
        closure_map = load_phase_closure_map(session_dir)
        completion = closure_completion_summary(closure_map)
        assert isinstance(completion, dict)


def test_evidence_chain_conflict_detection():
    """测试证据链冲突检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建冲突的结果文件
        stats_results = [
            {"feature": "feature1", "p_value": 0.01, "mean_diff": 1.5},
            {"feature": "feature2", "p_value": 0.03, "mean_diff": 0.8}
        ]
        (session_dir / "result" / "stats_results.json").write_text(
            json.dumps(stats_results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建与p值冲突的q值结果
        multiple_testing = [
            {"feature": "feature1", "q_value": 0.06},
            {"feature": "feature2", "q_value": 0.08}
        ]
        (session_dir / "result" / "multiple_testing.json").write_text(
            json.dumps(multiple_testing, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 构建证据
        hypothesis_payload = {
            "hypotheses": [
                {
                    "hypothesis": "H1: 差异检验",
                    "missing": [],
                    "steps": {"stats_tests": {"status": "ok"}}
                }
            ]
        }
        
        evidence = _build_hypothesis_evidence(session_dir, hypothesis_payload)
        contrast = _build_hypothesis_contrast(evidence, session_dir)
        
        # 检查冲突检测
        h1_contrast = next((h for h in contrast.get("hypotheses", []) if h.get("hypothesis_id") == "H1"), None)
        assert h1_contrast is not None
        assert h1_contrast.get("consistency") == "conflict"
        assert "conflict_reason" in h1_contrast


def test_depth_delta_calculation():
    """测试深度增量计算"""
    # 创建两个模拟的研究摘要
    previous_digest = {
        "depth": 1,
        "summary": {
            "total_hypotheses": 4,
            "stable_count": 1,
            "unresolved_count": 3,
            "blocking_phase_count": 1,
            "unique_evidence_source_count": 5
        },
        "hypotheses": [
            {"hypothesis_id": "H1", "gate_status": "pass", "path_overall": "complete"},
            {"hypothesis_id": "H2", "gate_status": "fail", "path_overall": "incomplete"},
            {"hypothesis_id": "H3", "gate_status": "partial", "path_overall": "complete"},
            {"hypothesis_id": "H4", "gate_status": "fail", "path_overall": "incomplete"}
        ]
    }
    
    current_digest = {
        "depth": 2,
        "summary": {
            "total_hypotheses": 4,
            "stable_count": 3,
            "unresolved_count": 1,
            "blocking_phase_count": 0,
            "unique_evidence_source_count": 8
        },
        "hypotheses": [
            {"hypothesis_id": "H1", "gate_status": "pass", "path_overall": "complete"},
            {"hypothesis_id": "H2", "gate_status": "pass", "path_overall": "complete"},
            {"hypothesis_id": "H3", "gate_status": "pass", "path_overall": "complete"},
            {"hypothesis_id": "H4", "gate_status": "fail", "path_overall": "incomplete"}
        ]
    }
    
    current_focus = {
        "mode": "closure_followup",
        "selected": [
            {"hypothesis_id": "H2"}, {"hypothesis_id": "H3"}
        ]
    }
    
    delta = build_depth_delta(previous_digest, current_digest, current_focus)
    assert delta.get("stable_count_delta") == 2
    assert delta.get("unresolved_count_delta") == -2
    assert delta.get("blocking_phase_count_delta") == -1
    assert delta.get("unique_evidence_source_count_delta") == 3
    assert delta.get("material_gain") is True


def test_evidence_chain_edge_cases():
    """测试证据链的边界情况"""
    # 测试空假设列表
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        
        # 创建空的分析计划
        plan_json = {"hypotheses": []}
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        (session_dir / "plan" / "analysis_plan.md").write_text(
            "# 分析计划\n\n### 1. 假设列表\n\n### 2. 详细分析步骤\n",
            encoding="utf-8"
        )
        
        state = {"plan_json": plan_json}
        digest = build_research_digest(session_dir, state)
        assert digest.get("summary", {}).get("total_hypotheses") == 0
        
        # 测试只有一个假设的情况
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        
        plan_json = {
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "唯一假设",
                    "hypothesis": "测试唯一假设",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        (session_dir / "plan" / "analysis_plan.md").write_text(
            "# 分析计划\n\n### 1. 假设列表\n\n#### 假设 1：唯一假设\n- 验证路径 A：测试\n- 验证路径 B：验证\n\n### 2. 详细分析步骤\n",
            encoding="utf-8"
        )
        
        state = {"plan_json": plan_json}
        digest = build_research_digest(session_dir, state)
        assert digest.get("summary", {}).get("total_hypotheses") == 1


def test_evidence_chain_custom_thresholds():
    """测试自定义阈值的情况"""
    from src.core.orchestration.closure import evaluate_evidence_chain_closure
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        
        # 创建基本的分析计划
        plan_json = {
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "测试假设",
                    "hypothesis": "测试自定义阈值",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        (session_dir / "plan" / "analysis_plan.md").write_text(
            "# 分析计划\n\n### 1. 假设列表\n\n#### 假设 1：测试假设\n- 验证路径 A：测试\n- 验证路径 B：验证\n\n### 2. 详细分析步骤\n",
            encoding="utf-8"
        )
        
        # 创建基本的结果文件
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps({
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": {"p_value": 0.01},
                        "evidence_sources": ["test.json"],
                        "hypothesis_type": "difference"
                    }
                ]
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps({
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "consistency": "consistent"
                    }
                ]
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试默认阈值
        merged_state = {"plan_json": plan_json}
        result = evaluate_evidence_chain_closure(session_dir, merged_state)
        assert result.get("summary", {}).get("thresholds", {}).get("complete") == 80
        assert result.get("summary", {}).get("thresholds", {}).get("partial") == 50
        
        # 测试自定义阈值
        merged_state = {
            "plan_json": plan_json,
            "config": {
                "closure": {
                    "complete_threshold": 90,
                    "partial_threshold": 60
                }
            }
        }
        result = evaluate_evidence_chain_closure(session_dir, merged_state)
        assert result.get("summary", {}).get("thresholds", {}).get("complete") == 90
        assert result.get("summary", {}).get("thresholds", {}).get("partial") == 60


if __name__ == "__main__":
    pytest.main([__file__])
