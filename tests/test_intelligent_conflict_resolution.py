from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.orchestration.closure import _generate_conflict_resolution, _detect_evidence_conflicts


def test_statistical_conflict_resolution():
    """测试统计冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含量化指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "hypothesis_type": "difference",
                    "quant_metrics": {
                        "p_value": 0.02,
                        "q_value": 0.06
                    },
                    "evidence_sources": ["data.csv"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "statistical_conflict",
            "reason": "p-value and q-value conflict",
            "severity": "high",
            "source": "multipath_consistency"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H1", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H1"
        assert resolution["conflict_type"] == "statistical_conflict"
        assert resolution["priority"] == "high"
        assert len(resolution["resolutions"]) == 5
        assert "p值(0.0200)显著但q值(0.0600)不显著" in resolution["resolutions"][0]
        assert "resolution_steps" in resolution
        assert len(resolution["resolution_steps"]) == 5


def test_overfitting_conflict_resolution():
    """测试过拟合冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含量化指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H2",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "train_accuracy": 0.95,
                        "test_accuracy": 0.70
                    },
                    "evidence_sources": ["model_results.json"]
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
        resolution = _generate_conflict_resolution(session_dir, "H2", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H2"
        assert resolution["conflict_type"] == "overfitting_conflict"
        assert resolution["priority"] == "high"  # 预测模型的过拟合冲突应该是高优先级
        assert len(resolution["resolutions"]) == 5
        assert "严重过拟合：训练准确率(0.95)与测试准确率(0.70)差异过大" in resolution["resolutions"][0]


def test_evidence_source_conflict_resolution():
    """测试证据源冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建只有一种证据源类型的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H3",
                    "hypothesis_type": "correlation",
                    "evidence_sources": ["data.csv"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "evidence_source_conflict",
            "reason": "Only one type of evidence source found: csv",
            "severity": "low",
            "source": "evidence_source_diversity"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H3", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H3"
        assert resolution["conflict_type"] == "evidence_source_conflict"
        assert resolution["priority"] == "low"
        assert len(resolution["resolutions"]) == 5
        assert "当前只有csv类型的证据，建议增加以下类型的证据" in resolution["resolutions"][0]


def test_embedding_conflict_resolution():
    """测试嵌入冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H4",
                    "hypothesis_type": "clustering",
                    "evidence_sources": ["embedding.png"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "embedding_conflict",
            "reason": "t-SNE visualization shows unclear clusters",
            "severity": "medium",
            "source": "visualization"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H4", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H4"
        assert resolution["conflict_type"] == "embedding_conflict"
        assert resolution["priority"] == "medium"
        assert len(resolution["resolutions"]) == 5
        assert "调整t-SNE的perplexity参数" in resolution["resolutions"][0]


def test_methodological_conflict_resolution():
    """测试方法学冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含准确率指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H5",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "train_accuracy": 0.85,
                        "test_accuracy": 0.80
                    },
                    "evidence_sources": ["model.json"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "methodological_conflict",
            "reason": "Accuracy is not sufficient",
            "severity": "medium",
            "source": "model_evaluation"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H5", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H5"
        assert resolution["conflict_type"] == "methodological_conflict"
        assert resolution["priority"] == "medium"
        assert len(resolution["resolutions"]) == 5
        assert "尝试不同的建模方法" in resolution["resolutions"][0]


def test_data_conflict_resolution():
    """测试数据冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含CSV证据源的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H6",
                    "hypothesis_type": "difference",
                    "evidence_sources": ["data.csv"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "data_conflict",
            "reason": "Data inconsistency detected",
            "severity": "high",
            "source": "data_quality"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H6", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H6"
        assert resolution["conflict_type"] == "data_conflict"
        assert resolution["priority"] == "high"
        assert len(resolution["resolutions"]) == 5
        assert "检查CSV数据的格式和编码是否正确" in resolution["resolutions"][0]


def test_correlation_conflict_resolution():
    """测试相关性冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H7",
                    "hypothesis_type": "correlation",
                    "evidence_sources": ["correlation.json"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "correlation_conflict",
            "reason": "Pearson correlation shows inconsistent results",
            "severity": "medium",
            "source": "correlation_analysis"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H7", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H7"
        assert resolution["conflict_type"] == "correlation_conflict"
        assert resolution["priority"] == "medium"
        assert len(resolution["resolutions"]) == 5
        assert "Pearson相关性对异常值敏感" in resolution["resolutions"][0]


def test_generic_conflict_resolution():
    """测试通用冲突的智能解决建议"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建基本证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H8",
                    "hypothesis_type": "generic",
                    "evidence_sources": ["analysis.md"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 创建冲突对象
        conflict = {
            "type": "unknown_conflict",
            "reason": "Unknown conflict reason",
            "severity": "medium",
            "source": "unknown_source"
        }
        
        # 生成解决建议
        resolution = _generate_conflict_resolution(session_dir, "H8", conflict)
        
        # 验证结果
        assert resolution["hypothesis_id"] == "H8"
        assert resolution["conflict_type"] == "unknown_conflict"
        assert resolution["priority"] == "medium"
        assert len(resolution["resolutions"]) == 5
        assert "详细分析冲突原因" in resolution["resolutions"][0]


if __name__ == "__main__":
    pytest.main([__file__])
