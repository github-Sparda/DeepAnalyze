from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

PHASES_WITH_CLOSURE = {
    "plan_analysis",
    "parallel_generation",
    "execution_guard",
    "code_repair",
    "analyze_results",
    "evidence_curation",
    "generate_visualizations",
    "report_outline",
    "generate_report",
    "finalize_run",
}

REQUIRED_PHASES = [
    "plan_analysis",
    "parallel_generation",
    "execution_guard",
    "analyze_results",
    "evidence_curation",
    "generate_report",
]


def ensure_phase_dirs(session_dir: Path) -> tuple[Path, Path]:
    closure_dir = session_dir / "meta" / "closure_status"
    recovery_dir = session_dir / "meta" / "recovery_trace"
    closure_dir.mkdir(parents=True, exist_ok=True)
    recovery_dir.mkdir(parents=True, exist_ok=True)
    return closure_dir, recovery_dir


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _ids_from(payload: dict[str, Any], key: str) -> set[str]:
    rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    result: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            continue
        raw = str(item.get(key, "")).strip().upper()
        match = re.search(r"\b(H\d+)\b", raw)
        if match:
            result.add(match.group(1))
    return result


def _active_plan_ids(session_dir: Path, merged_state: dict[str, Any]) -> set[str]:
    plan_json = merged_state.get("plan_json", {})
    if not isinstance(plan_json, dict) or not plan_json.get("hypotheses"):
        plan_json = _load_json(session_dir / "plan" / "analysis_plan.json")
    rows = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    ids: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("id", "")).strip().upper()
        if re.fullmatch(r"H\d+", raw):
            ids.add(raw)
    return ids


def _semantic_alignment_ok(session_dir: Path, merged_state: dict[str, Any]) -> tuple[bool, list[str]]:
    plan_ids = _active_plan_ids(session_dir, merged_state)
    if not plan_ids:
        return False, ["missing_plan_hypothesis_ids"]
    
    # 加载各模块的结果数据
    results_data = _load_json(session_dir / "result" / "hypothesis_results.json")
    multipath_data = _load_json(session_dir / "result" / "hypothesis_multipath.json")
    evidence_data = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    
    # 提取ID，增加容错处理
    result_ids = _ids_from(results_data, "hypothesis")
    multipath_ids = _ids_from(multipath_data, "hypothesis_id")
    evidence_ids = _ids_from(evidence_data, "hypothesis_id")
    
    # 检查数据结构一致性
    bad: list[str] = []
    
    # 检查结果数据结构
    if not isinstance(results_data, dict) or not isinstance(results_data.get("hypotheses"), list):
        bad.append("results_structure_invalid")
    
    # 检查多路径数据结构
    if not isinstance(multipath_data, dict) or not isinstance(multipath_data.get("hypotheses"), list):
        bad.append("multipath_structure_invalid")
    
    # 检查证据包数据结构
    if not isinstance(evidence_data, dict) or not isinstance(evidence_data.get("hypotheses"), list):
        bad.append("evidence_pack_structure_invalid")
    
    # 检查ID一致性
    for name, ids in (
        ("results", result_ids),
        ("multipath", multipath_ids),
        ("evidence_pack", evidence_ids),
    ):
        if ids and plan_ids and ids != plan_ids:
            # 如果ID不匹配，添加错误信息
            bad.append(f"{name}_ids_mismatch")
    
    return (len(bad) == 0, bad)


def _validate_evidence_completeness(session_dir: Path, hypothesis_id: str) -> dict[str, Any]:
    """验证证据的完整性"""
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    evidence = evidence_rows.get(hypothesis_id.upper(), {})
    quant_metrics = evidence.get("quant_metrics", {})
    evidence_sources = evidence.get("evidence_sources", [])
    hypothesis_type = evidence.get("hypothesis_type", "generic")
    
    # 检查证据维度，增加更多评估指标
    dimensions = {
        "statistical_significance": False,
        "effect_size": False,
        "robustness": False,
        "consistency": False,
        "evidence_diversity": False,
        "metric_quality": False,
        "source_quality": False
    }
    
    # 检查统计显著性
    if isinstance(quant_metrics, dict):
        if any(key in quant_metrics for key in ["p_value", "q_value", "significant_p_lt_0_05"]):
            dimensions["statistical_significance"] = True
        if any(key in quant_metrics for key in ["effect_size", "mean_diff", "cohen_d"]):
            dimensions["effect_size"] = True
        
        # 检查指标质量
        if len(quant_metrics) >= 3:
            dimensions["metric_quality"] = True
    
    # 检查稳健性
    if isinstance(evidence_sources, list) and len(evidence_sources) >= 2:
        dimensions["robustness"] = True
    
    # 检查一致性
    multipath = _load_json(session_dir / "result" / "hypothesis_multipath.json")
    multipath_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in multipath.get("hypotheses", [])
        if isinstance(row, dict)
    }
    multipath_data = multipath_rows.get(hypothesis_id.upper(), {})
    consistency = str(multipath_data.get("consistency", "")).lower()
    if consistency == "consistent":
        dimensions["consistency"] = True
    
    # 检查证据多样性
    if isinstance(evidence_sources, list):
        # 不同类型的证据源
        source_types = set()
        for source in evidence_sources:
            source_str = str(source)
            if ".json" in source_str:
                source_types.add("json")
            elif ".png" in source_str or ".jpg" in source_str or ".svg" in source_str:
                source_types.add("image")
            elif ".csv" in source_str:
                source_types.add("csv")
            elif ".md" in source_str:
                source_types.add("markdown")
        if len(source_types) >= 2:
            dimensions["evidence_diversity"] = True
    
    # 检查来源质量
    if isinstance(evidence_sources, list):
        # 计算高质量来源的数量
        high_quality_sources = 0
        for source in evidence_sources:
            source_str = str(source)
            # 认为结果文件和统计文件是高质量的
            if "result/" in source_str and (".json" in source_str or ".csv" in source_str):
                high_quality_sources += 1
        if high_quality_sources >= 2:
            dimensions["source_quality"] = True
    
    # 计算证据权重
    evidence_weights = calculate_evidence_weights(evidence_sources, quant_metrics, hypothesis_type)
    
    # 计算证据质量分数
    quality_score = calculate_evidence_quality_score(dimensions, evidence_weights)
    
    # 计算完整性分数
    completeness_score = sum(dimensions.values()) / len(dimensions) * 100
    
    return {
        "hypothesis_id": hypothesis_id,
        "dimensions": dimensions,
        "completeness_score": completeness_score,
        "quality_score": quality_score,
        "evidence_sources_count": len(evidence_sources),
        "quant_metrics_count": len(quant_metrics) if isinstance(quant_metrics, dict) else 0,
        "evidence_weights": evidence_weights,
        "evidence_diversity": len(set(str(source) for source in evidence_sources)) if isinstance(evidence_sources, list) else 0
    }


def calculate_evidence_weights(evidence_sources: list, quant_metrics: dict, hypothesis_type: str) -> dict[str, float]:
    """计算证据权重"""
    weights = {}
    
    # 基于证据源类型计算权重
    if isinstance(evidence_sources, list):
        for source in evidence_sources:
            source_str = str(source)
            weight = 1.0
            
            # 根据文件类型调整权重
            if ".json" in source_str:
                weight = 0.8
            elif ".png" in source_str or ".jpg" in source_str or ".svg" in source_str:
                weight = 0.6
            elif ".csv" in source_str:
                weight = 0.9
            elif ".md" in source_str:
                weight = 0.7
            
            # 根据路径调整权重
            if "stats" in source_str:
                weight *= 1.2
            elif "model" in source_str:
                weight *= 1.1
            elif "correlation" in source_str:
                weight *= 1.1
            
            weights[source_str] = weight
    
    # 基于量化指标调整权重
    if isinstance(quant_metrics, dict):
        # 根据假设类型调整权重
        if hypothesis_type == "difference":
            if "p_value" in quant_metrics:
                p_value = quant_metrics["p_value"]
                if p_value < 0.01:
                    for source in weights:
                        if "stats" in source:
                            weights[source] *= 1.3
                elif p_value < 0.05:
                    for source in weights:
                        if "stats" in source:
                            weights[source] *= 1.1
        
        elif hypothesis_type == "predictive":
            if "auc" in quant_metrics:
                auc = quant_metrics["auc"]
                if auc > 0.9:
                    for source in weights:
                        if "model" in source:
                            weights[source] *= 1.3
                elif auc > 0.8:
                    for source in weights:
                        if "model" in source:
                            weights[source] *= 1.1
        
        elif hypothesis_type == "correlation":
            if "strongest_abs_corr" in quant_metrics:
                corr = quant_metrics["strongest_abs_corr"]
                if corr > 0.8:
                    for source in weights:
                        if "correlation" in source:
                            weights[source] *= 1.3
                elif corr > 0.6:
                    for source in weights:
                        if "correlation" in source:
                            weights[source] *= 1.1
    
    return weights


def calculate_evidence_quality_score(dimensions: dict, evidence_weights: dict) -> float:
    """计算证据质量分数"""
    # 维度分数
    dimension_score = sum(dimensions.values()) / len(dimensions) * 50
    
    # 权重分数
    if evidence_weights:
        avg_weight = sum(evidence_weights.values()) / len(evidence_weights)
        weight_score = avg_weight * 50
    else:
        weight_score = 0
    
    # 总质量分数
    quality_score = dimension_score + weight_score
    
    return min(quality_score, 100)


def _detect_evidence_conflicts(session_dir: Path, hypothesis_id: str) -> dict[str, Any]:
    """检测证据冲突"""
    multipath = _load_json(session_dir / "result" / "hypothesis_multipath.json")
    multipath_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in multipath.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    multipath_data = multipath_rows.get(hypothesis_id.upper(), {})
    evidence_data = evidence_rows.get(hypothesis_id.upper(), {})
    
    consistency = str(multipath_data.get("consistency", "")).lower()
    conflict_reason = str(multipath_data.get("conflict_reason", ""))
    hypothesis_type = str(evidence_data.get("hypothesis_type", "generic")).lower()
    
    conflicts = []
    conflict_type = "none"
    
    # 检查多路径一致性冲突
    if consistency == "conflict":
        # 分析冲突类型
        if "p-value" in conflict_reason and "q-value" in conflict_reason:
            conflict_type = "statistical_conflict"
        elif "accuracy" in conflict_reason:
            conflict_type = "methodological_conflict"
        elif "corr" in conflict_reason:
            conflict_type = "correlation_conflict"
        elif "embedding" in conflict_reason:
            conflict_type = "embedding_conflict"
        else:
            conflict_type = "data_conflict"
        
        # 评估冲突严重程度
        severity = assess_conflict_severity(conflict_type, conflict_reason, hypothesis_type)
        
        conflicts.append({
            "type": conflict_type,
            "reason": conflict_reason,
            "severity": severity,
            "source": "multipath_consistency"
        })
    
    # 检查证据源冲突
    evidence_sources = evidence_data.get("evidence_sources", [])
    if isinstance(evidence_sources, list) and len(evidence_sources) > 0:
        # 检查证据源类型冲突
        source_types = set()
        for source in evidence_sources:
            source_str = str(source)
            if ".json" in source_str:
                source_types.add("json")
            elif ".png" in source_str or ".jpg" in source_str or ".svg" in source_str:
                source_types.add("image")
            elif ".csv" in source_str:
                source_types.add("csv")
            elif ".md" in source_str:
                source_types.add("markdown")
        
        # 如果只有一种类型的证据源，可能存在证据源单一的问题
        if len(source_types) == 1:
            conflicts.append({
                "type": "evidence_source_conflict",
                "reason": f"Only one type of evidence source found: {list(source_types)[0]}",
                "severity": "low",
                "source": "evidence_source_diversity"
            })
    
    # 检查量化指标冲突
    quant_metrics = evidence_data.get("quant_metrics", {})
    if isinstance(quant_metrics, dict) and len(quant_metrics) > 0:
        # 检查统计指标冲突
        if hypothesis_type == "difference":
            if "p_value" in quant_metrics and "q_value" in quant_metrics:
                p_value = quant_metrics["p_value"]
                q_value = quant_metrics["q_value"]
                if (p_value < 0.05 and q_value >= 0.05) or (p_value >= 0.05 and q_value < 0.05):
                    conflicts.append({
                        "type": "statistical_conflict",
                        "reason": f"p-value ({p_value}) and q-value ({q_value}) disagree on significance",
                        "severity": "high",
                        "source": "statistical_metrics"
                    })
        
        # 检查预测模型指标冲突
        elif hypothesis_type == "predictive":
            if "train_accuracy" in quant_metrics and "test_accuracy" in quant_metrics:
                train_acc = quant_metrics["train_accuracy"]
                test_acc = quant_metrics["test_accuracy"]
                if train_acc - test_acc > 0.2:
                    conflicts.append({
                        "type": "overfitting_conflict",
                        "reason": f"High overfitting detected: train accuracy ({train_acc}) vs test accuracy ({test_acc})",
                        "severity": "medium",
                        "source": "model_metrics"
                    })
            
            # 检查特征选择冲突
            if "feature_count" in quant_metrics and "feature_importance" in quant_metrics:
                feature_count = quant_metrics["feature_count"]
                feature_importance = quant_metrics["feature_importance"]
                if feature_count > 10:
                    # 计算低重要性特征的数量
                    low_importance_count = sum(1 for imp in feature_importance if imp < 0.1)
                    if low_importance_count > 3:
                        conflicts.append({
                            "type": "feature_selection_conflict",
                            "reason": "Too many features with low importance",
                            "severity": "medium",
                            "source": "feature_analysis"
                        })
        
        # 检查时间序列冲突
        elif hypothesis_type == "time_series":
            if "stationarity_p_value" in quant_metrics:
                stationarity_p_value = quant_metrics["stationarity_p_value"]
                if stationarity_p_value > 0.05:
                    conflicts.append({
                        "type": "time_series_conflict",
                        "reason": "Non-stationary time series detected",
                        "severity": "high",
                        "source": "time_series_analysis"
                    })
        
        # 检查因果推断冲突
        elif hypothesis_type == "causal":
            if "confounding_score" in quant_metrics:
                confounding_score = quant_metrics["confounding_score"]
                if confounding_score > 0.7:
                    conflicts.append({
                        "type": "causal_inference_conflict",
                        "reason": "High confounding detected",
                        "severity": "high",
                        "source": "causal_analysis"
                    })
    
    # 确定整体冲突类型
    if conflicts:
        # 按严重程度排序，取最严重的冲突类型
        conflicts.sort(key=lambda x: get_severity_score(x["severity"]), reverse=True)
        conflict_type = conflicts[0]["type"]
    
    return {
        "hypothesis_id": hypothesis_id,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "overall_conflict_type": conflict_type,
        "conflict_severity": conflicts[0]["severity"] if conflicts else "none"
    }


def assess_conflict_severity(conflict_type: str, conflict_reason: str, hypothesis_type: str) -> str:
    """评估冲突严重程度"""
    # 基于冲突类型的严重程度
    severity_map = {
        "statistical_conflict": "high",
        "methodological_conflict": "medium",
        "correlation_conflict": "medium",
        "embedding_conflict": "low",
        "data_conflict": "medium"
    }
    
    severity = severity_map.get(conflict_type, "medium")
    
    # 根据假设类型调整严重程度
    if hypothesis_type == "difference" and conflict_type == "statistical_conflict":
        # 差异检验中的统计冲突更为严重
        severity = "high"
    elif hypothesis_type == "predictive" and conflict_type == "methodological_conflict":
        # 预测模型中的方法冲突更为严重
        severity = "high"
    
    # 根据冲突原因调整严重程度
    if "p-value" in conflict_reason and "q-value" in conflict_reason:
        # p值和q值冲突通常较为严重
        severity = "high"
    elif "overfitting" in conflict_reason:
        # 过拟合问题较为严重
        severity = "high"
    
    return severity


def get_severity_score(severity: str) -> int:
    """获取严重程度分数"""
    score_map = {
        "high": 3,
        "medium": 2,
        "low": 1,
        "none": 0
    }
    return score_map.get(severity, 0)


def _generate_conflict_resolution(session_dir: Path, hypothesis_id: str, conflict: dict[str, Any]) -> dict[str, Any]:
    """生成智能冲突解决建议"""
    conflict_type = conflict.get("type", "")
    reason = conflict.get("reason", "")
    severity = conflict.get("severity", "medium")
    source = conflict.get("source", "unknown")
    
    # 加载相关数据以提供更智能的建议
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {}
    if isinstance(evidence_pack, dict):
        for row in evidence_pack.get("hypotheses", []):
            if isinstance(row, dict) and "hypothesis_id" in row:
                evidence_rows[str(row["hypothesis_id"]).strip().upper()] = row
    
    evidence_data = evidence_rows.get(hypothesis_id.upper(), {})
    hypothesis_type = str(evidence_data.get("hypothesis_type", "generic")).lower()
    quant_metrics = evidence_data.get("quant_metrics", {})
    user_preferences = evidence_data.get("user_preferences", {})
    resolution_history = evidence_data.get("resolution_history", [])
    
    # 智能生成解决建议
    resolutions = []
    
    if conflict_type == "statistical_conflict":
        # 基于具体统计指标生成建议
        if "p-value" in reason and "q-value" in reason:
            # 从量化指标中提取具体数值
            p_value = quant_metrics.get("p_value", None)
            q_value = quant_metrics.get("q_value", None)
            
            if p_value is not None and q_value is not None:
                if p_value < 0.05 and q_value >= 0.05:
                    resolutions = [
                        f"p值({p_value:.4f})显著但q值({q_value:.4f})不显著，建议使用更严格的多重检验校正方法",
                        "考虑使用Bonferroni校正或FDR控制",
                        "检查样本量是否足够，考虑增加样本",
                        "验证统计方法的选择是否适合当前数据分布",
                        "考虑使用非参数检验方法进行验证"
                    ]
                else:
                    resolutions = [
                        f"q值({q_value:.4f})显著但p值({p_value:.4f})不显著，建议检查多重检验校正方法",
                        "考虑使用更宽松的多重检验校正方法",
                        "验证数据是否存在异常值影响结果",
                        "检查统计假设是否满足",
                        "考虑使用自助法（bootstrap）验证结果"
                    ]
            else:
                resolutions = [
                    "使用q值作为最终显著性判断标准，因为它考虑了多重检验校正",
                    "调整显著性水平，例如使用Bonferroni校正",
                    "考虑使用更严格的统计方法，如 permutation test",
                    "增加样本量以提高统计功效",
                    "检查数据分布是否符合统计检验的假设条件"
                ]
        else:
            resolutions = [
                "考虑使用更严格的显著性水平",
                "执行多重检验校正",
                "增加样本量以提高统计功效",
                "考虑使用非参数检验方法",
                "检查数据预处理步骤是否正确"
            ]
    
    elif conflict_type == "methodological_conflict":
        # 基于假设类型生成建议
        if "accuracy" in reason.lower():
            if hypothesis_type == "predictive":
                train_acc = quant_metrics.get("train_accuracy", None)
                test_acc = quant_metrics.get("test_accuracy", None)
                
                if train_acc is not None and test_acc is not None:
                    acc_diff = train_acc - test_acc
                    if acc_diff > 0.2:
                        resolutions = [
                            f"模型准确率差异较大：训练({train_acc:.2f}) vs 测试({test_acc:.2f})，可能存在过拟合",
                            "尝试不同的建模方法，如随机森林、XGBoost等",
                            "调整模型参数，使用网格搜索或随机搜索优化",
                            "进行k折交叉验证以验证结果的稳定性",
                            "考虑使用集成方法提高模型性能"
                        ]
                    else:
                        resolutions = [
                            "尝试不同的建模方法，如随机森林、XGBoost等",
                            "调整模型参数，使用网格搜索或随机搜索优化",
                            "进行k折交叉验证以验证结果的稳定性",
                            "考虑使用集成方法提高模型性能",
                            "检查特征工程步骤是否合理"
                        ]
                else:
                    resolutions = [
                        "尝试不同的建模方法，如随机森林、XGBoost等",
                        "调整模型参数，使用网格搜索或随机搜索优化",
                        "进行k折交叉验证以验证结果的稳定性",
                        "考虑使用集成方法提高模型性能",
                        "检查特征工程步骤是否合理"
                    ]
            else:
                resolutions = [
                    "尝试不同的分析方法",
                    "调整方法参数设置",
                    "与领域专家讨论方法的适用性",
                    "考虑使用替代方法进行验证",
                    "详细记录方法选择的理由"
                ]
        else:
            resolutions = [
                "重新评估分析方法的选择",
                "检查方法参数设置是否合理",
                "与领域专家讨论方法的适用性",
                "考虑使用替代方法进行验证",
                "详细记录方法选择的理由"
            ]
    
    elif conflict_type == "correlation_conflict":
        # 基于相关性类型生成建议
        if "pearson" in reason.lower():
            resolutions = [
                "Pearson相关性对异常值敏感，建议检查并处理异常值",
                "考虑使用Spearman等级相关分析",
                "检查数据是否符合正态分布假设",
                "考虑使用偏相关分析控制其他变量的影响",
                "进行相关性的显著性检验"
            ]
        else:
            resolutions = [
                "检查相关性计算方法是否正确",
                "考虑使用不同的相关性度量方法（如Pearson、Spearman、Kendall）",
                "检查数据是否存在异常值影响相关性结果",
                "考虑使用偏相关分析控制其他变量的影响",
                "进行相关性的显著性检验"
            ]
    
    elif conflict_type == "embedding_conflict":
        # 基于降维方法生成建议
        if "tsne" in reason.lower() or "t-sne" in reason.lower():
            resolutions = [
                "调整t-SNE的perplexity参数（建议值：5-50）",
                "增加迭代次数以获得更稳定的结果",
                "尝试不同的距离度量方法",
                "考虑使用UMAP作为替代方法",
                "结合领域知识解释降维结果"
            ]
        elif "pca" in reason.lower():
            resolutions = [
                "检查数据是否已正确标准化",
                "分析主成分的解释方差比例",
                "考虑使用非线性降维方法",
                "验证特征选择是否合理",
                "结合领域知识解释主成分含义"
            ]
        else:
            resolutions = [
                "尝试不同的降维方法（如PCA、t-SNE、UMAP）",
                "调整降维参数，如t-SNE的perplexity值",
                "检查数据标准化步骤是否正确",
                "考虑使用不同的距离度量方法",
                "结合领域知识解释降维结果"
            ]
    
    elif conflict_type == "data_conflict":
        # 基于数据类型生成建议
        evidence_sources = evidence_data.get("evidence_sources", [])
        if isinstance(evidence_sources, list):
            csv_sources = [s for s in evidence_sources if ".csv" in str(s).lower()]
            if len(csv_sources) > 0:
                resolutions = [
                    "检查CSV数据的格式和编码是否正确",
                    "验证数据预处理步骤是否正确，如缺失值处理、异常值检测",
                    "检查数据类型转换是否正确",
                    "使用数据可视化工具检查数据分布",
                    "考虑数据标准化或归一化处理"
                ]
            else:
                resolutions = [
                    "检查数据预处理步骤是否正确",
                    "验证数据来源的一致性和可靠性",
                    "考虑数据质量问题，如缺失值、异常值等",
                    "进行数据清洗和标准化",
                    "使用数据可视化工具检查数据分布"
                ]
        else:
            resolutions = [
                "检查数据预处理步骤是否正确",
                "验证数据来源的一致性和可靠性",
                "考虑数据质量问题，如缺失值、异常值等",
                "进行数据清洗和标准化",
                "使用数据可视化工具检查数据分布"
            ]
    
    elif conflict_type == "evidence_source_conflict":
        # 基于证据源类型生成建议
        evidence_sources = evidence_data.get("evidence_sources", [])
        source_types = set()
        if isinstance(evidence_sources, list):
            for source in evidence_sources:
                source_str = str(source)
                if ".json" in source_str:
                    source_types.add("json")
                elif ".png" in source_str or ".jpg" in source_str or ".svg" in source_str:
                    source_types.add("image")
                elif ".csv" in source_str:
                    source_types.add("csv")
                elif ".md" in source_str:
                    source_types.add("markdown")
        
        if len(source_types) == 1:
            current_type = list(source_types)[0]
            missing_types = {"json", "image", "csv", "markdown"} - source_types
            if missing_types:
                resolutions = [
                    f"当前只有{current_type}类型的证据，建议增加以下类型的证据：{', '.join(missing_types)}",
                    "添加统计分析结果（JSON）以增强定量证据",
                    "添加可视化图表（Image）以提高直观性",
                    "添加原始数据（CSV）以支持可重复性",
                    "添加分析报告（Markdown）以提供详细解释"
                ]
            else:
                resolutions = [
                    "增加不同类型的证据源，如添加统计分析结果、可视化图表等",
                    "确保证据来源的多样性，包括定量和定性证据",
                    "验证所有证据源的可靠性和相关性",
                    "建立证据源的优先级和权重体系",
                    "详细记录每个证据源的获取方法和处理步骤"
                ]
        else:
            resolutions = [
                "确保证据来源的多样性，包括定量和定性证据",
                "验证所有证据源的可靠性和相关性",
                "建立证据源的优先级和权重体系",
                "详细记录每个证据源的获取方法和处理步骤",
                "考虑证据源之间的一致性和互补性"
            ]
    
    elif conflict_type == "overfitting_conflict":
        # 基于模型类型生成建议
        if hypothesis_type == "predictive":
            train_acc = quant_metrics.get("train_accuracy", None)
            test_acc = quant_metrics.get("test_accuracy", None)
            
            if train_acc is not None and test_acc is not None:
                acc_diff = train_acc - test_acc
                if acc_diff > 0.2:
                    resolutions = [
                        f"严重过拟合：训练准确率({train_acc:.2f})与测试准确率({test_acc:.2f})差异过大",
                        "强烈建议增加正则化项，如L1或L2正则化",
                        "使用更简单的模型架构",
                        "增加训练数据量或使用数据增强技术",
                        "考虑使用集成方法，如Bagging或Boosting"
                    ]
                elif acc_diff > 0.1:
                    resolutions = [
                        f"轻度过拟合：训练准确率({train_acc:.2f})与测试准确率({test_acc:.2f})存在差异",
                        "建议增加正则化项",
                        "使用交叉验证评估模型性能",
                        "考虑特征选择以减少模型复杂度",
                        "尝试不同的模型超参数"
                    ]
                else:
                    resolutions = [
                        "模型拟合良好，建议进行更全面的验证",
                        "使用交叉验证评估模型性能",
                        "考虑模型集成以提高性能",
                        "验证模型在不同数据集上的泛化能力",
                        "记录模型选择和评估过程"
                    ]
            else:
                resolutions = [
                    "增加正则化项，如L1或L2正则化",
                    "使用更简单的模型架构",
                    "增加训练数据量",
                    "使用交叉验证评估模型性能",
                    "考虑使用集成方法，如Bagging或Boosting"
                ]
        else:
            resolutions = [
                "检查分析方法是否过于复杂",
                "考虑使用更简单的模型或方法",
                "验证结果在不同数据集上的一致性",
                "与领域专家讨论方法选择的合理性",
                "记录分析过程和结果解释"
            ]
    
    elif conflict_type == "multipath_conflict":
        # 多路径冲突的解决建议
        resolutions = [
            "详细分析冲突原因，识别不同路径的差异",
            "检查各路径使用的方法和参数是否一致",
            "验证数据预处理步骤在各路径中是否相同",
            "考虑使用集成方法综合各路径的结果",
            "与领域专家讨论冲突的含义和可能的解决方案"
        ]
    
    elif conflict_type == "feature_selection_conflict":
        # 特征选择冲突的解决建议
        if "low importance" in reason.lower():
            resolutions = [
                "特征数量过多，存在多个低重要性特征",
                "建议使用特征选择算法（如LASSO、RFE等）减少特征数量",
                "考虑使用特征重要性阈值过滤低重要性特征",
                "尝试降维方法（如PCA）减少特征维度",
                "使用交叉验证评估特征选择对模型性能的影响"
            ]
        else:
            resolutions = [
                "优化特征选择策略",
                "使用多种特征选择方法进行比较",
                "考虑特征之间的相关性，避免冗余特征",
                "使用交叉验证评估特征选择的稳定性",
                "结合领域知识进行特征选择"
            ]
    
    elif conflict_type == "time_series_conflict":
        # 时间序列冲突的解决建议
        if "non-stationary" in reason.lower():
            resolutions = [
                "时间序列非平稳，建议进行差分处理",
                "考虑使用ARIMA模型处理非平稳时间序列",
                "尝试季节性调整方法",
                "使用单位根检验（如ADF检验）确认平稳性",
                "考虑使用指数平滑方法处理趋势和季节性"
            ]
        else:
            resolutions = [
                "优化时间序列模型参数",
                "考虑使用更复杂的时间序列模型（如LSTM、Prophet）",
                "检查时间序列数据的质量和完整性",
                "考虑添加外部变量作为预测因子",
                "使用滚动窗口验证模型性能"
            ]
    
    elif conflict_type == "causal_inference_conflict":
        # 因果推断冲突的解决建议
        if "confounding" in reason.lower():
            resolutions = [
                "存在高混淆因素，建议使用倾向得分匹配（PSM）",
                "考虑使用工具变量方法控制混淆",
                "使用双重差分（DID）方法减少混淆影响",
                "进行敏感性分析评估混淆因素的影响",
                "与领域专家讨论潜在的混淆因素"
            ]
        else:
            resolutions = [
                "优化因果推断方法",
                "考虑使用不同的因果推断框架",
                "验证因果假设的合理性",
                "进行稳健性检验",
                "详细记录因果推断的假设和局限性"
            ]
    
    else:
        # 通用建议
        resolutions = [
            "详细分析冲突原因",
            "与领域专家讨论冲突的含义",
            "考虑使用替代方法验证结果",
            "检查数据处理和分析步骤是否正确",
            "记录冲突及其解决过程"
        ]
    
    # 智能优先级调整
    priority = "medium"
    if severity == "high":
        priority = "high"
    elif severity == "low":
        priority = "low"
    # 基于假设类型和冲突来源调整优先级
    elif hypothesis_type == "predictive" and conflict_type in ["overfitting_conflict", "statistical_conflict"]:
        priority = "high"
    elif source == "multipath_consistency" and len(resolutions) > 3:
        priority = "high"
    
    # 基于用户偏好调整优先级
    if isinstance(user_preferences, dict):
        if user_preferences.get("priority") == "high":
            priority = "high"
    
    # 基于历史解决记录优化建议
    if isinstance(resolution_history, list) and resolution_history:
        # 查找成功的历史解决方法
        successful_resolutions = [r for r in resolution_history if r.get("success", False)]
        if successful_resolutions and conflict_type in [r.get("conflict_type") for r in successful_resolutions]:
            # 如果有相同类型的成功解决记录，调整建议顺序
            for r in successful_resolutions:
                if r.get("conflict_type") == conflict_type:
                    resolution_method = r.get("resolution", "")
                    if "regularization" in resolution_method.lower():
                        # 将正则化相关建议移到前面
                        regularization_suggestions = [s for s in resolutions if "正则化" in s]
                        if regularization_suggestions:
                            for suggestion in regularization_suggestions:
                                resolutions.remove(suggestion)
                                resolutions.insert(0, suggestion)
    
    # 添加冲突解决的具体步骤
    resolution_steps = {
        "hypothesis_id": hypothesis_id,
        "conflict_type": conflict_type,
        "conflict_reason": reason,
        "conflict_severity": severity,
        "conflict_source": source,
        "resolutions": resolutions,
        "priority": priority,
        "resolution_steps": [
            "确认冲突的具体原因和影响范围",
            "根据建议选择合适的解决方法",
            "实施解决方案并重新分析",
            "验证解决结果是否有效",
            "记录冲突解决过程和结果"
        ],
        "user_preferences": user_preferences,
        "resolution_history": resolution_history
    }
    
    return resolution_steps


def _classify_failure_type(
    phase: str,
    failed_checks: list[str],
    merged_state: dict[str, Any],
    error: str,
) -> str:
    text = " ".join(failed_checks + [str(error or "")]).lower()
    if "timeout" in text or "connection" in text or "service unavailable" in text:
        return "infrastructure"
    if "drift" in text or "mismatch" in text:
        return "semantic_drift"
    if "evidence" in text:
        return "evidence_insufficient"
    if "invalid" in text:
        return "artifact_invalid"
    if "missing" in text:
        return "artifact_missing"
    if phase in {"execution_guard", "code_repair"}:
        return "code_runtime"
    return "contract_violation"


def _status_payload(
    phase: str,
    status: str,
    failed_checks: list[str],
    merged_state: dict[str, Any],
    error: str = "",
    recoverable: bool = False,
    recovery_action: str = "",
    blocking: bool = False,
    notes: list[str] | None = None,
    waiver_reason: str = "",
    derived_from: list[str] | None = None,
) -> dict[str, Any]:
    retry_count = int(merged_state.get("execution_retry_count", 0) or 0)
    retry_limit = int((merged_state.get("config", {}) or {}).get("execution_failure_max_retries", 1) or 1)
    return {
        "phase": phase,
        "status": status,
        "failed_checks": failed_checks,
        "failure_type": _classify_failure_type(phase, failed_checks, merged_state, error),
        "recoverable": recoverable,
        "recovery_action": recovery_action,
        "retry_budget_remaining": max(0, retry_limit - retry_count),
        "blocking": blocking,
        "notes": notes or [],
        "waiver_reason": str(waiver_reason or "").strip(),
        "derived_from": [str(x).strip() for x in (derived_from or []) if str(x).strip()],
        "timestamp": int(time.time()),
    }


def evaluate_phase_closure(
    phase: str,
    session_dir: Path,
    merged_state: dict[str, Any],
    error: str = "",
) -> dict[str, Any] | None:
    if phase not in PHASES_WITH_CLOSURE:
        return None

    if phase == "plan_analysis":
        plan_json = merged_state.get("plan_json", {})
        rows = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
        failed: list[str] = []
        if len(rows) < 3:
            failed.append("hypothesis_count_lt_3")
        for idx, item in enumerate(rows):
            if not isinstance(item, dict):
                failed.append(f"hypothesis_{idx}_not_object")
                continue
            if not str(item.get("title", "")).strip():
                failed.append(f"{item.get('id', f'h{idx+1}')}_missing_title")
            if not str(item.get("hypothesis", "")).strip():
                failed.append(f"{item.get('id', f'h{idx+1}')}_missing_hypothesis_text")
            paths = item.get("validation_paths", [])
            if not isinstance(paths, list) or len(paths) < 2:
                failed.append(f"{item.get('id', f'h{idx+1}')}_validation_paths_lt_2")
        if not (session_dir / "plan" / "analysis_plan.md").exists():
            failed.append("analysis_plan_md_missing")
        if not (session_dir / "plan" / "analysis_plan.json").exists():
            failed.append("analysis_plan_json_missing")
        if failed:
            return _status_payload(
                phase,
                "recoverable_failed",
                failed,
                merged_state,
                error=error,
                recoverable=True,
                recovery_action="repair_plan_schema_and_rerun",
                blocking=True,
            )
        recovered = bool(merged_state.get("llm_degradation_events")) and bool(rows)
        return _status_payload(
            phase,
            "recovered" if recovered else "success",
            [],
            merged_state,
            notes=["deterministic_plan_fallback"] if recovered else [],
        )

    if phase == "parallel_generation":
        if merged_state.get("codegen_skipped"):
            return _status_payload(
                phase,
                "skipped",
                ["codegen_skipped_due_to_quality_gate"],
                merged_state,
                recoverable=False,
                recovery_action="restore_codegen_capability_then_rerun",
                blocking=True,
            )
        steps = merged_state.get("code_steps", []) if isinstance(merged_state.get("code_steps", []), list) else []
        failed: list[str] = []
        if not steps:
            failed.append("missing_codegen_steps")
        names: set[str] = set()
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                failed.append(f"step_{idx}_not_object")
                continue
            name = str(step.get("name", "")).strip()
            path = str(step.get("path", "")).strip()
            if not name:
                failed.append(f"step_{idx}_missing_name")
            elif name in names:
                failed.append(f"{name}_duplicate_name")
            else:
                names.add(name)
            if not path or not Path(path).exists():
                failed.append(f"{name or f'step_{idx}'}_script_missing")
        if failed:
            return _status_payload(
                phase,
                "recoverable_failed",
                failed,
                merged_state,
                recoverable=True,
                recovery_action="rerun_codegen_for_failed_steps",
                blocking=True,
            )
        return _status_payload(phase, "success", [], merged_state)

    if phase == "execution_guard":
        failures = merged_state.get("execution_errors", []) if isinstance(merged_state.get("execution_errors", []), list) else []
        if failures:
            requested = bool(merged_state.get("execution_retry_requested", False))
            exhausted = bool(merged_state.get("execution_retry_exhausted", False))
            step_names = [str(item.get("step", "unknown")) for item in failures if isinstance(item, dict)]
            if requested:
                return _status_payload(
                    phase,
                    "recoverable_failed",
                    [f"failed_steps:{','.join(step_names)}"],
                    merged_state,
                    recoverable=True,
                    recovery_action="invoke_code_repair_then_rerun",
                    blocking=True,
                )
            return _status_payload(
                phase,
                "failed" if exhausted else "recoverable_failed",
                [f"failed_steps:{','.join(step_names)}"],
                merged_state,
                recoverable=not exhausted,
                recovery_action="manual_runtime_debug_required" if exhausted else "invoke_code_repair_then_rerun",
                blocking=True,
            )
        recovered = int(merged_state.get("execution_retry_count", 0) or 0) > 0
        return _status_payload(phase, "recovered" if recovered else "success", [], merged_state)

    if phase == "code_repair":
        if merged_state.get("code_repair_skipped"):
            return _status_payload(
                phase,
                "skipped",
                ["code_repair_skipped_due_to_quality_gate"],
                merged_state,
                recoverable=False,
                recovery_action="restore_llm_then_retry_failed_steps",
                blocking=True,
            )
        if not merged_state.get("code_repair_ran"):
            return _status_payload(phase, "success", [], merged_state, notes=["repair_not_required"])
        exec_results = merged_state.get("exec_results", []) if isinstance(merged_state.get("exec_results", []), list) else []
        failed = [
            str(row.get("step", "unknown"))
            for row in exec_results
            if isinstance(row, dict) and isinstance(row.get("statuses"), list) and row.get("statuses") and row["statuses"][-1] == "error"
        ]
        if failed:
            return _status_payload(
                phase,
                "failed",
                [f"repair_failed_steps:{','.join(failed)}"],
                merged_state,
                recoverable=False,
                recovery_action="manual_runtime_debug_required",
                blocking=True,
            )
        return _status_payload(phase, "recovered", [], merged_state)

    if phase == "analyze_results":
        required = [
            session_dir / "result" / "analysis_results.md",
            session_dir / "result" / "hypothesis_results.json",
            session_dir / "result" / "hypothesis_evidence.json",
            session_dir / "result" / "hypothesis_contrast.json",
            session_dir / "result" / "hypothesis_multipath.json",
            session_dir / "result" / "hypothesis_validation_contract.json",
            session_dir / "result" / "path_execution_status.json",
        ]
        failed = [f"missing:{path.name}" for path in required if not path.exists()]
        if not str(merged_state.get("docs_analysis_results", "")).strip():
            failed.append("missing_docs_analysis_results")
        if failed:
            return _status_payload(
                phase,
                "recoverable_failed",
                failed,
                merged_state,
                recoverable=True,
                recovery_action="rebuild_analysis_artifacts_and_rerun",
                blocking=True,
            )
        return _status_payload(phase, "success", [], merged_state)

    if phase == "evidence_curation":
        failed = []
        required = [
            session_dir / "result" / "hypothesis_evidence_pack.json",
            session_dir / "result" / "hypothesis_gate_report.json",
            session_dir / "result" / "hypothesis_evidence_pack_validation.json",
        ]
        failed.extend([f"missing:{path.name}" for path in required if not path.exists()])
        validation = merged_state.get("hypothesis_evidence_pack_validation", {})
        if not isinstance(validation, dict) or not bool(validation.get("valid", False)):
            failed.append("invalid_evidence_pack")
        ok, mismatch = _semantic_alignment_ok(session_dir, merged_state)
        if not ok:
            failed.extend(mismatch)
        if failed:
            return _status_payload(
                phase,
                "recoverable_failed",
                failed,
                merged_state,
                recoverable=True,
                recovery_action="repair_evidence_binding_and_sync_hypotheses",
                blocking=True,
            )
        return _status_payload(phase, "success", [], merged_state)

    if phase == "generate_visualizations":
        plan = merged_state.get("visualization_plan", []) if isinstance(merged_state.get("visualization_plan", []), list) else []
        rendered = merged_state.get("visualizations", []) if isinstance(merged_state.get("visualizations", []), list) else []
        if not plan:
            return _status_payload(phase, "success", [], merged_state, notes=["no_visualization_plan"])
        failed = []
        if not rendered:
            failed.append("visualizations_not_rendered")
        for idx, entry in enumerate(rendered):
            if not isinstance(entry, dict):
                failed.append(f"rendered_{idx}_not_object")
                continue
            path = str(entry.get("path", "")).strip()
            meta = entry.get("metadata", {})
            if not path or not Path(path).exists():
                failed.append(f"rendered_{idx}_path_missing")
            if not isinstance(meta, dict):
                failed.append(f"rendered_{idx}_metadata_missing")
                continue
            if not str(meta.get("type", "")).strip():
                failed.append(f"rendered_{idx}_type_missing")
            if not str(meta.get("dataset_path", "")).strip():
                failed.append(f"rendered_{idx}_dataset_path_missing")
        if failed:
            return _status_payload(
                phase,
                "recoverable_failed",
                failed,
                merged_state,
                recoverable=True,
                recovery_action="rerender_missing_visualizations_and_metadata",
                blocking=True,
            )
        return _status_payload(phase, "success", [], merged_state)

    if phase == "report_outline":
        outline = str(merged_state.get("report_outline", "")).strip()
        if not outline:
            return _status_payload(
                phase,
                "recoverable_failed",
                ["report_outline_missing"],
                merged_state,
                recoverable=True,
                recovery_action="regenerate_report_outline",
                blocking=True,
            )
        return _status_payload(phase, "success", [], merged_state)

    if phase == "generate_report":
        versions = merged_state.get("report_versions", []) if isinstance(merged_state.get("report_versions", []), list) else []
        report_text = str(merged_state.get("report", "")).strip()
        failed = []
        if not versions:
            failed.append("report_version_missing")
        if not report_text:
            failed.append("report_body_missing")
        if "报告已跳过生成" in report_text:
            failed.append("report_generation_skipped")
        waiver = merged_state.get("report_generation_waiver", {})
        waiver_allowed = isinstance(waiver, dict) and bool(waiver.get("allow", False))
        completion = merged_state.get("completion_validation", {})
        if isinstance(completion, dict) and not bool(completion.get("complete", False)) and not waiver_allowed:
            failed.append("completion_validation_incomplete")
        if failed:
            return _status_payload(
                phase,
                "failed",
                failed,
                merged_state,
                recoverable=False,
                recovery_action="resolve_blockers_before_report_generation",
                blocking=True,
            )
        if waiver_allowed:
            return _status_payload(
                phase,
                "success",
                [],
                merged_state,
                notes=["report_generated_with_explicit_waiver"],
                waiver_reason=str(waiver.get("reason", "")).strip(),
                derived_from=[str(x) for x in (waiver.get("derived_from", []) if isinstance(waiver.get("derived_from"), list) else [])],
            )
        return _status_payload(phase, "success", [], merged_state)

    if phase == "finalize_run":
        failed = []
        for rel in ("meta/run_audit.json", "meta/completion_validation.json", "summary.json"):
            if not (session_dir / rel).exists():
                failed.append(f"missing:{Path(rel).name}")
        if failed:
            return _status_payload(
                phase,
                "recoverable_failed",
                failed,
                merged_state,
                recoverable=True,
                recovery_action="rebuild_audit_and_summary",
                blocking=True,
            )
        return _status_payload(phase, "success", [], merged_state)

    return None


def persist_phase_closure(session_dir: Path, closure: dict[str, Any]) -> None:
    closure_dir, recovery_dir = ensure_phase_dirs(session_dir)
    phase = str(closure.get("phase", "")).strip()
    if not phase:
        return
    path = closure_dir / f"{phase}.json"
    path.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")
    if closure.get("status") in {"recoverable_failed", "failed", "skipped"}:
        trace = {
            "phase": phase,
            "status": closure.get("status"),
            "failed_checks": closure.get("failed_checks", []),
            "failure_type": closure.get("failure_type", ""),
            "recoverable": closure.get("recoverable", False),
            "recovery_action": closure.get("recovery_action", ""),
            "blocking": closure.get("blocking", False),
            "waiver_reason": closure.get("waiver_reason", ""),
            "derived_from": closure.get("derived_from", []),
            "timestamp": closure.get("timestamp", int(time.time())),
        }
        (recovery_dir / f"{phase}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_phase_closure_map(session_dir: Path) -> dict[str, dict[str, Any]]:
    closure_dir = session_dir / "meta" / "closure_status"
    if not closure_dir.exists():
        return {}
    payload: dict[str, dict[str, Any]] = {}
    for path in sorted(closure_dir.glob("*.json")):
        data = _load_json(path)
        if data:
            payload[path.stem] = data
    return payload


def build_phase_blockers(closure_map: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    blockers: dict[str, list[str]] = {}
    for phase, payload in closure_map.items():
        if not isinstance(payload, dict):
            continue
        if payload.get("blocking"):
            failed_checks = payload.get("failed_checks", [])
            blockers[phase] = [str(item) for item in failed_checks if str(item).strip()]
    return blockers


def closure_completion_summary(closure_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required_missing = [phase for phase in REQUIRED_PHASES if phase not in closure_map]
    incomplete_required = [
        phase
        for phase in REQUIRED_PHASES
        if phase in closure_map and str(closure_map[phase].get("status", "")).strip() not in {"success", "recovered"}
    ]
    blocking_required = [
        phase
        for phase in REQUIRED_PHASES
        if phase in closure_map and bool(closure_map[phase].get("blocking", False))
    ]
    return {
        "required_missing": required_missing,
        "incomplete_required": incomplete_required,
        "blocking_required": blocking_required,
        "complete": not required_missing and not incomplete_required and not blocking_required,
    }


def evaluate_evidence_chain_closure(session_dir: Path, merged_state: dict[str, Any]) -> dict[str, Any]:
    """评估整个证据链的闭环状态"""
    plan_json = merged_state.get("plan_json", {}) if isinstance(merged_state.get("plan_json", {}), dict) else {}
    if not plan_json:
        plan_json = _load_json(session_dir / "plan" / "analysis_plan.json")
    
    # 获取配置的阈值，默认为80和50
    config = merged_state.get("config", {}) if isinstance(merged_state.get("config"), dict) else {}
    closure_config = config.get("closure", {}) if isinstance(config.get("closure"), dict) else {}
    complete_threshold = closure_config.get("complete_threshold", 80)
    partial_threshold = closure_config.get("partial_threshold", 50)
    
    plan_rows = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    hypothesis_ids = [str(item.get("id", f"H{idx+1}")).strip().upper() for idx, item in enumerate(plan_rows) if isinstance(item, dict)]
    
    evidence_chain_status = {
        "hypotheses": [],
        "summary": {
            "total_hypotheses": len(hypothesis_ids),
            "complete_hypotheses": 0,
            "partial_hypotheses": 0,
            "failed_hypotheses": 0,
            "average_completeness_score": 0,
            "conflict_count": 0,
            "overall_status": "incomplete",
            "thresholds": {
                "complete": complete_threshold,
                "partial": partial_threshold
            }
        }
    }
    
    total_completeness_score = 0
    complete_count = 0
    partial_count = 0
    failed_count = 0
    total_conflicts = 0
    
    for hypothesis_id in hypothesis_ids:
        # 验证证据完整性
        completeness = _validate_evidence_completeness(session_dir, hypothesis_id)
        
        # 检测证据冲突
        conflicts = _detect_evidence_conflicts(session_dir, hypothesis_id)
        
        # 生成冲突解决建议
        conflict_resolutions = []
        for conflict in conflicts.get("conflicts", []):
            resolution = _generate_conflict_resolution(session_dir, hypothesis_id, conflict)
            conflict_resolutions.append(resolution)
        
        # 确定假设的状态
        if completeness.get("completeness_score", 0) >= complete_threshold and conflicts.get("conflict_count", 0) == 0:
            status = "complete"
            complete_count += 1
        elif completeness.get("completeness_score", 0) >= partial_threshold:
            status = "partial"
            partial_count += 1
        else:
            status = "failed"
            failed_count += 1
        
        total_completeness_score += completeness.get("completeness_score", 0)
        total_conflicts += conflicts.get("conflict_count", 0)
        
        evidence_chain_status["hypotheses"].append({
            "hypothesis_id": hypothesis_id,
            "status": status,
            "completeness": completeness,
            "conflicts": conflicts,
            "conflict_resolutions": conflict_resolutions
        })
    
    # 更新摘要
    if hypothesis_ids:
        evidence_chain_status["summary"]["average_completeness_score"] = total_completeness_score / len(hypothesis_ids)
    evidence_chain_status["summary"]["complete_hypotheses"] = complete_count
    evidence_chain_status["summary"]["partial_hypotheses"] = partial_count
    evidence_chain_status["summary"]["failed_hypotheses"] = failed_count
    evidence_chain_status["summary"]["conflict_count"] = total_conflicts
    
    # 确定整体状态
    if complete_count == len(hypothesis_ids):
        evidence_chain_status["summary"]["overall_status"] = "complete"
    elif complete_count + partial_count == len(hypothesis_ids):
        evidence_chain_status["summary"]["overall_status"] = "partial"
    else:
        evidence_chain_status["summary"]["overall_status"] = "failed"
    
    return evidence_chain_status
