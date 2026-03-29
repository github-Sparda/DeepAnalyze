from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from ..state import OrchestrationState


@dataclass
class SupervisorContext:
    phase_id: str
    session_dir: Path
    config: dict[str, Any]
    state_getter: Callable[[], OrchestrationState]
    wait_strategy: str = "poll"
    poll_interval: int = 5
    max_wait: int = 300
    max_retries: int = 3
    semantic_check: bool = True
    _check_history: list[dict[str, Any]] = field(default_factory=list)
    _wait_count: int = 0
    _start_time: float = 0.0

    @classmethod
    def from_config(
        cls,
        phase_id: str,
        session_dir: Path | str,
        config: dict[str, Any],
        state_getter: Callable[[], OrchestrationState],
    ) -> SupervisorContext:
        session_path = Path(session_dir) if isinstance(session_dir, str) else session_dir
        wait_strategy = str(config.get("supervisor_wait_strategy", "poll")).strip().lower()
        if wait_strategy not in {"poll", "sleep"}:
            wait_strategy = "poll"
        return cls(
            phase_id=phase_id,
            session_dir=session_path,
            config=config,
            state_getter=state_getter,
            wait_strategy=wait_strategy,
            poll_interval=max(1, int(config.get("supervisor_poll_interval", 5))),
            max_wait=max(10, int(config.get("supervisor_max_wait", 300))),
            max_retries=max(0, int(config.get("supervisor_max_retries", 3))),
            semantic_check=bool(config.get("supervisor_semantic_check", True)),
        )

    def record_check(self, result: dict[str, Any]) -> None:
        self._check_history.append(
            {
                "timestamp": int(time.time()),
                "phase_id": self.phase_id,
                "result": result,
            }
        )

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._check_history)

    def reset(self) -> None:
        self._check_history.clear()
        self._wait_count = 0
        self._start_time = 0.0

    def start_wait(self) -> None:
        self._start_time = time.time()
        self._wait_count = 0

    def increment_wait(self) -> int:
        self._wait_count += 1
        return self._wait_count

    def elapsed(self) -> float:
        if self._start_time == 0.0:
            return 0.0
        return time.time() - self._start_time

    def is_timeout(self) -> bool:
        return self.elapsed() >= self.max_wait
