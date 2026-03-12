from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_research_digest(session_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    plan_json = state.get("plan_json", {}) if isinstance(state.get("plan_json", {}), dict) else {}
    if not plan_json:
        plan_json = _load_json(session_dir / "plan" / "analysis_plan.json")
    gate_payload = state.get("hypothesis_gate_report", {}) if isinstance(state.get("hypothesis_gate_report", {}), dict) else {}
    if not gate_payload:
        gate_payload = _load_json(session_dir / "result" / "hypothesis_gate_report.json")
    evidence_pack = state.get("hypothesis_evidence_pack", {}) if isinstance(state.get("hypothesis_evidence_pack", {}), dict) else {}
    if not evidence_pack:
        evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    path_execution = _load_json(session_dir / "result" / "path_execution_status.json")
    multipath = state.get("hypothesis_multipath", {}) if isinstance(state.get("hypothesis_multipath", {}), dict) else _load_json(session_dir / "result" / "hypothesis_multipath.json")
    hypothesis_results = _load_json(session_dir / "result" / "hypothesis_results.json")
    closure_status = state.get("closure_status", {}) if isinstance(state.get("closure_status", {}), dict) else {}

    plan_rows = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
    gate_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in gate_payload.get("hypotheses", [])
        if isinstance(row, dict)
    }
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    path_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in path_execution.get("hypotheses", [])
        if isinstance(row, dict)
    }
    multipath_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in multipath.get("hypotheses", [])
        if isinstance(row, dict)
    }
    result_title_map: dict[str, str] = {}
    for row in hypothesis_results.get("hypotheses", []) if isinstance(hypothesis_results, dict) else []:
        if not isinstance(row, dict):
            continue
        raw = str(row.get("hypothesis", "")).strip()
        if ":" not in raw:
            continue
        prefix, suffix = raw.split(":", 1)
        hid = str(prefix).strip().upper()
        title = str(suffix).strip()
        if hid and title:
            result_title_map[hid] = title

    hypotheses: list[dict[str, Any]] = []
    stable_findings: list[dict[str, Any]] = []
    unresolved_candidates: list[dict[str, Any]] = []
    unique_evidence_sources: set[str] = set()
    for idx, item in enumerate(plan_rows):
        if not isinstance(item, dict):
            continue
        hid = str(item.get("id", f"H{idx+1}")).strip().upper()
        title = str(item.get("title", hid)).strip() or hid
        if result_title_map.get(hid):
            title = result_title_map[hid]
        gate = gate_rows.get(hid, {})
        evidence = evidence_rows.get(hid, {})
        path_status = path_rows.get(hid, {})
        multipath_row = multipath_rows.get(hid, {})
        quant_metrics = evidence.get("quant_metrics", [])
        quant_metric_count = (
            len([m for m in quant_metrics if isinstance(m, dict) and str(m.get("name", "")).strip()])
            if isinstance(quant_metrics, list)
            else len([k for k in (quant_metrics or {}).keys() if str(k).strip()])
            if isinstance(quant_metrics, dict)
            else 0
        )
        overall = str(path_status.get("overall", "")).strip().lower()
        gate_status = str(gate.get("gate_status", "")).strip().lower()
        consistency = str(multipath_row.get("consistency", "")).strip().lower()
        reason_code = str(gate.get("reason_code", "") or evidence.get("reason_code", "")).strip()
        missing_artifacts = path_status.get("missing_artifacts", []) if isinstance(path_status.get("missing_artifacts"), list) else []
        summary = {
            "hypothesis_id": hid,
            "title": title,
            "gate_status": gate_status or "unknown",
            "path_overall": overall or "unknown",
            "consistency": consistency or "unknown",
            "reason_code": reason_code,
            "quant_metric_count": quant_metric_count,
            "missing_artifact_count": len(missing_artifacts),
            "missing_artifacts": [str(x) for x in missing_artifacts[:6]],
            "key_metrics": (
                [m for m in quant_metrics[:4] if isinstance(m, dict)]
                if isinstance(quant_metrics, list)
                else [{"name": k, "value": v} for k, v in list((quant_metrics or {}).items())[:4]]
                if isinstance(quant_metrics, dict)
                else []
            ),
            "evidence_sources": [str(x) for x in (evidence.get("evidence_sources", []) if isinstance(evidence.get("evidence_sources"), list) else [])[:4]],
        }
        for source in summary["evidence_sources"]:
            if str(source).strip():
                unique_evidence_sources.add(str(source).strip())
        hypotheses.append(summary)
        if gate_status == "pass" and overall == "complete":
            stable_findings.append(summary)
        else:
            unresolved_candidates.append(summary)

    blocking_phases = [
        phase
        for phase, payload in closure_status.items()
        if isinstance(payload, dict) and bool(payload.get("blocking", False))
    ]
    digest = {
        "depth": int(state.get("depth", 1) or 1),
        "iteration_count": int(state.get("iteration_count", 1) or 1),
        "hypotheses": hypotheses,
        "stable_findings": stable_findings,
        "unresolved_candidates": unresolved_candidates,
        "blocking_phases": blocking_phases,
        "summary": {
            "total_hypotheses": len(hypotheses),
            "stable_count": len(stable_findings),
            "unresolved_count": len(unresolved_candidates),
            "blocking_phase_count": len(blocking_phases),
            "unique_evidence_source_count": len(unique_evidence_sources),
        },
    }
    return digest


def render_research_digest_markdown(digest: dict[str, Any]) -> str:
    lines = ["# Research Digest", ""]
    summary = digest.get("summary", {}) if isinstance(digest.get("summary"), dict) else {}
    lines.append(
        f"- total_hypotheses={summary.get('total_hypotheses', 0)}; "
        f"stable_count={summary.get('stable_count', 0)}; "
        f"unresolved_count={summary.get('unresolved_count', 0)}; "
        f"blocking_phase_count={summary.get('blocking_phase_count', 0)}"
    )
    lines.append("")
    lines.append("## Unresolved Candidates")
    for row in digest.get("unresolved_candidates", [])[:5]:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('hypothesis_id')}: {row.get('title')} | gate={row.get('gate_status')} | "
            f"path={row.get('path_overall')} | consistency={row.get('consistency')} | "
            f"reason={row.get('reason_code') or 'none'} | missing={row.get('missing_artifact_count', 0)}"
        )
    lines.append("")
    lines.append("## Stable Findings")
    for row in digest.get("stable_findings", [])[:5]:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('hypothesis_id')}: {row.get('title')} | gate={row.get('gate_status')} | "
            f"path={row.get('path_overall')} | metrics={row.get('quant_metric_count', 0)}"
        )
    lines.append("")
    if digest.get("blocking_phases"):
        lines.append("## Blocking Phases")
        for phase in digest.get("blocking_phases", []):
            lines.append(f"- {phase}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def select_depth_focus(digest: dict[str, Any], max_candidates: int = 3) -> dict[str, Any]:
    unresolved = digest.get("unresolved_candidates", []) if isinstance(digest.get("unresolved_candidates"), list) else []
    stable = digest.get("stable_findings", []) if isinstance(digest.get("stable_findings"), list) else []
    closure_candidates: list[dict[str, Any]] = []
    for row in unresolved:
        if not isinstance(row, dict):
            continue
        score = 0
        if str(row.get("gate_status", "")).strip().lower() in {"partial", "fail"}:
            score += 40
        if str(row.get("path_overall", "")).strip().lower() == "incomplete":
            score += 20
        if str(row.get("consistency", "")).strip().lower() == "conflict":
            score += 15
        score += min(int(row.get("quant_metric_count", 0) or 0), 4) * 5
        missing_count = int(row.get("missing_artifact_count", 0) or 0)
        score += 10 if 0 < missing_count <= 3 else 0
        closure_candidates.append(
            {
                **row,
                "score": score,
                "mode": "closure_followup",
                "why": "首轮未闭环但已有定量证据，优先补齐缺失路径/冲突/产物。",
            }
        )
    closure_candidates.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("hypothesis_id", ""))))
    closure_candidates = closure_candidates[:max_candidates]

    def _has_explicit_extension_space(row: dict[str, Any]) -> bool:
        consistency = str(row.get("consistency", "")).strip().lower()
        reason_code = str(row.get("reason_code", "")).strip().lower()
        if consistency == "conflict":
            return True
        if any(token in reason_code for token in ["robust", "mechanism", "generalization", "instability", "extension"]):
            return True
        return False

    escalated_candidates: list[dict[str, Any]] = []
    if not closure_candidates:
        for row in stable:
            if not isinstance(row, dict):
                continue
            if not _has_explicit_extension_space(row):
                continue
            score = 20 + min(int(row.get("quant_metric_count", 0) or 0), 4) * 5
            escalated_candidates.append(
                {
                    **row,
                    "score": score,
                    "mode": "escalated_research",
                    "why": "首轮已有稳定发现，可继续做稳健性/机制/替代方法扩展。",
                }
            )
        escalated_candidates.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("hypothesis_id", ""))))
        escalated_candidates = escalated_candidates[:1]

    selected = closure_candidates if closure_candidates else escalated_candidates
    return {
        "mode": selected[0]["mode"] if selected else "stop",
        "selected": selected,
        "reason": "has_prioritized_targets" if selected else "no_material_depth_gain_space",
    }


def build_depth_delta(previous_digest: dict[str, Any], current_digest: dict[str, Any], current_focus: dict[str, Any] | None = None) -> dict[str, Any]:
    prev_summary = previous_digest.get("summary", {}) if isinstance(previous_digest.get("summary"), dict) else {}
    curr_summary = current_digest.get("summary", {}) if isinstance(current_digest.get("summary"), dict) else {}
    prev_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in previous_digest.get("hypotheses", [])
        if isinstance(row, dict) and str(row.get("hypothesis_id", "")).strip()
    }
    curr_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in current_digest.get("hypotheses", [])
        if isinstance(row, dict) and str(row.get("hypothesis_id", "")).strip()
    }
    selected_targets = [
        str(row.get("hypothesis_id", "")).strip().upper()
        for row in (current_focus or {}).get("selected", [])
        if isinstance(row, dict) and str(row.get("hypothesis_id", "")).strip()
    ]
    matched_targets = [target for target in selected_targets if target in prev_rows and target in curr_rows] or [
        hid for hid in curr_rows.keys() if hid in prev_rows
    ]
    target_improvements = []
    for hid in matched_targets:
        prev_row = prev_rows.get(hid, {})
        curr_row = curr_rows.get(hid, {})
        prev_closed = str(prev_row.get("gate_status", "")).lower() == "pass" and str(prev_row.get("path_overall", "")).lower() == "complete"
        curr_closed = str(curr_row.get("gate_status", "")).lower() == "pass" and str(curr_row.get("path_overall", "")).lower() == "complete"
        prev_missing = int(prev_row.get("missing_artifact_count", 0) or 0)
        curr_missing = int(curr_row.get("missing_artifact_count", 0) or 0)
        if curr_closed and not prev_closed:
            target_improvements.append({"hypothesis_id": hid, "type": "closed"})
        elif curr_missing < prev_missing:
            target_improvements.append(
                {
                    "hypothesis_id": hid,
                    "type": "missing_artifacts_reduced",
                    "previous_missing": prev_missing,
                    "current_missing": curr_missing,
                }
            )
    delta = {
        "previous_depth": previous_digest.get("depth"),
        "current_depth": current_digest.get("depth"),
        "stable_count_delta": int(curr_summary.get("stable_count", 0) or 0) - int(prev_summary.get("stable_count", 0) or 0),
        "unresolved_count_delta": int(curr_summary.get("unresolved_count", 0) or 0) - int(prev_summary.get("unresolved_count", 0) or 0),
        "blocking_phase_count_delta": int(curr_summary.get("blocking_phase_count", 0) or 0) - int(prev_summary.get("blocking_phase_count", 0) or 0),
        "unique_evidence_source_count_delta": int(curr_summary.get("unique_evidence_source_count", 0) or 0) - int(prev_summary.get("unique_evidence_source_count", 0) or 0),
        "selected_mode": (current_focus or {}).get("mode", ""),
        "selected_targets": [row.get("hypothesis_id") for row in (current_focus or {}).get("selected", []) if isinstance(row, dict)],
        "matched_targets": matched_targets,
        "target_improvements": target_improvements,
    }
    improved = (
        len(target_improvements) > 0
        or delta["stable_count_delta"] > 0
        or delta["blocking_phase_count_delta"] < 0
        or delta["unique_evidence_source_count_delta"] > 0
    )
    delta["material_gain"] = bool(improved)
    if improved:
        delta["summary"] = "第二轮相对首轮带来了实质增益。"
    else:
        delta["summary"] = "第二轮未带来实质深度增益。"
    return delta


def integrate_multidimensional_evidence(session_dir: Path, hypothesis_id: str) -> dict[str, Any]:
    """整合多维度证据（支持多模态数据）"""
    # 加载证据数据
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    evidence = evidence_rows.get(hypothesis_id.upper(), {})
    quant_metrics = evidence.get("quant_metrics", {})
    evidence_sources = evidence.get("evidence_sources", [])
    
    # 加载多路径数据
    multipath = _load_json(session_dir / "result" / "hypothesis_multipath.json")
    multipath_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in multipath.get("hypotheses", [])
        if isinstance(row, dict)
    }
    multipath_data = multipath_rows.get(hypothesis_id.upper(), {})
    
    # 计算证据权重
    evidence_weights = calculate_evidence_weights(evidence_sources, quant_metrics)
    
    # 构建证据网络
    evidence_network = build_evidence_network(session_dir, hypothesis_id)
    
    # 分析多模态数据
    multimodal_analysis = analyze_multimodal_data(evidence_sources, quant_metrics, evidence_network)
    
    # 整合证据
    integrated_evidence = {
        "hypothesis_id": hypothesis_id,
        "evidence_sources": evidence_sources,
        "quant_metrics": quant_metrics,
        "evidence_weights": evidence_weights,
        "evidence_network": evidence_network,
        "multipath_consistency": multipath_data.get("consistency", "unknown"),
        "confidence_score": calculate_confidence_score(evidence_weights, multipath_data),
        "multimodal_analysis": multimodal_analysis
    }
    
    return integrated_evidence


def calculate_evidence_weights(evidence_sources: list, quant_metrics: dict) -> dict[str, float]:
    """计算证据权重（支持动态权重调整）"""
    weights = {}
    
    # 基于证据源类型计算权重
    for source in evidence_sources:
        source_str = str(source)
        weight = 1.0
        
        # 根据文件类型调整权重（多模态支持）
        if ".json" in source_str:
            weight = 0.8
        elif ".png" in source_str or ".jpg" in source_str or ".jpeg" in source_str or ".svg" in source_str:
            weight = 0.7  # 提高图像证据权重
        elif ".csv" in source_str or ".tsv" in source_str:
            weight = 0.9
        elif ".md" in source_str or ".txt" in source_str:
            weight = 0.6  # 文本证据权重
        elif ".pdf" in source_str:
            weight = 0.7  # PDF文档权重
        elif ".wav" in source_str or ".mp3" in source_str:
            weight = 0.6  # 音频证据权重
        
        # 根据路径调整权重
        if "stats" in source_str:
            weight *= 1.2
        elif "model" in source_str:
            weight *= 1.1
        elif "text" in source_str:
            weight *= 0.9
        elif "image" in source_str:
            weight *= 1.0
        elif "audio" in source_str:
            weight *= 0.9
        
        weights[source_str] = weight
    
    # 基于量化指标调整权重
    if isinstance(quant_metrics, dict):
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
        
        # 多模态特定指标权重调整
        if "text_confidence" in quant_metrics:
            text_conf = quant_metrics["text_confidence"]
            if text_conf > 0.9:
                for source in weights:
                    if any(ext in source for ext in [".md", ".txt", ".pdf"]):
                        weights[source] *= 1.2
        
        if "image_quality" in quant_metrics:
            img_quality = quant_metrics["image_quality"]
            if img_quality > 0.8:
                for source in weights:
                    if any(ext in source for ext in [".png", ".jpg", ".jpeg", ".svg"]):
                        weights[source] *= 1.2
        
        if "audio_clarity" in quant_metrics:
            audio_clarity = quant_metrics["audio_clarity"]
            if audio_clarity > 0.8:
                for source in weights:
                    if any(ext in source for ext in [".wav", ".mp3"]):
                        weights[source] *= 1.2
        
        # 考虑不确定性指标
        if "p_value_std" in quant_metrics:
            p_value_std = quant_metrics["p_value_std"]
            if p_value_std < 0.01:
                for source in weights:
                    if "stats" in source:
                        weights[source] *= 1.1
        
        if "auc_std" in quant_metrics:
            auc_std = quant_metrics["auc_std"]
            if auc_std < 0.05:
                for source in weights:
                    if "model" in source:
                        weights[source] *= 1.1
    
    return weights


def build_evidence_network(session_dir: Path, hypothesis_id: str) -> dict[str, Any]:
    """构建证据网络（支持多模态数据）"""
    # 加载相关证据
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    evidence = evidence_rows.get(hypothesis_id.upper(), {})
    evidence_sources = evidence.get("evidence_sources", [])
    quant_metrics = evidence.get("quant_metrics", {})
    hypothesis_type = evidence.get("hypothesis_type", "generic")
    method_trace = evidence.get("method_trace", [])
    
    # 构建网络节点和边
    nodes = []
    edges = []
    
    # 节点ID映射，用于快速查找
    node_id_map = {}
    node_counter = 0
    
    # 添加假设节点
    hypothesis_node_id = f"hypothesis_0"
    nodes.append({
        "id": hypothesis_node_id,
        "label": f"假设 {hypothesis_id}",
        "type": "hypothesis",
        "weight": 1.5  # 假设节点权重较高
    })
    node_id_map["hypothesis"] = hypothesis_node_id
    node_counter += 1
    
    # 添加方法节点
    method_nodes = []
    if isinstance(method_trace, list):
        for i, method in enumerate(method_trace):
            if isinstance(method, dict):
                method_name = method.get("model_name", method.get("model", method.get("estimator", f"方法{i+1}")))
                method_node_id = f"method_{i}"
                nodes.append({
                    "id": method_node_id,
                    "label": str(method_name),
                    "type": "method",
                    "weight": 1.2
                })
                method_nodes.append(method_node_id)
                node_id_map[f"method_{i}"] = method_node_id
                # 连接假设节点和方法节点
                edges.append({
                    "source": hypothesis_node_id,
                    "target": method_node_id,
                    "weight": 0.8
                })
                node_counter += 1
    
    # 添加证据源节点（支持多模态）
    source_nodes = []
    evidence_types = []
    for i, source in enumerate(evidence_sources):
        source_str = str(source)
        source_node_id = f"source_{i}"
        
        # 基于证据源类型计算权重（多模态支持）
        weight = 1.0
        evidence_type = "generic"
        if ".json" in source_str:
            weight = 0.8
            evidence_type = "json"
        elif ".csv" in source_str or ".tsv" in source_str:
            weight = 0.9
            evidence_type = "data"
        elif ".png" in source_str or ".jpg" in source_str or ".jpeg" in source_str or ".svg" in source_str:
            weight = 0.7  # 提高图像证据权重
            evidence_type = "image"
        elif ".md" in source_str or ".txt" in source_str:
            weight = 0.6
            evidence_type = "text"
        elif ".pdf" in source_str:
            weight = 0.7
            evidence_type = "document"
        elif ".wav" in source_str or ".mp3" in source_str:
            weight = 0.6
            evidence_type = "audio"
        
        # 根据路径调整权重
        if "stats" in source_str:
            weight *= 1.2
        elif "model" in source_str:
            weight *= 1.1
        elif "text" in source_str:
            weight *= 0.9
        elif "image" in source_str:
            weight *= 1.0
        
        nodes.append({
            "id": source_node_id,
            "label": source_str,
            "type": "evidence_source",
            "subtype": evidence_type,
            "weight": weight
        })
        source_nodes.append(source_node_id)
        evidence_types.append(evidence_type)
        node_id_map[f"source_{i}"] = source_node_id
        
        # 连接证据源到方法节点（如果有）
        for method_node_id in method_nodes:
            # 基于证据类型和方法类型计算边权重
            edge_weight = 0.6
            method_str = str(method_nodes.index(method_node_id))
            if evidence_type == "data" and "stats" in source_str:
                edge_weight = 0.9
            elif evidence_type == "image" and "visual" in method_str:
                edge_weight = 0.8
            elif evidence_type == "text" and "nlp" in method_str:
                edge_weight = 0.8
            
            edges.append({
                "source": method_node_id,
                "target": source_node_id,
                "weight": edge_weight,
                "type": "method_evidence"
            })
        
        # 如果没有方法节点，直接连接到假设节点
        if not method_nodes:
            edges.append({
                "source": hypothesis_node_id,
                "target": source_node_id,
                "weight": 0.7,
                "type": "direct_evidence"
            })
        
        node_counter += 1
    
    # 添加量化指标节点
    metric_nodes = []
    if isinstance(quant_metrics, dict):
        for i, (metric, value) in enumerate(quant_metrics.items()):
            metric_node_id = f"metric_{i}"
            
            # 基于指标类型和值计算权重
            weight = 1.0
            if metric == "p_value" and isinstance(value, (int, float)) and value < 0.05:
                weight = 1.3
            elif metric == "auc" and isinstance(value, (int, float)) and value > 0.8:
                weight = 1.3
            elif metric == "accuracy" and isinstance(value, (int, float)) and value > 0.8:
                weight = 1.2
            elif metric == "text_confidence" and isinstance(value, (int, float)) and value > 0.9:
                weight = 1.2
            elif metric == "image_quality" and isinstance(value, (int, float)) and value > 0.8:
                weight = 1.2
            
            nodes.append({
                "id": metric_node_id,
                "label": str(metric),
                "type": "quantitative_metric",
                "value": value,
                "weight": weight
            })
            metric_nodes.append(metric_node_id)
            node_id_map[f"metric_{i}"] = metric_node_id
            
            # 连接指标到证据源
            for source_node_id in source_nodes:
                # 基于证据源类型和指标类型计算边权重
                edge_weight = 0.5
                source_idx = source_nodes.index(source_node_id)
                source_str = str(evidence_sources[source_idx])
                evidence_type = evidence_types[source_idx]
                
                if "stats" in source_str and metric in ["p_value", "q_value", "effect_size"]:
                    edge_weight = 0.9
                elif "model" in source_str and metric in ["auc", "accuracy", "f1"]:
                    edge_weight = 0.9
                elif evidence_type == "text" and metric == "text_confidence":
                    edge_weight = 0.9
                elif evidence_type == "image" and metric == "image_quality":
                    edge_weight = 0.9
                
                edges.append({
                    "source": source_node_id,
                    "target": metric_node_id,
                    "weight": edge_weight,
                    "type": "evidence_metric"
                })
            
            # 连接指标到假设节点
            edges.append({
                "source": metric_node_id,
                "target": hypothesis_node_id,
                "weight": 0.7,
                "type": "metric_hypothesis"
            })
            
            node_counter += 1
    
    # 添加多模态融合节点（如果有多种类型的证据）
    multimodal = len(set(evidence_types)) > 1
    if multimodal:
        fusion_node_id = f"fusion_{node_counter}"
        nodes.append({
            "id": fusion_node_id,
            "label": "多模态融合",
            "type": "fusion",
            "weight": 1.3
        })
        node_counter += 1
        
        # 连接所有证据到融合节点
        for i, source_node_id in enumerate(source_nodes):
            evidence_type = evidence_types[i]
            edges.append({
                "source": source_node_id,
                "target": fusion_node_id,
                "weight": 0.7,
                "type": "fusion_evidence",
                "evidence_type": evidence_type
            })
        
        # 连接融合节点到假设
        edges.append({
            "source": fusion_node_id,
            "target": hypothesis_node_id,
            "weight": 0.9,
            "type": "fusion_hypothesis"
        })
    
    # 添加证据之间的关联边（基于多模态关系）
    for i in range(len(source_nodes)):
        for j in range(i + 1, len(source_nodes)):
            type_i = evidence_types[i]
            type_j = evidence_types[j]
            
            # 基于类型相似性的边
            if type_i == type_j and type_i != "generic":
                edges.append({
                    "source": source_nodes[i],
                    "target": source_nodes[j],
                    "weight": 0.4,
                    "type": "similarity"
                })
            # 基于多模态关联的边
            elif type_i != type_j and type_i != "generic" and type_j != "generic":
                edges.append({
                    "source": source_nodes[i],
                    "target": source_nodes[j],
                    "weight": 0.3,
                    "type": "multimodal"
                })
    
    # 计算网络分析指标
    network_metrics = calculate_network_metrics(nodes, edges)
    
    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "network_metrics": network_metrics,
        "multimodal": multimodal,
        "evidence_types": list(set(evidence_types))
    }


def calculate_network_metrics(nodes: list, edges: list) -> dict[str, Any]:
    """计算网络分析指标"""
    metrics = {
        "density": 0.0,
        "average_degree": 0.0,
        "node_types": {},
        "edge_types": {}
    }
    
    # 计算网络密度
    n = len(nodes)
    if n > 1:
        max_edges = n * (n - 1)
        metrics["density"] = len(edges) / max_edges
    
    # 计算平均度
    if n > 0:
        degree_count = {node["id"]: 0 for node in nodes}
        for edge in edges:
            if edge["source"] in degree_count:
                degree_count[edge["source"]] += 1
            if edge["target"] in degree_count:
                degree_count[edge["target"]] += 1
        total_degree = sum(degree_count.values())
        metrics["average_degree"] = total_degree / n
    
    # 统计节点类型
    for node in nodes:
        node_type = node.get("type", "unknown")
        if node_type not in metrics["node_types"]:
            metrics["node_types"][node_type] = 0
        metrics["node_types"][node_type] += 1
    
    # 统计边类型
    for edge in edges:
        edge_type = edge.get("type", "unknown")
        if edge_type not in metrics["edge_types"]:
            metrics["edge_types"][edge_type] = 0
        metrics["edge_types"][edge_type] += 1
    
    return metrics


def analyze_multimodal_data(evidence_sources: list, quant_metrics: dict, evidence_network: dict) -> dict[str, Any]:
    """分析多模态数据（支持跨模态相关性分析和异常检测）"""
    # 分析证据源类型分布
    source_types = {}
    for source in evidence_sources:
        source_str = str(source)
        if ".json" in source_str:
            source_types["json"] = source_types.get("json", 0) + 1
        elif ".csv" in source_str or ".tsv" in source_str:
            source_types["data"] = source_types.get("data", 0) + 1
        elif ".png" in source_str or ".jpg" in source_str or ".jpeg" in source_str or ".svg" in source_str:
            source_types["image"] = source_types.get("image", 0) + 1
        elif ".md" in source_str or ".txt" in source_str:
            source_types["text"] = source_types.get("text", 0) + 1
        elif ".pdf" in source_str:
            source_types["document"] = source_types.get("document", 0) + 1
        elif ".wav" in source_str or ".mp3" in source_str:
            source_types["audio"] = source_types.get("audio", 0) + 1
    
    # 评估多模态融合效果
    multimodal = evidence_network.get("multimodal", False)
    evidence_types = evidence_network.get("evidence_types", [])
    node_count = evidence_network.get("node_count", 0)
    edge_count = evidence_network.get("edge_count", 0)
    
    # 计算融合质量评分
    fusion_quality = 0.0
    if multimodal:
        # 基于证据类型多样性和网络连接性计算融合质量
        type_diversity = len(evidence_types) / 6  # 最大6种类型（包括音频）
        network_connectivity = min(1.0, edge_count / (node_count * (node_count - 1)))
        fusion_quality = (type_diversity * 0.6 + network_connectivity * 0.4) * 100
    
    # 分析多模态特定指标
    multimodal_metrics = {}
    if "text_confidence" in quant_metrics:
        multimodal_metrics["text_confidence"] = quant_metrics["text_confidence"]
    if "image_quality" in quant_metrics:
        multimodal_metrics["image_quality"] = quant_metrics["image_quality"]
    if "audio_clarity" in quant_metrics:
        multimodal_metrics["audio_clarity"] = quant_metrics["audio_clarity"]
    
    # 分析跨模态相关性
    cross_modal_correlation = {}
    if len(evidence_types) > 1:
        # 计算跨模态相关性得分
        cross_modal_correlation["score"] = fusion_quality / 100
        cross_modal_correlation["strength"] = "strong" if fusion_quality > 70 else "medium" if fusion_quality > 40 else "weak"
    
    # 多模态异常检测
    anomalies = []
    # 检查各模态质量指标
    if "text" in source_types and "text_confidence" in quant_metrics:
        text_conf = quant_metrics["text_confidence"]
        if text_conf < 0.6:
            anomalies.append({"type": "text", "issue": "低置信度", "value": text_conf})
    
    if "image" in source_types and "image_quality" in quant_metrics:
        img_quality = quant_metrics["image_quality"]
        if img_quality < 0.5:
            anomalies.append({"type": "image", "issue": "低质量", "value": img_quality})
    
    if "audio" in source_types and "audio_clarity" in quant_metrics:
        audio_clarity = quant_metrics["audio_clarity"]
        if audio_clarity < 0.6:
            anomalies.append({"type": "audio", "issue": "低清晰度", "value": audio_clarity})
    
    # 检查不确定性指标
    if "p_value_std" in quant_metrics and quant_metrics["p_value_std"] > 0.05:
        anomalies.append({"type": "statistical", "issue": "高p值不确定性", "value": quant_metrics["p_value_std"]})
    
    if "auc_std" in quant_metrics and quant_metrics["auc_std"] > 0.1:
        anomalies.append({"type": "model", "issue": "高AUC不确定性", "value": quant_metrics["auc_std"]})
    
    # 生成多模态融合建议
    recommendations = []
    if not multimodal:
        # 单模态数据，建议增加其他类型的证据
        current_types = list(source_types.keys())
        all_types = ["json", "data", "image", "text", "document", "audio"]
        missing_types = [t for t in all_types if t not in current_types]
        if missing_types:
            recommendations.append(f"建议增加以下类型的证据：{', '.join(missing_types)}")
    else:
        # 多模态数据，评估融合效果
        if fusion_quality < 60:
            recommendations.append("多模态融合质量较低，建议增加更多类型的证据或提高证据之间的关联性")
        elif fusion_quality < 80:
            recommendations.append("多模态融合质量中等，建议加强不同类型证据之间的关联")
        else:
            recommendations.append("多模态融合质量良好，继续保持")
    
    # 基于证据类型提供具体建议
    if "text" in source_types and "text_confidence" in quant_metrics:
        text_conf = quant_metrics["text_confidence"]
        if text_conf < 0.8:
            recommendations.append("文本证据置信度较低，建议提高文本分析的质量")
    
    if "image" in source_types and "image_quality" in quant_metrics:
        img_quality = quant_metrics["image_quality"]
        if img_quality < 0.7:
            recommendations.append("图像证据质量较低，建议使用更高质量的图像数据")
    
    if "audio" in source_types and "audio_clarity" in quant_metrics:
        audio_clarity = quant_metrics["audio_clarity"]
        if audio_clarity < 0.7:
            recommendations.append("音频证据清晰度较低，建议使用更高质量的音频数据")
    
    # 基于异常检测结果提供建议
    if anomalies:
        recommendations.append(f"检测到{len(anomalies)}个多模态异常，建议检查相关证据质量")
    
    return {
        "source_types": source_types,
        "multimodal": multimodal,
        "evidence_types": evidence_types,
        "fusion_quality": fusion_quality,
        "multimodal_metrics": multimodal_metrics,
        "cross_modal_correlation": cross_modal_correlation,
        "anomalies": anomalies,
        "recommendations": recommendations
    }


def calculate_confidence_score(evidence_weights: dict[str, float], multipath_data: dict) -> float:
    """计算置信度分数"""
    # 计算证据权重平均值
    if evidence_weights:
        avg_weight = sum(evidence_weights.values()) / len(evidence_weights)
    else:
        avg_weight = 0.0
    
    # 考虑多路径一致性
    consistency = str(multipath_data.get("consistency", "unknown")).lower()
    consistency_score = 0.0
    if consistency == "consistent":
        consistency_score = 1.0
    elif consistency == "partial":
        consistency_score = 0.5
    
    # 综合计算置信度
    confidence_score = (avg_weight * 0.7) + (consistency_score * 0.3)
    return min(confidence_score, 1.0)


def perform_sensitivity_analysis(session_dir: Path, hypothesis_id: str) -> dict[str, Any]:
    """执行敏感性分析"""
    # 加载证据数据
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    evidence = evidence_rows.get(hypothesis_id.upper(), {})
    quant_metrics = evidence.get("quant_metrics", {})
    
    # 执行敏感性分析
    sensitivity_results = {}
    
    if isinstance(quant_metrics, dict):
        # 对p值进行敏感性分析
        if "p_value" in quant_metrics:
            p_value = quant_metrics["p_value"]
            sensitivity_results["p_value_sensitivity"] = {
                "original": p_value,
                "threshold_0_05": p_value < 0.05,
                "threshold_0_01": p_value < 0.01,
                "threshold_0_001": p_value < 0.001
            }
        
        # 对AUC进行敏感性分析
        if "auc" in quant_metrics:
            auc = quant_metrics["auc"]
            sensitivity_results["auc_sensitivity"] = {
                "original": auc,
                "excellent": auc > 0.9,
                "good": auc > 0.8,
                "fair": auc > 0.7
            }
        
        # 对准确率进行敏感性分析
        if "accuracy" in quant_metrics:
            accuracy = quant_metrics["accuracy"]
            sensitivity_results["accuracy_sensitivity"] = {
                "original": accuracy,
                "excellent": accuracy > 0.9,
                "good": accuracy > 0.8,
                "fair": accuracy > 0.7
            }
        
        # 对F1分数进行敏感性分析
        if "f1" in quant_metrics:
            f1 = quant_metrics["f1"]
            sensitivity_results["f1_sensitivity"] = {
                "original": f1,
                "excellent": f1 > 0.9,
                "good": f1 > 0.8,
                "fair": f1 > 0.7
            }
        
        # 对相关系数进行敏感性分析
        if "strongest_abs_corr" in quant_metrics:
            corr = quant_metrics["strongest_abs_corr"]
            sensitivity_results["correlation_sensitivity"] = {
                "original": corr,
                "very_strong": corr > 0.8,
                "strong": corr > 0.6,
                "moderate": corr > 0.4,
                "weak": corr > 0.2
            }
        
        # 对效应量进行敏感性分析
        if "effect_size" in quant_metrics:
            effect_size = quant_metrics["effect_size"]
            sensitivity_results["effect_size_sensitivity"] = {
                "original": effect_size,
                "large": effect_size > 0.8,
                "medium": effect_size > 0.5,
                "small": effect_size > 0.2
            }
        
        # 对q值进行敏感性分析（多重检验校正）
        if "q_value" in quant_metrics:
            q_value = quant_metrics["q_value"]
            sensitivity_results["q_value_sensitivity"] = {
                "original": q_value,
                "threshold_0_05": q_value < 0.05,
                "threshold_0_01": q_value < 0.01,
                "threshold_0_001": q_value < 0.001
            }
    
    return {
        "hypothesis_id": hypothesis_id,
        "sensitivity_results": sensitivity_results,
        "overall_stability": calculate_stability_score(sensitivity_results)
    }


def calculate_stability_score(sensitivity_results: dict) -> float:
    """计算稳定性分数"""
    if not sensitivity_results:
        return 0.0
    
    stability_score = 0.0
    total_tests = 0
    
    # 评估p值稳定性
    if "p_value_sensitivity" in sensitivity_results:
        p_sensitivity = sensitivity_results["p_value_sensitivity"]
        if p_sensitivity["threshold_0_001"]:
            stability_score += 1.0
        elif p_sensitivity["threshold_0_01"]:
            stability_score += 0.8
        elif p_sensitivity["threshold_0_05"]:
            stability_score += 0.6
        total_tests += 1
    
    # 评估AUC稳定性
    if "auc_sensitivity" in sensitivity_results:
        auc_sensitivity = sensitivity_results["auc_sensitivity"]
        if auc_sensitivity["excellent"]:
            stability_score += 1.0
        elif auc_sensitivity["good"]:
            stability_score += 0.8
        elif auc_sensitivity["fair"]:
            stability_score += 0.6
        total_tests += 1
    
    # 评估准确率稳定性
    if "accuracy_sensitivity" in sensitivity_results:
        accuracy_sensitivity = sensitivity_results["accuracy_sensitivity"]
        if accuracy_sensitivity["excellent"]:
            stability_score += 1.0
        elif accuracy_sensitivity["good"]:
            stability_score += 0.8
        elif accuracy_sensitivity["fair"]:
            stability_score += 0.6
        total_tests += 1
    
    # 评估F1分数稳定性
    if "f1_sensitivity" in sensitivity_results:
        f1_sensitivity = sensitivity_results["f1_sensitivity"]
        if f1_sensitivity["excellent"]:
            stability_score += 1.0
        elif f1_sensitivity["good"]:
            stability_score += 0.8
        elif f1_sensitivity["fair"]:
            stability_score += 0.6
        total_tests += 1
    
    # 评估相关系数稳定性
    if "correlation_sensitivity" in sensitivity_results:
        corr_sensitivity = sensitivity_results["correlation_sensitivity"]
        if corr_sensitivity["very_strong"]:
            stability_score += 1.0
        elif corr_sensitivity["strong"]:
            stability_score += 0.8
        elif corr_sensitivity["moderate"]:
            stability_score += 0.6
        elif corr_sensitivity["weak"]:
            stability_score += 0.4
        total_tests += 1
    
    # 评估效应量稳定性
    if "effect_size_sensitivity" in sensitivity_results:
        effect_sensitivity = sensitivity_results["effect_size_sensitivity"]
        if effect_sensitivity["large"]:
            stability_score += 1.0
        elif effect_sensitivity["medium"]:
            stability_score += 0.8
        elif effect_sensitivity["small"]:
            stability_score += 0.6
        total_tests += 1
    
    # 评估q值稳定性
    if "q_value_sensitivity" in sensitivity_results:
        q_sensitivity = sensitivity_results["q_value_sensitivity"]
        if q_sensitivity["threshold_0_001"]:
            stability_score += 1.0
        elif q_sensitivity["threshold_0_01"]:
            stability_score += 0.8
        elif q_sensitivity["threshold_0_05"]:
            stability_score += 0.6
        total_tests += 1
    
    if total_tests > 0:
        return stability_score / total_tests
    else:
        return 0.0


def generate_depth_research_plan(session_dir: Path, hypothesis_id: str) -> dict[str, Any]:
    """生成深度研究计划"""
    # 加载证据数据
    evidence_pack = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    evidence_rows = {
        str(row.get("hypothesis_id", "")).strip().upper(): row
        for row in evidence_pack.get("hypotheses", [])
        if isinstance(row, dict)
    }
    
    evidence = evidence_rows.get(hypothesis_id.upper(), {})
    quant_metrics = evidence.get("quant_metrics", {})
    
    # 执行敏感性分析
    sensitivity_analysis = perform_sensitivity_analysis(session_dir, hypothesis_id)
    
    # 生成深度研究计划
    research_plan = {
        "hypothesis_id": hypothesis_id,
        "sensitivity_analysis": sensitivity_analysis,
        "recommended_actions": [],
        "priority": "medium"
    }
    
    # 根据敏感性分析结果生成建议
    stability_score = sensitivity_analysis.get("overall_stability", 0.0)
    
    if stability_score < 0.6:
        research_plan["priority"] = "high"
        research_plan["recommended_actions"].extend([
            "执行更严格的统计检验",
            "增加样本量以提高统计功效",
            "尝试不同的分析方法",
            "进行交叉验证以验证结果"
        ])
    elif stability_score < 0.8:
        research_plan["priority"] = "medium"
        research_plan["recommended_actions"].extend([
            "进行稳健性测试",
            "验证结果在不同数据集上的一致性",
            "执行敏感性分析以评估参数影响"
        ])
    else:
        research_plan["priority"] = "low"
        research_plan["recommended_actions"].extend([
            "进行结果解释和可视化",
            "准备报告和文档",
            "考虑扩展分析到相关领域"
        ])
    
    # 根据量化指标添加特定建议
    if isinstance(quant_metrics, dict):
        if "p_value" in quant_metrics and quant_metrics["p_value"] < 0.05:
            research_plan["recommended_actions"].append("执行多重检验校正以控制假阳性率")
        
        if "auc" in quant_metrics and quant_metrics["auc"] > 0.8:
            research_plan["recommended_actions"].append("尝试不同的模型以进一步提高性能")
    
    return research_plan
