from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoleInput:
    role_id: str
    plan_id: str | None
    session_dir: str
    inputs: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "plan_id": self.plan_id,
            "session_dir": self.session_dir,
            "inputs": self.inputs,
            "config": self.config,
            "artifacts": self.artifacts,
        }


@dataclass
class RoleOutput:
    role_id: str
    status: str
    artifacts: list[str] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "status": self.status,
            "artifacts": self.artifacts,
            "results": self.results,
            "errors": self.errors,
            "metrics": self.metrics,
        }
