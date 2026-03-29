from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Optional

from ..closure import evaluate_phase_closure, load_phase_closure_map
from ..state import OrchestrationState
from .context import SupervisorContext
from .result import ValidationResult, make_failure_result, make_success_result


FAILURE_TYPE_KEYWORDS = {
    "infrastructure": ["timeout", "connection", "service unavailable", "network", "refused"],
    "semantic_drift": ["drift", "mismatch", "inconsistent", "contradict"],
    "evidence_insufficient": ["evidence", "insufficient", "missing evidence", "incomplete"],
    "artifact_invalid": ["invalid", "malformed", "corrupt"],
    "artifact_missing": ["missing", "not found", "not exist"],
    "code_runtime": ["runtime", "execution error", "traceback", "exception"],
}

RECOVERY_ACTIONS = {
    "infrastructure": "check_service_status_and_increase_timeout",
    "semantic_drift": "resync_assumptions_and_evidence",
    "evidence_insufficient": "supplement_evidence_or_adjust_paths",
    "artifact_invalid": "regenerate_artifact_with_correct_schema",
    "artifact_missing": "regenerate_artifact",
    "code_runtime": "invoke_code_repair_or_manual_debug",
    "contract_violation": "check_artifact_definitions_and_rerun",
}


class PhaseSupervisor:
    def __init__(
        self,
        context: SupervisorContext,
        state_provider: Callable[[], OrchestrationState],
    ) -> None:
        self.context = context
        self._state_provider = state_provider

    @property
    def phase_id(self) -> str:
        return self.context.phase_id

    def validate_input(self) -> ValidationResult:
        state = self._state_provider()
        phase = self.context.phase_id

        if phase == "execution_guard":
            return self._validate_execution_guard_input(state)
        elif phase == "analyze_results":
            return self._validate_analyze_results_input(state)
        elif phase == "evidence_curation":
            return self._validate_evidence_curation_input(state)
        elif phase == "generate_report":
            return self._validate_generate_report_input(state)
        return make_success_result(reason=f"No input validation for phase {phase}")

    def validate_output(self) -> ValidationResult:
        state = self._state_provider()
        phase = self.context.phase_id

        struct_result = self._validate_structure(state)
        if not struct_result["valid"]:
            failure_type = struct_result.get("failure_type", "contract_violation")
            return make_failure_result(
                reason=struct_result["reason"],
                action="retry" if struct_result.get("retryable") else "abort",
                retryable=struct_result.get("retryable", False),
                failure_type=failure_type,
                recovery_action=RECOVERY_ACTIONS.get(failure_type, "check_artifact_definitions_and_rerun"),
                blocking=True,
                notes=struct_result.get("notes", []),
            )

        if self.context.semantic_check:
            semantic_result = self._semantic_check(state)
            if not semantic_result["valid"]:
                return semantic_result

        return make_success_result(reason=f"Output validation passed for phase {phase}")

    def wait_for_completion(self) -> tuple[bool, str]:
        if self.context.wait_strategy == "sleep":
            return self._sleep_wait()
        return self._poll_wait()

    def _poll_wait(self) -> tuple[bool, str]:
        self.context.start_wait()
        phase = self.context.phase_id

        while not self.context.is_timeout():
            closure_map = load_phase_closure_map(self.context.session_dir)
            closure = closure_map.get(phase)

            if closure:
                status = str(closure.get("status", "")).strip().lower()
                if status in {"success", "recovered"}:
                    return True, "Phase completed successfully"
                if status in {"failed", "skipped", "recoverable_failed"}:
                    return False, f"Phase ended with status: {status}"

            self.context.increment_wait()
            time.sleep(self.context.poll_interval)

        return False, "Wait timeout"

    def _sleep_wait(self) -> tuple[bool, str]:
        self.context.start_wait()
        time.sleep(self.context.poll_interval)

        closure_map = load_phase_closure_map(self.context.session_dir)
        closure = closure_map.get(self.context.phase_id)

        if closure:
            status = str(closure.get("status", "")).strip().lower()
            if status in {"success", "recovered"}:
                return True, "Phase completed"
            if status in {"failed", "skipped"}:
                return False, f"Phase ended with status: {status}"

        return True, "Sleep wait completed (no closure status)"

    def _validate_structure(self, state: OrchestrationState) -> dict[str, Any]:
        closure = evaluate_phase_closure(
            self.context.phase_id,
            self.context.session_dir,
            state,
        )

        if closure is None:
            return {"valid": True, "reason": "No closure validation for this phase"}

        status = str(closure.get("status", "")).strip().lower()
        failed_checks = closure.get("failed_checks", [])
        retryable = closure.get("recoverable", False)
        blocking = closure.get("blocking", True)

        if status in {"success", "recovered"}:
            return {"valid": True, "reason": "Structure validation passed", "retryable": False}

        if status == "skipped":
            return {
                "valid": False,
                "reason": f"Phase skipped: {', '.join(failed_checks)}",
                "retryable": False,
                "failure_type": "contract_violation",
                "blocking": True,
                "notes": closure.get("notes", []),
            }

        failure_type = closure.get("failure_type", "contract_violation")

        return {
            "valid": False,
            "reason": f"Structure validation failed: {', '.join(failed_checks)}",
            "retryable": retryable,
            "failure_type": failure_type,
            "blocking": blocking,
            "notes": closure.get("notes", []),
        }

    def _semantic_check(self, state: OrchestrationState) -> ValidationResult:
        phase = self.context.phase_id

        if phase == "execution_guard":
            return self._semantic_check_execution_guard(state)
        elif phase == "analyze_results":
            return self._semantic_check_analyze_results(state)
        elif phase == "evidence_curation":
            return self._semantic_check_evidence_curation(state)

        return make_success_result(reason="No semantic check for this phase")

    def _semantic_check_execution_guard(self, state: OrchestrationState) -> ValidationResult:
        actual_state = self._state_provider()
        exec_results = actual_state.get("exec_results", [])
        if not exec_results:
            return make_failure_result(
                reason="No execution results found",
                action="abort",
                retryable=False,
                failure_type="artifact_missing",
                recovery_action="regenerate_artifact",
            )

        error_results = [r for r in exec_results if "error" in str(r.get("statuses", [""])).lower()]
        if error_results:
            error_outputs = [r.get("output", "")[:200] for r in error_results]
            return make_failure_result(
                reason=f"Found {len(error_results)} error(s) in execution results",
                action="retry",
                retryable=True,
                failure_type="code_runtime",
                recovery_action="invoke_code_repair_or_manual_debug",
                notes=[f"Error samples: {'; '.join(error_outputs[:3])}"],
            )

        return make_success_result(reason="Execution results semantic check passed")

    def _semantic_check_analyze_results(self, state: OrchestrationState) -> ValidationResult:
        plan_json = state.get("plan_json", {})
        hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []

        if not hypotheses:
            plan_path = self.context.session_dir / "plan" / "analysis_plan.json"
            if plan_path.exists():
                try:
                    import json
                    with open(plan_path, encoding="utf-8") as f:
                        loaded_plan = json.load(f)
                    hypotheses = loaded_plan.get("hypotheses", [])
                except Exception:
                    pass

        if not hypotheses:
            return make_failure_result(
                reason="No hypotheses found in plan",
                action="retry",
                retryable=True,
                failure_type="evidence_insufficient",
                recovery_action="supplement_evidence_or_adjust_paths",
            )

        expected_count = len(hypotheses)
        results_path = self.context.session_dir / "result" / "hypothesis_results.json"

        if not results_path.exists():
            return make_failure_result(
                reason="hypothesis_results.json not found",
                action="retry",
                retryable=True,
                failure_type="artifact_missing",
                recovery_action="regenerate_artifact",
            )

        return make_success_result(reason=f"Semantic check passed for {expected_count} hypotheses")

    def _semantic_check_evidence_curation(self, state: OrchestrationState) -> ValidationResult:
        evidence_path = self.context.session_dir / "result" / "hypothesis_evidence_pack.json"

        if not evidence_path.exists():
            return make_failure_result(
                reason="hypothesis_evidence_pack.json not found",
                action="retry",
                retryable=True,
                failure_type="artifact_missing",
                recovery_action="regenerate_artifact",
            )

        try:
            import json
            with open(evidence_path, encoding="utf-8") as f:
                evidence_data = json.load(f)

            evidence_hypotheses = evidence_data.get("hypotheses", [])
            if not evidence_hypotheses:
                return make_failure_result(
                    reason="Evidence pack is empty",
                    action="retry",
                    retryable=True,
                    failure_type="evidence_insufficient",
                    recovery_action="supplement_evidence_or_adjust_paths",
                )
        except Exception as e:
            return make_failure_result(
                reason=f"Failed to load evidence pack: {str(e)[:100]}",
                action="abort",
                retryable=False,
                failure_type="artifact_invalid",
                recovery_action="regenerate_artifact_with_correct_schema",
            )

        return make_success_result(reason="Evidence curation semantic check passed")

    def _validate_execution_guard_input(self, state: OrchestrationState) -> ValidationResult:
        code_steps = state.get("code_steps", [])
        if not code_steps:
            return make_failure_result(
                reason="No code steps found for execution",
                action="retry",
                retryable=True,
                failure_type="artifact_missing",
                recovery_action="regenerate_artifact",
            )
        return make_success_result(reason="execution_guard input validated")

    def _validate_analyze_results_input(self, state: OrchestrationState) -> ValidationResult:
        exec_results = state.get("exec_results", [])
        if not exec_results:
            return make_failure_result(
                reason="No execution results to analyze",
                action="abort",
                retryable=False,
                failure_type="artifact_missing",
                recovery_action="check_execution_guard_output",
            )
        return make_success_result(reason="analyze_results input validated")

    def _validate_evidence_curation_input(self, state: OrchestrationState) -> ValidationResult:
        multipath_path = self.context.session_dir / "result" / "hypothesis_multipath.json"
        if not multipath_path.exists():
            return make_failure_result(
                reason="hypothesis_multipath.json not found",
                action="retry",
                retryable=True,
                failure_type="artifact_missing",
                recovery_action="regenerate_artifact",
            )
        return make_success_result(reason="evidence_curation input validated")

    def _validate_generate_report_input(self, state: OrchestrationState) -> ValidationResult:
        closure_map = load_phase_closure_map(self.context.session_dir)
        evidence_closure = closure_map.get("evidence_curation", {})
        status = str(evidence_closure.get("status", "")).strip().lower()

        if status in {"failed", "recoverable_failed"}:
            return make_failure_result(
                reason="Evidence curation did not complete successfully",
                action="retry",
                retryable=True,
                failure_type="evidence_insufficient",
                recovery_action="supplement_evidence_or_adjust_paths",
                blocking=True,
            )
        return make_success_result(reason="generate_report input validated")

    def _classify_failure(self, reason: str, error: str = "") -> str:
        text = f"{reason} {error}".lower()
        for failure_type, keywords in FAILURE_TYPE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return failure_type
        return "contract_violation"

    def _suggest_recovery(self, failure_type: str) -> str:
        return RECOVERY_ACTIONS.get(failure_type, "check_artifact_definitions_and_rerun")

    def get_action(self, validation: ValidationResult) -> str:
        return validation.get("action", "continue")

    def analyze_mismatch(
        self,
        validation: ValidationResult,
    ) -> ValidationResult:
        if validation["valid"]:
            return validation

        reason = validation.get("reason", "")
        failure_type = self._classify_failure(reason)
        recovery_action = self._suggest_recovery(failure_type)

        updated = dict(validation)
        updated["failure_type"] = failure_type
        updated["recovery_action"] = recovery_action

        if failure_type == "infrastructure":
            updated["action"] = "retry"
            updated["retryable"] = True
        elif failure_type == "evidence_insufficient":
            updated["action"] = "retry"
            updated["retryable"] = True
        elif failure_type == "artifact_missing":
            updated["action"] = "retry"
            updated["retryable"] = True
        elif failure_type == "code_runtime":
            if validation.get("retryable", False):
                updated["action"] = "retry"
            else:
                updated["action"] = "abort"
                updated["blocking"] = True

        return ValidationResult(**updated)
