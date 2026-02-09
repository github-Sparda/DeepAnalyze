from __future__ import annotations

from typing import Any

from .prompts import get_prompt, get_system, render_role_prompt


class HypothesisPlanner:
    def __init__(self, llm: Any, language: str) -> None:
        self.llm = llm
        self.language = language

    def plan(
        self,
        summary: str,
        history: list[str] | None = None,
        plan_id: str | None = None,
        artifact_context: str | None = None,
        telemetry_context: str | None = None,
        goal_hint: str | None = None,
    ) -> str:
        history_text = "\n".join(history or []) or "N_A"
        messages = render_role_prompt(
            "hypothesis_planner",
            self.language,
            prompt_key="hypothesis_planner",
            summary=summary,
            history=history_text,
            plan_id=plan_id or "",
            artifact_context=artifact_context or "",
            telemetry_context=telemetry_context or "",
            goal_hint=goal_hint or "",
        )
        if not messages:
            system = get_system(self.language)
            prompt = get_prompt("hypothesis_planner", self.language)
            messages = [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nSummary:\n{summary}\n\nHistory:\n{history_text}\n\n"
                        f"Telemetry:\n{telemetry_context or 'N_A'}"
                    ),
                },
            ]
        return self.llm.chat(messages, max_tokens=4096)
