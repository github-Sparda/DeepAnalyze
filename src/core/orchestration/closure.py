from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

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
    result_ids = _ids_from(_load_json(session_dir / "result" / "hypothesis_results.json"), "hypothesis")
    multipath_ids = _ids_from(_load_json(session_dir / "result" / "hypothesis_multipath.json"), "hypothesis_id")
    evidence_ids = _ids_from(_load_json(session_dir / "result" / "hypothesis_evidence_pack.json"), "hypothesis_id")
    bad: list[str] = []
    for name, ids in (
        ("results", result_ids),
        ("multipath", multipath_ids),
        ("evidence_pack", evidence_ids),
    ):
        if ids and ids != plan_ids:
            bad.append(f"{name}_ids_mismatch")
    return (len(bad) == 0, bad)


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
        completion = merged_state.get("completion_validation", {})
        if isinstance(completion, dict) and not bool(completion.get("complete", False)):
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
