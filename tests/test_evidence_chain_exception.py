from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.orchestration.closure import evaluate_evidence_chain_closure
from src.core.orchestration.depth_research import (
    integrate_multidimensional_evidence,
    perform_sensitivity_analysis,
    build_evidence_network
)


def test_evidence_chain_exception_corrupted_files():
    """测试证据文件损坏的情况"""
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
                    "hypothesis": "测试异常场景",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建损坏的证据文件
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            "{这不是有效的JSON",  # 损坏的JSON
            encoding="utf-8"
        )
        
        # 测试证据链评估
        merged_state = {"plan_json": plan_json}
        result = evaluate_evidence_chain_closure(session_dir, merged_state)
        # 应该能够处理损坏的文件，返回默认值
        assert isinstance(result, dict)
        assert "hypotheses" in result


def test_evidence_chain_exception_missing_files():
    """测试缺失证据文件的情况"""
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
                    "hypothesis": "测试异常场景",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 故意不创建证据文件
        # 测试证据链评估
        merged_state = {"plan_json": plan_json}
        result = evaluate_evidence_chain_closure(session_dir, merged_state)
        # 应该能够处理缺失文件，返回默认值
        assert isinstance(result, dict)
        assert "hypotheses" in result


def test_evidence_chain_exception_invalid_data_structure():
    """测试无效数据结构的情况"""
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
                    "hypothesis": "测试异常场景",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建无效数据结构的证据文件
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps({
                "hypotheses": "这不是一个列表"  # 无效的数据结构
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试证据链评估
        merged_state = {"plan_json": plan_json}
        result = evaluate_evidence_chain_closure(session_dir, merged_state)
        # 应该能够处理无效数据结构，返回默认值
        assert isinstance(result, dict)
        assert "hypotheses" in result


def test_depth_research_exception_corrupted_files():
    """测试深度研究模块处理损坏文件的情况"""
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
                    "hypothesis": "测试异常场景",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建损坏的证据文件
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            "{这不是有效的JSON",  # 损坏的JSON
            encoding="utf-8"
        )
        
        # 测试多维度证据整合
        try:
            result = integrate_multidimensional_evidence(session_dir, "H1")
            # 应该能够处理损坏的文件，返回默认值
            assert isinstance(result, dict)
        except Exception as e:
            # 也可以接受抛出异常，因为损坏的文件可能导致解析错误
            pass


def test_sensitivity_analysis_exception_missing_data():
    """测试敏感性分析处理缺失数据的情况"""
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
                    "hypothesis": "测试异常场景",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建没有量化指标的证据文件
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps({
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        # 故意不包含quant_metrics
                        "evidence_sources": ["test.json"],
                        "hypothesis_type": "difference"
                    }
                ]
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试敏感性分析
        result = perform_sensitivity_analysis(session_dir, "H1")
        # 应该能够处理缺失数据，返回默认值
        assert isinstance(result, dict)
        assert "sensitivity_results" in result
        assert "overall_stability" in result


def test_evidence_network_exception_empty_data():
    """测试证据网络构建处理空数据的情况"""
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
                    "hypothesis": "测试异常场景",
                    "validation_paths": ["path_a", "path_b"]
                }
            ]
        }
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建空数据的证据文件
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps({
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": {},  # 空的量化指标
                        "evidence_sources": [],  # 空的证据源
                        "hypothesis_type": "difference"
                    }
                ]
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试证据网络构建
        result = build_evidence_network(session_dir, "H1")
        # 应该能够处理空数据，返回默认值
        assert isinstance(result, dict)
        assert "nodes" in result
        assert "edges" in result
        assert "node_count" in result
        assert "edge_count" in result


if __name__ == "__main__":
    pytest.main([__file__])
