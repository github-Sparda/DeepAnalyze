from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.orchestration.closure import (
    _generate_conflict_resolution, 
    _detect_evidence_conflicts,
    assess_conflict_severity,
    get_severity_score
)


def test_feature_selection_conflict_resolution():
    """测试特征选择冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含特征选择指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "feature_count": 15,
                        "feature_importance": [0.2, 0.15, 0.1, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01]
                    },
                    "evidence_sources": ["feature_importance.json"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "feature_selection_conflict",
            "reason": "Too many features with low importance",
            "severity": "medium",
            "source": "feature_analysis"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H1", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H1"
        assert resolution["conflict_type"] == "feature_selection_conflict"
        assert resolution["priority"] == "medium"
        assert len(resolution["resolutions"]) == 5
        assert "特征数量过多，存在多个低重要性特征" in resolution["resolutions"][0]
        assert "建议使用特征选择算法（如LASSO、RFE等）减少特征数量" in resolution["resolutions"][1]


def test_time_series_conflict_resolution():
    """测试时间序列冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含时间序列指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H2",
                    "hypothesis_type": "time_series",
                    "quant_metrics": {
                        "stationarity_p_value": 0.15
                    },
                    "evidence_sources": ["time_series_analysis.json"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "time_series_conflict",
            "reason": "Non-stationary time series detected",
            "severity": "high",
            "source": "time_series_analysis"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H2", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H2"
        assert resolution["conflict_type"] == "time_series_conflict"
        assert resolution["priority"] == "high"
        assert len(resolution["resolutions"]) == 5
        assert "时间序列非平稳，建议进行差分处理" in resolution["resolutions"][0]
        assert "考虑使用ARIMA模型处理非平稳时间序列" in resolution["resolutions"][1]


def test_causal_inference_conflict_resolution():
    """测试因果推断冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含因果推断指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H3",
                    "hypothesis_type": "causal",
                    "quant_metrics": {
                        "confounding_score": 0.85
                    },
                    "evidence_sources": ["causal_analysis.json"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "causal_inference_conflict",
            "reason": "High confounding detected",
            "severity": "high",
            "source": "causal_analysis"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H3", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H3"
        assert resolution["conflict_type"] == "causal_inference_conflict"
        assert resolution["priority"] == "high"
        assert len(resolution["resolutions"]) == 5
        assert "存在高混淆因素，建议使用倾向得分匹配（PSM）" in resolution["resolutions"][0]
        assert "考虑使用工具变量方法控制混淆" in resolution["resolutions"][1]


def test_conflict_severity_assessment():
    """测试冲突严重程度评估"""
    # 测试统计冲突的严重程度
    severity = assess_conflict_severity("statistical_conflict", "p-value and q-value conflict", "difference")
    assert severity == "high"
    
    # 测试方法学冲突的严重程度
    severity = assess_conflict_severity("methodological_conflict", "Accuracy is not sufficient", "predictive")
    assert severity == "high"
    
    # 测试相关性冲突的严重程度
    severity = assess_conflict_severity("correlation_conflict", "Pearson correlation shows inconsistent results", "correlation")
    assert severity == "medium"
    
    # 测试嵌入冲突的严重程度
    severity = assess_conflict_severity("embedding_conflict", "t-SNE visualization shows unclear clusters", "clustering")
    assert severity == "low"


def test_severity_score():
    """测试严重程度分数"""
    assert get_severity_score("high") == 3
    assert get_severity_score("medium") == 2
    assert get_severity_score("low") == 1
    assert get_severity_score("none") == 0
    assert get_severity_score("unknown") == 0


def test_evidence_conflict_detection():
    """测试证据冲突检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含多种冲突的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H4",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "p_value": 0.02,
                        "q_value": 0.06,
                        "train_accuracy": 0.95,
                        "test_accuracy": 0.70,
                        "feature_count": 12,
                        "feature_importance": [0.3, 0.2, 0.15, 0.1, 0.05, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01, 0.01]
                    },
                    "evidence_sources": ["data.csv"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建多路径数据
        multipath = {
            "hypotheses": [
                {
                    "hypothesis_id": "H4",
                    "consistency": "conflict",
                    "conflict_reason": "p-value and q-value conflict"
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps(multipath, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 检测冲突
        conflicts = _detect_evidence_conflicts(session_dir, "H4")
        
        # 验证结果
        assert conflicts["hypothesis_id"] == "H4"
        assert conflicts["conflict_count"] > 0
        assert conflicts["overall_conflict_type"] == "statistical_conflict"
        assert conflicts["conflict_severity"] == "high"


def test_conflict_resolution_with_user_preferences():
    """测试基于用户偏好的冲突解决"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含用户偏好的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H5",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "train_accuracy": 0.92,
                        "test_accuracy": 0.75
                    },
                    "evidence_sources": ["model_results.json"],
                    "user_preferences": {
                        "priority": "high"
                    }
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "overfitting_conflict",
            "reason": "High overfitting detected",
            "severity": "medium",
            "source": "model_metrics"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H5", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H5"
        assert resolution["priority"] == "high"  # 基于用户偏好调整优先级


def test_conflict_resolution_with_history():
    """测试基于历史解决记录的冲突解决"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含历史解决记录的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H6",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "train_accuracy": 0.90,
                        "test_accuracy": 0.70
                    },
                    "evidence_sources": ["model_results.json"],
                    "resolution_history": [
                        {
                            "conflict_type": "overfitting_conflict",
                            "resolution": "增加L2正则化",
                            "success": True
                        }
                    ]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "overfitting_conflict",
            "reason": "High overfitting detected",
            "severity": "medium",
            "source": "model_metrics"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H6", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H6"
        # 验证正则化相关建议是否在前面
        assert any("正则化" in res for res in resolution["resolutions"])


def test_multiple_conflicts_detection():
    """测试多个冲突的检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含多个冲突的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H7",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "p_value": 0.03,
                        "q_value": 0.07,
                        "train_accuracy": 0.93,
                        "test_accuracy": 0.68
                    },
                    "evidence_sources": ["data.csv"]  # 只有一种类型的证据源
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建多路径数据
        multipath = {
            "hypotheses": [
                {
                    "hypothesis_id": "H7",
                    "consistency": "conflict",
                    "conflict_reason": "p-value and q-value conflict"
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps(multipath, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 检测冲突
        conflicts = _detect_evidence_conflicts(session_dir, "H7")
        
        # 验证结果
        assert conflicts["hypothesis_id"] == "H7"
        assert conflicts["conflict_count"] >= 2  # 至少有统计冲突和证据源冲突
        assert conflicts["overall_conflict_type"] == "statistical_conflict"  # 最严重的冲突类型


if __name__ == "__main__":
    pytest.main([__file__])
