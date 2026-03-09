from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
