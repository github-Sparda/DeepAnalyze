from __future__ import annotations

from typing import Any


class DepthRecursionController:
    def __init__(self, max_depth: int, retry_limit: int = 1) -> None:
        self.max_depth = max_depth
        self.retry_limit = retry_limit

    def evaluate(
        self,
        depth: int,
        followups: list[str] | None,
        execution_retry_requested: bool,
        execution_retry_exhausted: bool,
        user_decision: str,
        execution_retry_count: int = 0,
        unresolved_pending: bool = False,
    ) -> dict[str, Any]:
        followups = followups or []
        decision = {"should_recurse": False, "continuation_required": False, "depth_prompt": ""}
        if execution_retry_requested and not execution_retry_exhausted:
            decision.update(
                {
                    "should_recurse": True,
                    "continuation_required": False,
                    "depth_prompt": "Execution failure detected，正在 retry。",
                }
            )
            return decision

        if depth < self.max_depth:
            if unresolved_pending:
                return {"should_recurse": True, "continuation_required": False, "depth_prompt": ""}
            if followups:
                return {"should_recurse": True, "continuation_required": False, "depth_prompt": ""}
            if execution_retry_exhausted and execution_retry_count < self.retry_limit:
                return {"should_recurse": True, "continuation_required": False, "depth_prompt": ""}
            return decision

        if self.max_depth == 0:
            if user_decision == "continue":
                return {"should_recurse": True, "continuation_required": False, "depth_prompt": ""}
            if user_decision == "stop":
                return {"should_recurse": False, "continuation_required": False, "depth_prompt": ""}
            return {
                "should_recurse": False,
                "continuation_required": True,
                "depth_prompt": "初次分析已完成。\n回复 'continue' 以开始更深一层的分析，否则输入 'stop' 结束。",
            }

        if followups or unresolved_pending:
            preview_items = followups[:3]
            if not preview_items and unresolved_pending:
                preview_items = ["存在未完成验证项或冲突证据，建议继续迭代收敛。"]
            preview = "; ".join(preview_items)
            prompt = (
                f"Reached depth limit ({self.max_depth}) with pending follow-ups"
                f"{f' (retries: {execution_retry_count})' if execution_retry_count else ''}: "
                f"{preview}. Reply 'continue' to dig deeper or 'stop' to finish."
            )
            return {
                "should_recurse": False,
                "continuation_required": True,
                "depth_prompt": prompt,
            }
        return decision
