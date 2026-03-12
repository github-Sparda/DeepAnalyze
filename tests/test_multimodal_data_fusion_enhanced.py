from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.core.orchestration.depth_research import (
    calculate_evidence_weights,
    build_evidence_network,
    integrate_multidimensional_evidence,
    analyze_multimodal_data,
    calculate_confidence_score,
    perform_sensitivity_analysis,
    calculate_stability_score
)


def test_multimodal_evidence_weights_with_uncertainty():
    """测试带有不确定性指标的多模态证据权重计算"""
    # 测试不同类型的证据源
    evidence_sources = [
        "data.csv",
        "results.json",
        "visualization.png",
        "analysis.md",
        "audio_recording.wav"
    ]
    
    # 测试多模态特定指标，包括不确定性指标
    quant_metrics = {
        "p_value": 0.01,
        "p_value_std": 0.001,  # 低不确定性
        "auc": 0.92,
        "auc_std": 0.02,       # 低不确定性
        "text_confidence": 0.95,
        "image_quality": 0.85,
        "audio_clarity": 0.90
    }
    
    # 计算权重
    weights = calculate_evidence_weights(evidence_sources, quant_metrics)
    
    # 验证结果
    assert len(weights) == 5
    assert "data.csv" in weights
    assert "results.json" in weights
    assert "visualization.png" in weights
    assert "analysis.md" in weights
    assert "audio_recording.wav" in weights
    
    # 验证权重值
    assert weights["data.csv"] > 0
    assert weights["results.json"] > 0
    assert weights["visualization.png"] > 0
    assert weights["analysis.md"] > 0
    assert weights["audio_recording.wav"] > 0


def test_multimodal_evidence_network_with_complex_connections():
    """测试带有复杂连接的多模态证据网络构建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含复杂多模态证据的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "p_value": 0.01,
                        "p_value_std": 0.001,
                        "auc": 0.92,
                        "auc_std": 0.02,
                        "text_confidence": 0.95,
                        "image_quality": 0.85,
                        "audio_clarity": 0.90
                    },
                    "evidence_sources": [
                        "data.csv",
                        "results.json",
                        "visualization.png",
                        "analysis.md",
                        "audio_recording.wav"
                    ],
                    "method_trace": [
                        {"model_name": "stats_model"},
                        {"model_name": "visual_model"},
                        {"model_name": "nlp_model"},
                        {"model_name": "audio_model"}
                    ]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 构建证据网络
        network = build_evidence_network(session_dir, "H1")
        
        # 验证结果
        assert "nodes" in network
        assert "edges" in network
        assert "multimodal" in network
        assert "evidence_types" in network
        assert "network_metrics" in network
        
        # 验证多模态标志
        assert network["multimodal"] is True
        assert len(network["evidence_types"]) > 1
        
        # 验证节点和边的数量
        assert len(network["nodes"]) > 0
        assert len(network["edges"]) > 0
        
        # 验证融合节点存在
        fusion_nodes = [node for node in network["nodes"] if node.get("type") == "fusion"]
        assert len(fusion_nodes) == 1
        
        # 验证网络指标
        assert "density" in network["network_metrics"]
        assert "average_degree" in network["network_metrics"]
        assert "node_types" in network["network_metrics"]
        assert "edge_types" in network["network_metrics"]


def test_multimodal_analysis_with_anomaly_detection():
    """测试带有异常检测的多模态数据分析"""
    # 测试多模态证据源
    evidence_sources = [
        "data.csv",
        "results.json",
        "visualization.png",
        "analysis.md",
        "audio_recording.wav"
    ]
    
    # 测试带有异常的多模态特定指标
    quant_metrics = {
        "p_value": 0.01,
        "p_value_std": 0.1,  # 高不确定性（异常）
        "auc": 0.92,
        "auc_std": 0.15,      # 高不确定性（异常）
        "text_confidence": 0.5,  # 低置信度（异常）
        "image_quality": 0.4,   # 低质量（异常）
        "audio_clarity": 0.5    # 低清晰度（异常）
    }
    
    # 模拟证据网络
    evidence_network = {
        "multimodal": True,
        "evidence_types": ["data", "json", "image", "text", "audio"],
        "node_count": 20,
        "edge_count": 50
    }
    
    # 分析多模态数据
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    
    # 验证结果
    assert "source_types" in analysis
    assert "multimodal" in analysis
    assert "evidence_types" in analysis
    assert "fusion_quality" in analysis
    assert "multimodal_metrics" in analysis
    assert "cross_modal_correlation" in analysis
    assert "anomalies" in analysis
    assert "recommendations" in analysis
    
    # 验证多模态标志
    assert analysis["multimodal"] is True
    assert len(analysis["evidence_types"]) > 1
    
    # 验证融合质量
    assert analysis["fusion_quality"] > 0
    
    # 验证多模态指标
    assert "text_confidence" in analysis["multimodal_metrics"]
    assert "image_quality" in analysis["multimodal_metrics"]
    assert "audio_clarity" in analysis["multimodal_metrics"]
    
    # 验证异常检测
    assert len(analysis["anomalies"]) > 0
    assert any(anomaly["type"] == "text" and anomaly["issue"] == "低置信度" for anomaly in analysis["anomalies"])
    assert any(anomaly["type"] == "image" and anomaly["issue"] == "低质量" for anomaly in analysis["anomalies"])
    assert any(anomaly["type"] == "audio" and anomaly["issue"] == "低清晰度" for anomaly in analysis["anomalies"])
    assert any(anomaly["type"] == "statistical" and "高p值不确定性" in anomaly["issue"] for anomaly in analysis["anomalies"])
    assert any(anomaly["type"] == "model" and "高AUC不确定性" in anomaly["issue"] for anomaly in analysis["anomalies"])


def test_multimodal_integration_with_sensitivity_analysis():
    """测试带有敏感性分析的多维度证据整合"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含多模态证据的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "p_value": 0.01,
                        "q_value": 0.02,
                        "auc": 0.92,
                        "accuracy": 0.85,
                        "f1": 0.82,
                        "effect_size": 0.6,
                        "strongest_abs_corr": 0.75,
                        "text_confidence": 0.95,
                        "image_quality": 0.85
                    },
                    "evidence_sources": [
                        "data.csv",
                        "results.json",
                        "visualization.png",
                        "analysis.md"
                    ],
                    "method_trace": [
                        {"model_name": "stats_model"},
                        {"model_name": "visual_model"}
                    ]
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
                    "hypothesis_id": "H1",
                    "consistency": "consistent"
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_multipath.json").write_text(
            json.dumps(multipath, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 整合多维度证据
        integrated = integrate_multidimensional_evidence(session_dir, "H1")
        
        # 验证结果
        assert "hypothesis_id" in integrated
        assert "evidence_sources" in integrated
        assert "quant_metrics" in integrated
        assert "evidence_weights" in integrated
        assert "evidence_network" in integrated
        assert "multipath_consistency" in integrated
        assert "confidence_score" in integrated
        assert "multimodal_analysis" in integrated
        
        # 验证多模态分析
        multimodal_analysis = integrated["multimodal_analysis"]
        assert "source_types" in multimodal_analysis
        assert "multimodal" in multimodal_analysis
        assert "evidence_types" in multimodal_analysis
        assert "fusion_quality" in multimodal_analysis
        assert "recommendations" in multimodal_analysis


def test_confidence_score_calculation():
    """测试置信度分数计算"""
    # 测试证据权重
    evidence_weights = {
        "data.csv": 0.9,
        "results.json": 0.8,
        "visualization.png": 0.7,
        "analysis.md": 0.6
    }
    
    # 测试一致的多路径数据
    multipath_data_consistent = {
        "consistency": "consistent"
    }
    
    # 测试部分一致的多路径数据
    multipath_data_partial = {
        "consistency": "partial"
    }
    
    # 测试冲突的多路径数据
    multipath_data_conflict = {
        "consistency": "conflict"
    }
    
    # 计算置信度分数
    score_consistent = calculate_confidence_score(evidence_weights, multipath_data_consistent)
    score_partial = calculate_confidence_score(evidence_weights, multipath_data_partial)
    score_conflict = calculate_confidence_score(evidence_weights, multipath_data_conflict)
    
    # 验证结果
    assert score_consistent > score_partial > score_conflict
    assert 0 <= score_consistent <= 1
    assert 0 <= score_partial <= 1
    assert 0 <= score_conflict <= 1


def test_sensitivity_analysis():
    """测试敏感性分析"""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        (session_dir / "result").mkdir(parents=True, exist_ok=True)
        
        # 创建包含多种指标的证据包
        evidence_pack = {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "hypothesis_type": "predictive",
                    "quant_metrics": {
                        "p_value": 0.001,
                        "q_value": 0.002,
                        "auc": 0.95,
                        "accuracy": 0.90,
                        "f1": 0.88,
                        "effect_size": 0.7,
                        "strongest_abs_corr": 0.85
                    },
                    "evidence_sources": ["data.csv"]
                }
            ]
        }
        
        (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 执行敏感性分析
        sensitivity = perform_sensitivity_analysis(session_dir, "H1")
        
        # 验证结果
        assert "hypothesis_id" in sensitivity
        assert "sensitivity_results" in sensitivity
        assert "overall_stability" in sensitivity
        
        # 验证敏感性结果
        sensitivity_results = sensitivity["sensitivity_results"]
        assert "p_value_sensitivity" in sensitivity_results
        assert "auc_sensitivity" in sensitivity_results
        assert "accuracy_sensitivity" in sensitivity_results
        assert "f1_sensitivity" in sensitivity_results
        assert "correlation_sensitivity" in sensitivity_results
        assert "effect_size_sensitivity" in sensitivity_results
        assert "q_value_sensitivity" in sensitivity_results
        
        # 验证稳定性分数
        assert 0 <= sensitivity["overall_stability"] <= 1


def test_stability_score_calculation():
    """测试稳定性分数计算"""
    # 测试高稳定性的敏感性结果
    high_stability_results = {
        "p_value_sensitivity": {
            "original": 0.001,
            "threshold_0_05": True,
            "threshold_0_01": True,
            "threshold_0_001": True
        },
        "auc_sensitivity": {
            "original": 0.95,
            "excellent": True,
            "good": True,
            "fair": True
        }
    }
    
    # 测试低稳定性的敏感性结果
    low_stability_results = {
        "p_value_sensitivity": {
            "original": 0.049,
            "threshold_0_05": True,
            "threshold_0_01": False,
            "threshold_0_001": False
        },
        "auc_sensitivity": {
            "original": 0.75,
            "excellent": False,
            "good": False,
            "fair": True
        }
    }
    
    # 计算稳定性分数
    high_stability = calculate_stability_score(high_stability_results)
    low_stability = calculate_stability_score(low_stability_results)
    
    # 验证结果
    assert high_stability > low_stability
    assert 0 <= high_stability <= 1
    assert 0 <= low_stability <= 1


def test_multimodal_edge_cases():
    """测试多模态数据融合的边界情况"""
    # 测试空证据源
    evidence_sources = []
    quant_metrics = {}
    evidence_network = {
        "multimodal": False,
        "evidence_types": [],
        "node_count": 0,
        "edge_count": 0
    }
    
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    assert analysis["source_types"] == {}
    assert analysis["multimodal"] is False
    assert analysis["evidence_types"] == []
    assert analysis["fusion_quality"] == 0.0
    
    # 测试只有一种类型的证据源
    evidence_sources = ["data1.csv", "data2.csv"]
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    assert analysis["source_types"] == {"data": 2}
    assert analysis["multimodal"] is False
    assert analysis["evidence_types"] == []
    
    # 测试只有音频证据源
    evidence_sources = ["audio1.wav", "audio2.mp3"]
    quant_metrics = {
        "audio_clarity": 0.85
    }
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    assert analysis["source_types"] == {"audio": 2}
    assert analysis["multimodal"] is False
    assert "audio_clarity" in analysis["multimodal_metrics"]


def test_multimodal_cross_correlation():
    """测试多模态数据的跨模态相关性分析"""
    # 测试多模态证据源
    evidence_sources = [
        "data.csv",
        "results.json",
        "visualization.png",
        "analysis.md"
    ]
    
    # 测试多模态特定指标
    quant_metrics = {
        "p_value": 0.01,
        "auc": 0.92,
        "text_confidence": 0.95,
        "image_quality": 0.85
    }
    
    # 模拟证据网络
    evidence_network = {
        "multimodal": True,
        "evidence_types": ["data", "json", "image", "text"],
        "node_count": 15,
        "edge_count": 30
    }
    
    # 分析多模态数据
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    
    # 验证跨模态相关性
    assert "cross_modal_correlation" in analysis
    cross_correlation = analysis["cross_modal_correlation"]
    assert "score" in cross_correlation
    assert "strength" in cross_correlation
    assert 0 <= cross_correlation["score"] <= 1
    assert cross_correlation["strength"] in ["strong", "medium", "weak"]


if __name__ == "__main__":
    pytest.main([__file__])
