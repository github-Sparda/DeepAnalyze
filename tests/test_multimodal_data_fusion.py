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
    analyze_multimodal_data
)


def test_multimodal_evidence_weights():
    """测试多模态证据权重计算"""
    # 测试不同类型的证据源
    evidence_sources = [
        "data.csv",
        "results.json",
        "visualization.png",
        "analysis.md",
        "report.pdf"
    ]
    
    # 测试多模态特定指标
    quant_metrics = {
        "p_value": 0.01,
        "auc": 0.92,
        "text_confidence": 0.95,
        "image_quality": 0.85
    }
    
    # 计算权重
    weights = calculate_evidence_weights(evidence_sources, quant_metrics)
    
    # 验证结果
    assert len(weights) == 5
    assert "data.csv" in weights
    assert "results.json" in weights
    assert "visualization.png" in weights
    assert "analysis.md" in weights
    assert "report.pdf" in weights
    
    # 验证权重值
    assert weights["data.csv"] > 0
    assert weights["results.json"] > 0
    assert weights["visualization.png"] > 0
    assert weights["analysis.md"] > 0
    assert weights["report.pdf"] > 0


def test_multimodal_evidence_network():
    """测试多模态证据网络构建"""
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
                        "auc": 0.92,
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
        
        # 构建证据网络
        network = build_evidence_network(session_dir, "H1")
        
        # 验证结果
        assert "nodes" in network
        assert "edges" in network
        assert "multimodal" in network
        assert "evidence_types" in network
        
        # 验证多模态标志
        assert network["multimodal"] is True
        assert len(network["evidence_types"]) > 1
        
        # 验证节点和边的数量
        assert len(network["nodes"]) > 0
        assert len(network["edges"]) > 0
        
        # 验证融合节点存在
        fusion_nodes = [node for node in network["nodes"] if node.get("type") == "fusion"]
        assert len(fusion_nodes) == 1


def test_multimodal_analysis():
    """测试多模态数据分析"""
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
        "node_count": 10,
        "edge_count": 20
    }
    
    # 分析多模态数据
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    
    # 验证结果
    assert "source_types" in analysis
    assert "multimodal" in analysis
    assert "evidence_types" in analysis
    assert "fusion_quality" in analysis
    assert "multimodal_metrics" in analysis
    assert "recommendations" in analysis
    
    # 验证多模态标志
    assert analysis["multimodal"] is True
    assert len(analysis["evidence_types"]) > 1
    
    # 验证融合质量
    assert analysis["fusion_quality"] > 0
    
    # 验证多模态指标
    assert "text_confidence" in analysis["multimodal_metrics"]
    assert "image_quality" in analysis["multimodal_metrics"]


def test_single_modal_analysis():
    """测试单模态数据分析"""
    # 测试单模态证据源
    evidence_sources = [
        "data.csv",
        "more_data.csv"
    ]
    
    # 测试基本指标
    quant_metrics = {
        "p_value": 0.01,
        "effect_size": 0.5
    }
    
    # 模拟证据网络
    evidence_network = {
        "multimodal": False,
        "evidence_types": ["data"],
        "node_count": 5,
        "edge_count": 5
    }
    
    # 分析单模态数据
    analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    
    # 验证结果
    assert "source_types" in analysis
    assert "multimodal" in analysis
    assert "evidence_types" in analysis
    assert "fusion_quality" in analysis
    assert "recommendations" in analysis
    
    # 验证单模态标志
    assert analysis["multimodal"] is False
    assert len(analysis["evidence_types"]) == 1
    
    # 验证融合质量为0
    assert analysis["fusion_quality"] == 0.0
    
    # 验证建议
    assert len(analysis["recommendations"]) > 0
    assert "建议增加以下类型的证据" in analysis["recommendations"][0]


def test_multimodal_integration():
    """测试多维度证据整合（多模态）"""
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
                        "auc": 0.92,
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


if __name__ == "__main__":
    pytest.main([__file__])
