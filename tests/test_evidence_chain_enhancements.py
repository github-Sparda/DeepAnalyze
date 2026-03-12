from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.orchestration.closure import (
    _semantic_alignment_ok, 
    _validate_evidence_completeness, 
    _detect_evidence_conflicts, 
    _generate_conflict_resolution
)
from src.core.orchestration.hypothesis_engine import (
    _build_hypothesis_evidence, 
    _build_hypothesis_contrast
)

def test_semantic_alignment_ok():
    """测试语义对齐检查功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # 创建必要的目录结构
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
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
                }
            ]
        }
        
        # 写入分析计划
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建基本的结果文件
        hypothesis_results = {
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
        (session_dir / "result" / "hypothesis_results.json").write_text(
            json.dumps(hypothesis_results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        hypothesis_multipath = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "consistency": "consistent"
                },
                {
                    "hypothesis_id": "H2",
                    "consistency": "consistent"
                }
            ]
        }
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps(hypothesis_multipath, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        hypothesis_evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "evidence_sources": ["result/stats_results.json"],
                    "quant_metrics": {"p_value": 0.01},
                    "hypothesis_type": "difference"
                },
                {
                    "hypothesis_id": "H2",
                    "evidence_sources": ["result/model_eval.json"],
                    "quant_metrics": {"auc": 0.85},
                    "hypothesis_type": "predictive"
                }
            ]
        }
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(hypothesis_evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试语义对齐检查
        merged_state = {"plan_json": plan_json}
        ok, bad = _semantic_alignment_ok(session_dir, merged_state)
        assert ok == True
        assert len(bad) == 0
        
        # 测试部分匹配的情况
        # 修改结果文件，只包含H1
        hypothesis_results_partial = {
            "hypotheses": [
                {
                    "hypothesis": "H1: 差异检验",
                    "missing": [],
                    "steps": {"stats_tests": {"status": "ok"}}
                }
            ]
        }
        (session_dir / "result" / "hypothesis_results.json").write_text(
            json.dumps(hypothesis_results_partial, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        ok, bad = _semantic_alignment_ok(session_dir, merged_state)
        assert ok == False
        assert "results_ids_mismatch" in bad

def test_build_hypothesis_evidence():
    """测试证据构建功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # 创建必要的目录结构
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建基本的分析计划
        plan_json = {
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "差异检验",
                    "hypothesis": "组间存在显著差异标志物",
                    "hypothesis_type": "difference"
                },
                {
                    "id": "H2",
                    "title": "预测模型",
                    "hypothesis": "多特征组合具备诊断预测力",
                    "hypothesis_type": "predictive"
                }
            ]
        }
        
        # 写入分析计划
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
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
        assert len(evidence.get("hypotheses", [])) == 2
        
        # 检查H1的证据
        h1_evidence = next((h for h in evidence.get("hypotheses", []) if h.get("hypothesis_id") == "H1"), None)
        assert h1_evidence is not None
        assert h1_evidence.get("hypothesis_type") == "difference"
        assert "tested_features" in h1_evidence.get("quant_metrics", {})
        
        # 检查H2的证据
        h2_evidence = next((h for h in evidence.get("hypotheses", []) if h.get("hypothesis_id") == "H2"), None)
        assert h2_evidence is not None
        assert h2_evidence.get("hypothesis_type") == "predictive"
        assert "auc" in h2_evidence.get("quant_metrics", {})

def test_build_hypothesis_contrast():
    """测试证据对比功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # 创建必要的目录结构
        (session_dir / "plan").mkdir(parents=True, exist_ok=True)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建基本的分析计划
        plan_json = {
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "差异检验",
                    "hypothesis": "组间存在显著差异标志物",
                    "hypothesis_type": "difference"
                },
                {
                    "id": "H2",
                    "title": "预测模型",
                    "hypothesis": "多特征组合具备诊断预测力",
                    "hypothesis_type": "predictive"
                }
            ]
        }
        
        # 写入分析计划
        (session_dir / "plan" / "analysis_plan.json").write_text(
            json.dumps(plan_json, ensure_ascii=False, indent=2),
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
        
        multiple_testing = [
            {"feature": "feature1", "q_value": 0.02},
            {"feature": "feature2", "q_value": 0.06}
        ]
        (session_dir / "result" / "multiple_testing.json").write_text(
            json.dumps(multiple_testing, ensure_ascii=False, indent=2),
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
        
        cv_results = {
            "mean_accuracy": 0.75,
            "std_accuracy": 0.05,
            "fold_metrics": [0.72, 0.78, 0.75, 0.73, 0.77]
        }
        (session_dir / "result" / "cv_results.json").write_text(
            json.dumps(cv_results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 构建证据
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
        contrast = _build_hypothesis_contrast(evidence, session_dir)
        
        assert len(contrast.get("hypotheses", [])) == 2
        
        # 检查H1的对比
        h1_contrast = next((h for h in contrast.get("hypotheses", []) if h.get("hypothesis_id") == "H1"), None)
        assert h1_contrast is not None
        assert h1_contrast.get("hypothesis_type") == "difference"
        assert "q_lt_0_05" in h1_contrast.get("path_b", {}).get("metrics", {})
        
        # 检查H2的对比
        h2_contrast = next((h for h in contrast.get("hypotheses", []) if h.get("hypothesis_id") == "H2"), None)
        assert h2_contrast is not None
        assert h2_contrast.get("hypothesis_type") == "predictive"
        assert "cv_mean_accuracy" in h2_contrast.get("path_b", {}).get("metrics", {})

def test_validate_evidence_completeness():
    """测试证据完整性评估功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # 创建必要的目录结构
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建证据包文件
        hypothesis_evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "claim": "组间存在显著差异标志物",
                    "evidence_sources": [
                        "result/stats_results.json",
                        "result/stats_summary.json",
                        "plots/volcano_plot.png"
                    ],
                    "quant_metrics": {
                        "tested_features": 100,
                        "significant_p_lt_0_05": 10,
                        "max_abs_mean_diff": 2.5
                    },
                    "hypothesis_type": "difference"
                }
            ]
        }
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(hypothesis_evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建多路径文件
        hypothesis_multipath = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "consistency": "consistent"
                }
            ]
        }
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps(hypothesis_multipath, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试证据完整性评估
        completeness = _validate_evidence_completeness(session_dir, "H1")
        assert completeness.get("hypothesis_id") == "H1"
        assert "completeness_score" in completeness
        assert "quality_score" in completeness
        assert "evidence_weights" in completeness
        assert "evidence_diversity" in completeness
        
        # 检查维度评估
        dimensions = completeness.get("dimensions", {})
        assert "statistical_significance" in dimensions
        assert "effect_size" in dimensions
        assert "robustness" in dimensions
        assert "consistency" in dimensions
        assert "evidence_diversity" in dimensions
        assert "metric_quality" in dimensions
        assert "source_quality" in dimensions

def test_detect_evidence_conflicts():
    """测试证据冲突检测功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # 创建必要的目录结构
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建证据包文件
        hypothesis_evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "claim": "组间存在显著差异标志物",
                    "evidence_sources": ["result/stats_results.json"],
                    "quant_metrics": {
                        "p_value": 0.01,
                        "q_value": 0.06
                    },
                    "hypothesis_type": "difference"
                }
            ]
        }
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(hypothesis_evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建多路径文件
        hypothesis_multipath = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "consistency": "conflict",
                    "conflict_reason": "p-significant=10, q-significant=0"
                }
            ]
        }
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps(hypothesis_multipath, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 测试证据冲突检测
        conflicts = _detect_evidence_conflicts(session_dir, "H1")
        assert conflicts.get("hypothesis_id") == "H1"
        assert conflicts.get("conflict_count") > 0
        assert "conflicts" in conflicts
        assert "overall_conflict_type" in conflicts
        assert "conflict_severity" in conflicts
        
        # 测试冲突解决建议
        if conflicts.get("conflicts"):
            conflict = conflicts.get("conflicts")[0]
            resolution = _generate_conflict_resolution(session_dir, "H1", conflict)
            assert resolution.get("hypothesis_id") == "H1"
            assert "resolutions" in resolution
            assert "priority" in resolution
            assert "conflict_severity" in resolution
            assert "conflict_source" in resolution

if __name__ == "__main__":
    pytest.main([__file__])