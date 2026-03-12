import json
import os
import tempfile
from pathlib import Path
from src.core.reporting.assembler import ReportAssembler


def test_report_evidence_chain_integration():
    """测试报告中证据链集成功能"""
    # 创建临时目录结构
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建必要的目录结构
        (temp_path / "result").mkdir(parents=True, exist_ok=True)
        (temp_path / "meta").mkdir(parents=True, exist_ok=True)
        (temp_path / "plan").mkdir(parents=True, exist_ok=True)
        (temp_path / "report").mkdir(parents=True, exist_ok=True)
        
        # 创建测试证据链数据
        evidence_chain_data = {
            "evidence": [
                {
                    "id": "E1",
                    "type": "statistical",
                    "source": "stats_results.json",
                    "description": "统计检验结果",
                    "confidence": 0.95,
                    "dimensions": ["statistical", "quantitative"]
                },
                {
                    "id": "E2",
                    "type": "visual",
                    "source": "volcano.png",
                    "description": "火山图",
                    "confidence": 0.85,
                    "dimensions": ["visual", "comparative"]
                },
                {
                    "id": "E3",
                    "type": "model",
                    "source": "model_eval.json",
                    "description": "模型评估结果",
                    "confidence": 0.90,
                    "dimensions": ["predictive", "quantitative"]
                }
            ],
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "组间差异显著",
                    "evidence_ids": ["E1", "E2"]
                },
                {
                    "id": "H2",
                    "title": "模型预测性能良好",
                    "evidence_ids": ["E3"]
                }
            ],
            "connections": [
                {
                    "source": "E1",
                    "target": "H1",
                    "strength": 0.9
                },
                {
                    "source": "E2",
                    "target": "H1",
                    "strength": 0.8
                },
                {
                    "source": "E3",
                    "target": "H2",
                    "strength": 0.95
                }
            ]
        }
        
        # 写入证据链数据
        with open(temp_path / "result" / "evidence_chain.json", "w", encoding="utf-8") as f:
            json.dump(evidence_chain_data, f, ensure_ascii=False, indent=2)
        
        # 创建分析计划
        analysis_plan = {
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "组间差异显著",
                    "hypothesis": "两组样本在关键特征上存在显著差异",
                    "validation_plan_steps": [
                        "执行统计检验",
                        "生成火山图",
                        "分析显著特征"
                    ]
                },
                {
                    "id": "H2",
                    "title": "模型预测性能良好",
                    "hypothesis": "训练的模型具有良好的预测性能",
                    "validation_plan_steps": [
                        "训练模型",
                        "评估模型性能",
                        "交叉验证"
                    ]
                }
            ]
        }
        
        # 写入分析计划
        with open(temp_path / "plan" / "analysis_plan.json", "w", encoding="utf-8") as f:
            json.dump(analysis_plan, f, ensure_ascii=False, indent=2)
        
        # 创建分析计划markdown
        plan_md = """
### 1. 假设列表

#### 假设 1：组间差异显著
- 验证路径 A：统计检验
- 验证路径 B：可视化分析

#### 假设 2：模型预测性能良好
- 验证路径 A：模型训练与评估
- 验证路径 B：交叉验证

### 2. 详细分析步骤
1. 数据预处理
2. 执行统计检验
3. 生成可视化图表
4. 训练预测模型
5. 评估模型性能
6. 生成报告
"""
        with open(temp_path / "plan" / "analysis_plan.md", "w", encoding="utf-8") as f:
            f.write(plan_md)
        
        # 创建假设结果
        hypothesis_results = {
            "hypotheses": [
                {
                    "hypothesis": "H1: 组间差异显著",
                    "steps": {
                        "statistical_test": {"status": "success", "output": "stats_results.json"},
                        "visualization": {"status": "success", "output": "volcano.png"}
                    }
                },
                {
                    "hypothesis": "H2: 模型预测性能良好",
                    "steps": {
                        "model_training": {"status": "success", "output": "model.pkl"},
                        "model_evaluation": {"status": "success", "output": "model_eval.json"}
                    }
                }
            ]
        }
        
        # 写入假设结果
        with open(temp_path / "result" / "hypothesis_results.json", "w", encoding="utf-8") as f:
            json.dump(hypothesis_results, f, ensure_ascii=False, indent=2)
        
        # 创建可视化绑定
        visual_binding = {
            "bindings": [
                {"artifact": "volcano.png", "hypothesis": "H1"}
            ]
        }
        
        # 写入可视化绑定
        with open(temp_path / "result" / "visual_binding.json", "w", encoding="utf-8") as f:
            json.dump(visual_binding, f, ensure_ascii=False, indent=2)
        
        # 创建文档清单
        document_manifest = {
            "visualizations": [
                {
                    "name": "火山图",
                    "path": str(temp_path / "volcano.png"),
                    "relative_path": "volcano.png"
                }
            ],
            "tables": [],
            "plans": [
                {
                    "entries": [
                        {
                            "kind": "plan",
                            "path": str(temp_path / "plan" / "analysis_plan.md"),
                            "relative_path": "plan/analysis_plan.md"
                        }
                    ]
                }
            ]
        }
        
        # 创建报告载荷
        report_payload = {
            "title": "测试报告",
            "summary": "这是一份测试报告，用于验证证据链集成功能",
            "outline_mode": "structure_only"
        }
        
        # 创建报告汇编器
        assembler = ReportAssembler(language="zh")
        
        # 生成报告
        report = assembler.assemble(
            outline="",
            analysis_md="",
            document_manifest=document_manifest,
            report_payload=report_payload,
            execution_warning=""
        )
        
        # 验证报告内容
        assert "## 证据链闭环分析" in report
        assert "## 多维度证据整合" in report
        assert "## 敏感性分析" in report
        assert "## 深度研究计划" in report
        
        # 验证证据链分析内容
        assert "整体状态" in report
        assert "完整度评分" in report
        assert "冲突数量" in report
        
        # 验证多维度证据整合内容
        assert "整合证据数量" in report
        assert "证据网络节点数" in report
        assert "证据网络边数" in report
        assert "整体置信度" in report
        
        # 验证敏感性分析内容
        assert "稳定性评分" in report
        
        # 验证深度研究计划内容
        assert "建议研究方向数量" in report
        
        print("✓ 报告证据链集成测试通过")


if __name__ == "__main__":
    test_report_evidence_chain_integration()
