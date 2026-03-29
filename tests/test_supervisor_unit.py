from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from src.core.orchestration.supervisor import PhaseSupervisor, SupervisorContext, ValidationResult
from src.core.orchestration.supervisor.context import SupervisorContext as ContextClass
from src.core.orchestration.supervisor.result import (
    make_failure_result,
    make_success_result,
)


class TestSupervisorContext:
    def test_from_config_creates_valid_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "supervisor_wait_strategy": "poll",
                "supervisor_poll_interval": 3,
                "supervisor_max_wait": 60,
                "supervisor_max_retries": 2,
                "supervisor_semantic_check": True,
            }

            def state_getter():
                return {}

            context = ContextClass.from_config(
                phase_id="test_phase",
                session_dir=Path(tmpdir),
                config=config,
                state_getter=state_getter,
            )

            assert context.phase_id == "test_phase"
            assert context.session_dir == Path(tmpdir)
            assert context.wait_strategy == "poll"
            assert context.poll_interval == 3
            assert context.max_wait == 60
            assert context.max_retries == 2
            assert context.semantic_check is True

    def test_from_config_defaults_for_invalid_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "supervisor_wait_strategy": "invalid_strategy",
            }

            context = ContextClass.from_config(
                phase_id="test",
                session_dir=Path(tmpdir),
                config=config,
                state_getter=lambda: {},
            )

            assert context.wait_strategy == "poll"

    def test_record_check_appends_to_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )

            context.record_check({"valid": True})
            context.record_check({"valid": False, "reason": "test failure"})

            history = context.get_history()
            assert len(history) == 2
            assert history[0]["result"]["valid"] is True
            assert history[1]["result"]["valid"] is False

    def test_timeout_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
                max_wait=1,
            )

            context.start_wait()
            time.sleep(1.5)

            assert context.is_timeout() is True
            assert context.elapsed() >= 1.0


class TestValidationResult:
    def test_make_success_result_defaults(self):
        result = make_success_result()

        assert result["valid"] is True
        assert result["action"] == "continue"
        assert result["retryable"] is False
        assert result["reason"] == "Validation passed"
        assert result["notes"] == []
        assert "timestamp" in result

    def test_make_success_result_with_custom_values(self):
        result = make_success_result(
            reason="Custom reason",
            notes=["note1", "note2"],
            derived_from=["phase1", "phase2"],
        )

        assert result["valid"] is True
        assert result["reason"] == "Custom reason"
        assert result["notes"] == ["note1", "note2"]
        assert result["derived_from"] == ["phase1", "phase2"]

    def test_make_failure_result_defaults(self):
        result = make_failure_result(reason="Test failure")

        assert result["valid"] is False
        assert result["reason"] == "Test failure"
        assert result["action"] == "abort"
        assert result["retryable"] is False
        assert result["blocking"] is True
        assert result["failure_type"] == "unknown"

    def test_make_failure_result_retryable(self):
        result = make_failure_result(
            reason="Temporary failure",
            action="retry",
            retryable=True,
            failure_type="infrastructure",
            recovery_action="check_service_status",
        )

        assert result["valid"] is False
        assert result["action"] == "retry"
        assert result["retryable"] is True
        assert result["failure_type"] == "infrastructure"
        assert result["recovery_action"] == "check_service_status"


class TestPhaseSupervisor:
    def test_validate_input_execution_guard_with_no_code_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="execution_guard",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {"code_steps": []})

            result = supervisor.validate_input()

            assert result["valid"] is False
            assert result["failure_type"] == "artifact_missing"
            assert result["action"] == "retry"

    def test_validate_input_execution_guard_with_code_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="execution_guard",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(
                context,
                lambda: {"code_steps": [{"name": "step1", "path": "/tmp/step1.py"}]},
            )

            result = supervisor.validate_input()

            assert result["valid"] is True
            assert result["action"] == "continue"

    def test_validate_input_analyze_results_with_no_exec_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="analyze_results",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {"exec_results": []})

            result = supervisor.validate_input()

            assert result["valid"] is False
            assert result["failure_type"] == "artifact_missing"
            assert result["action"] == "abort"

    def test_validate_output_unknown_phase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="unknown_phase",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            result = supervisor.validate_output()

            assert result["valid"] is True

    def test_semantic_check_execution_guard_with_error_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="execution_guard",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(
                context,
                lambda: {
                    "exec_results": [
                        {"step": "step1", "statuses": ["success"], "output": "ok"},
                        {"step": "step2", "statuses": ["error"], "output": "Traceback..."},
                    ]
                },
            )

            result = supervisor._semantic_check_execution_guard({})

            assert result["valid"] is False
            assert result["failure_type"] == "code_runtime"
            assert result["action"] == "retry"

    def test_classify_failure_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            failure_type = supervisor._classify_failure("Connection timeout occurred")
            assert failure_type == "infrastructure"

            failure_type = supervisor._classify_failure("Service unavailable")
            assert failure_type == "infrastructure"

    def test_classify_failure_semantic_drift(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            failure_type = supervisor._classify_failure("Results mismatch with hypothesis")
            assert failure_type == "semantic_drift"

    def test_classify_failure_contract_violation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            failure_type = supervisor._classify_failure("Unexpected artifact format")
            assert failure_type == "contract_violation"

    def test_analyze_mismatch_updates_failure_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            failure = make_failure_result(
                reason="timeout error",
                action="abort",
                retryable=False,
            )

            updated = supervisor.analyze_mismatch(failure)

            assert updated["failure_type"] == "infrastructure"
            assert updated["recovery_action"] == "check_service_status_and_increase_timeout"

    def test_get_action_returns_action_from_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            validation: ValidationResult = {"valid": True, "action": "continue", "reason": "ok"}
            assert supervisor.get_action(validation) == "continue"

            validation = {"valid": False, "action": "retry", "reason": "fail"}
            assert supervisor.get_action(validation) == "retry"

    def test_wait_for_completion_with_sleep_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ContextClass(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
                wait_strategy="sleep",
                poll_interval=1,
                max_wait=5,
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            completed, reason = supervisor.wait_for_completion()

            assert completed is True
            assert "Sleep" in reason or "closure" in reason.lower()


class TestSupervisorIntegration:
    def test_supervisor_validation_stored_in_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.core.orchestration.graph import _run_supervisor

            state = {
                "code_steps": [{"name": "step1", "path": "/tmp/step1.py"}],
                "session_dir": tmpdir,
            }
            config = {
                "supervisor_enabled": True,
                "supervisor_semantic_check": False,
            }

            result = _run_supervisor(state, "execution_guard", config, "input")

            assert "supervisor_validation" in result or result == {}
