from __future__ import annotations

from typing import Any, Literal, TypedDict


class ValidationResult(TypedDict, total=False):
    valid: bool
    reason: str
    retryable: bool
    action: Literal["continue", "retry", "skip", "abort"]
    notes: list[str]
    failure_type: str
    recovery_action: str
    blocking: bool
    waiver_reason: str
    derived_from: list[str]
    timestamp: int


def make_success_result(
    reason: str = "",
    notes: list[str] | None = None,
    derived_from: list[str] | None = None,
) -> ValidationResult:
    return ValidationResult(
        valid=True,
        reason=reason or "Validation passed",
        retryable=False,
        action="continue",
        notes=list(notes) if notes else [],
        failure_type="",
        recovery_action="",
        blocking=False,
        waiver_reason="",
        derived_from=list(derived_from) if derived_from else [],
        timestamp=int(__import__("time").time()),
    )


def make_failure_result(
    reason: str,
    action: Literal["continue", "retry", "skip", "abort"] = "abort",
    retryable: bool = False,
    failure_type: str = "unknown",
    recovery_action: str = "",
    blocking: bool = True,
    notes: list[str] | None = None,
    waiver_reason: str = "",
    derived_from: list[str] | None = None,
) -> ValidationResult:
    return ValidationResult(
        valid=False,
        reason=reason,
        retryable=retryable,
        action=action,
        notes=list(notes) if notes else [],
        failure_type=failure_type,
        recovery_action=recovery_action,
        blocking=blocking,
        waiver_reason=waiver_reason,
        derived_from=list(derived_from) if derived_from else [],
        timestamp=int(__import__("time").time()),
    )
