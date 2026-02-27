from __future__ import annotations

from src.core.orchestration.recursion import DepthRecursionController


def test_depth_recursion_prompts_when_max_depth_zero():
    controller = DepthRecursionController(max_depth=0)
    decision = controller.evaluate(
        depth=0,
        followups=[],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="",
        execution_retry_count=0,
    )
    assert decision["continuation_required"] is True
    assert decision["should_recurse"] is False
    assert "continue" in decision["depth_prompt"]


def test_depth_recursion_respects_user_choice():
    controller = DepthRecursionController(max_depth=0)
    continue_decision = controller.evaluate(
        depth=0,
        followups=[],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="continue",
        execution_retry_count=0,
    )
    assert continue_decision["should_recurse"] is True
    assert continue_decision["continuation_required"] is False
    assert continue_decision["depth_prompt"] == ""

    stop_decision = controller.evaluate(
        depth=0,
        followups=[],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="stop",
        execution_retry_count=0,
    )
    assert stop_decision["should_recurse"] is False
    assert stop_decision["continuation_required"] is False
    assert stop_decision["depth_prompt"] == ""


def test_depth_recursion_requests_continuation_for_pending_followups():
    controller = DepthRecursionController(max_depth=2)
    decision = controller.evaluate(
        depth=2,
        followups=["refine metric", "validate trend"],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="",
        execution_retry_count=0,
    )
    assert decision["continuation_required"] is True
    assert decision["should_recurse"] is False
    assert decision["depth_prompt"]


def test_depth_recursion_triggers_on_unresolved_pending_before_depth_limit():
    controller = DepthRecursionController(max_depth=3)
    decision = controller.evaluate(
        depth=1,
        followups=[],
        execution_retry_requested=False,
        execution_retry_exhausted=False,
        user_decision="",
        execution_retry_count=0,
        unresolved_pending=True,
    )
    assert decision["should_recurse"] is True
    assert decision["continuation_required"] is False
