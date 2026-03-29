from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.orchestration.graph import _run_supervisor
from src.core.orchestration.supervisor import PhaseSupervisor, SupervisorContext


class TestSupervisorGraphIntegration:
    def test_run_supervisor_disabled_by_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {"session_dir": tmpdir, "code_steps": []}
            config = {"supervisor_enabled": False}

            result = _run_supervisor(state, "execution_guard", config, "input")

            assert result == {}

    def test_run_supervisor_enabled_with_valid_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "session_dir": tmpdir,
                "code_steps": [{"name": "test_step", "path": "/tmp/test.py"}],
            }
            config = {
                "supervisor_enabled": True,
                "supervisor_semantic_check": False,
            }

            result = _run_supervisor(state, "execution_guard", config, "input")

            assert "supervisor_validation" in result
            validation = result["supervisor_validation"]
            assert validation["valid"] is True
            assert validation["action"] == "continue"

    def test_run_supervisor_detects_missing_code_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "session_dir": tmpdir,
                "code_steps": [],
            }
            config = {
                "supervisor_enabled": True,
                "supervisor_semantic_check": False,
            }

            result = _run_supervisor(state, "execution_guard", config, "input")

            assert "supervisor_validation" in result
            validation = result["supervisor_validation"]
            assert validation["valid"] is False
            assert validation["failure_type"] in ("artifact_missing", "contract_violation")
            assert validation["action"] == "retry"

    def test_run_supervisor_analyze_results_with_exec_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "session_dir": tmpdir,
                "exec_results": [
                    {"step": "step1", "statuses": ["success"], "output": "OK result"},
                ],
            }
            config = {
                "supervisor_enabled": True,
                "supervisor_semantic_check": True,
            }

            result = _run_supervisor(state, "analyze_results", config, "input")

            assert "supervisor_validation" in result
            validation = result["supervisor_validation"]
            assert validation["valid"] is True

    def test_run_supervisor_stores_context_in_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "session_dir": tmpdir,
                "code_steps": [{"name": "test", "path": "/tmp/test.py"}],
            }
            config = {
                "supervisor_enabled": True,
                "supervisor_semantic_check": False,
            }

            _run_supervisor(state, "execution_guard", config, "output")

            assert "supervisor_context" in state
            assert state["supervisor_context"]["phase_id"] == "execution_guard"
            assert state["supervisor_context"]["check_type"] == "output"

    def test_supervisor_with_poll_strategy_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {"session_dir": tmpdir, "code_steps": []}
            config = {
                "supervisor_enabled": True,
                "supervisor_wait_strategy": "poll",
                "supervisor_poll_interval": 1,
                "supervisor_max_wait": 60,
                "supervisor_max_retries": 2,
                "supervisor_semantic_check": False,
            }

            context = SupervisorContext.from_config(
                phase_id="test_phase",
                session_dir=Path(tmpdir),
                config=config,
                state_getter=lambda: state,
            )

            assert context.wait_strategy == "poll"
            assert context.poll_interval == 1
            assert context.max_wait == 60
            assert context.max_retries == 2

    def test_supervisor_with_sleep_strategy_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "supervisor_wait_strategy": "sleep",
            }

            context = SupervisorContext.from_config(
                phase_id="test_phase",
                session_dir=Path(tmpdir),
                config=config,
                state_getter=lambda: {},
            )

            assert context.wait_strategy == "sleep"


class TestSupervisorSemanticValidation:
    def test_semantic_check_execution_guard_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "exec_results": [
                    {"step": "step1", "statuses": ["success"], "output": "All good"},
                    {"step": "step2", "statuses": ["success"], "output": "Also good"},
                ]
            }

            context = SupervisorContext(
                phase_id="execution_guard",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: state,
                semantic_check=True,
            )
            supervisor = PhaseSupervisor(context, lambda: state)

            result = supervisor._semantic_check_execution_guard({})

            assert result["valid"] is True

    def test_semantic_check_execution_guard_with_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "exec_results": [
                    {"step": "step1", "statuses": ["error"], "output": "Traceback: division by zero"},
                    {"step": "step2", "statuses": ["success"], "output": "OK"},
                ]
            }

            context = SupervisorContext(
                phase_id="execution_guard",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: state,
                semantic_check=True,
            )
            supervisor = PhaseSupervisor(context, lambda: state)

            result = supervisor._semantic_check_execution_guard({})

            assert result["valid"] is False
            assert result["failure_type"] == "code_runtime"
            assert result["action"] == "retry"
            assert result["retryable"] is True

    def test_semantic_check_analyze_results_missing_hypotheses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / "plan"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_file = plan_dir / "analysis_plan.json"
            plan_file.write_text(
                json.dumps({"hypotheses": [{"id": "H1", "title": "Test"}]}),
                encoding="utf-8",
            )
            result_dir = Path(tmpdir) / "result"
            result_dir.mkdir(parents=True, exist_ok=True)
            results_file = result_dir / "hypothesis_results.json"
            results_file.write_text(
                json.dumps({"hypotheses": [{"hypothesis": "H1: Test hypothesis"}]}),
                encoding="utf-8",
            )

            state = {"plan_json": {"hypotheses": []}, "exec_results": [{"step": "1", "statuses": ["success"]}]}

            context = SupervisorContext(
                phase_id="analyze_results",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: state,
                semantic_check=True,
            )
            supervisor = PhaseSupervisor(context, lambda: state)

            result = supervisor._semantic_check_analyze_results({})

            assert result["valid"] is True


class TestSupervisorFailureClassification:
    def test_classify_infrastructure_failures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = SupervisorContext(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            assert supervisor._classify_failure("Connection timeout") == "infrastructure"
            assert supervisor._classify_failure("Service unavailable error") == "infrastructure"
            assert supervisor._classify_failure("Network connection refused") == "infrastructure"

    def test_classify_semantic_drift(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = SupervisorContext(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            assert supervisor._classify_failure("Results mismatch hypothesis") == "semantic_drift"
            assert supervisor._classify_failure("Data drift detected") == "semantic_drift"

    def test_classify_evidence_insufficient(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = SupervisorContext(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            assert supervisor._classify_failure("Evidence insufficient") == "evidence_insufficient"
            assert supervisor._classify_failure("Missing evidence for hypothesis") == "evidence_insufficient"

    def test_recovery_suggestions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = SupervisorContext(
                phase_id="test",
                session_dir=Path(tmpdir),
                config={},
                state_getter=lambda: {},
            )
            supervisor = PhaseSupervisor(context, lambda: {})

            assert "check_service_status" in supervisor._suggest_recovery("infrastructure")
            assert "resync" in supervisor._suggest_recovery("semantic_drift")
            assert "supplement_evidence" in supervisor._suggest_recovery("evidence_insufficient")
            assert "regenerate_artifact" in supervisor._suggest_recovery("artifact_missing")
