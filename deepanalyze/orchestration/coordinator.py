from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable

from API.utils import execute_code_safe
from API.config import CODE_EXECUTION_TIMEOUT

from .io_utils import ensure_dir, write_json, write_text, record_artifact
from .plan_store import ArtifactRegistry
from .prompts import get_prompt, get_system


class ExecutionMonitor:
    def __init__(self, workspace_dir: Path, plan_id: str) -> None:
        self.workspace_dir = workspace_dir
        self.plan_id = plan_id
        self.log_dir = ensure_dir(self.workspace_dir / "logs" / "execution")
        self.log_path = self.log_dir / f"{plan_id}.json"
        self.entries: list[dict[str, Any]] = []

    def log_attempt(self, step_name: str, status: str, error: str | None = None) -> None:
        entry = {
            "step": step_name,
            "status": status,
            "error": error or "",
            "timestamp": int(time.time()),
        }
        self.entries.append(entry)
        write_json(self.log_path, self.entries)

    def finalize(self) -> None:
        write_json(self.log_path, self.entries)


class CodeExecutionOrchestrator:
    def __init__(self, llm: Any, config: dict[str, Any], workspace_dir: Path, plan_id: str) -> None:
        self.llm = llm
        self.config = config
        self.workspace_dir = workspace_dir
        self.plan_id = plan_id
        self.artifact_registry = ArtifactRegistry(self.workspace_dir)
        self.code_dir = self.artifact_registry.artifact_dir(plan_id, "code")
        self.legacy_code_dir = ensure_dir(self.workspace_dir / "code")

    def _write_code(self, entry: dict[str, Any]) -> dict[str, Any]:
        filename = entry.get("filename") or f"{entry.get('name','step')}.py"
        path = self.code_dir / filename
        write_text(path, entry.get("code") or "")
        legacy_path = self.legacy_code_dir / filename
        write_text(legacy_path, entry.get("code") or "")
        self.artifact_registry.register(self.plan_id, "code", path, {"step": entry.get("name", filename)})
        record_artifact(self.workspace_dir, path, "code", "generate_code")
        return {"name": entry.get("name", filename), "path": str(path)}

    def _safe_json(self, raw: str) -> dict[str, Any]:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"code": raw}

    def generate(
        self,
        steps: list[dict[str, Any]],
        worker_fn: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> list[dict[str, Any]]:
        workers = max(1, int(self.config.get("codegen_concurrency", 1)))
        recorded: list[dict[str, Any]] = []
        if workers > 1 and len(steps) > 1:
            async def _run() -> list[dict[str, Any]]:
                tasks = [asyncio.to_thread(worker_fn, step) for step in steps]
                return await asyncio.gather(*tasks)

            for entry in asyncio.run(_run()):
                recorded.append(self._write_code(entry))
        else:
            for step in steps:
                entry = worker_fn(step)
                recorded.append(self._write_code(entry))
        return recorded

    def execute(
        self,
        steps: list[dict[str, Any]],
        execution_timeout: int,
        monitor: ExecutionMonitor,
        retries: int,
    ) -> list[dict[str, Any]]:
        results_dir = self.artifact_registry.artifact_dir(self.plan_id, "result")
        legacy_results_dir = ensure_dir(self.workspace_dir / "result")
        recorded: list[dict[str, Any]] = []

        def _run(step: dict[str, Any]) -> dict[str, Any]:
            path = Path(step["path"])
            code = path.read_text(encoding="utf-8") if path.exists() else ""
            output = ""
            statuses: list[str] = []
            for attempt in range(retries + 1):
                output = execute_code_safe(code, str(self.workspace_dir), execution_timeout)
                status = "success" if "Traceback" not in output and "[Error]" not in output else "error"
                monitor.log_attempt(step.get("name", "unknown"), status, output if status == "error" else None)
                statuses.append(status)
                if status == "success":
                    break
                fix_messages = [
                    {"role": "system", "content": get_system("en")},
                    {
                        "role": "user",
                        "content": (
                            f"{get_prompt('code_fix','en')}\n\nError:\n{output}\n\nCode:\n{code}"
                        ),
                    },
                ]
                code = self.llm.chat(fix_messages, max_tokens=2048)
                write_text(path, code)
            result_path = results_dir / f"{path.stem}_output.txt"
            write_text(result_path, output)
            legacy_result = legacy_results_dir / result_path.name
            write_text(legacy_result, output)
            record_artifact(self.workspace_dir, result_path, "result", "execute_steps")
            self.artifact_registry.register(self.plan_id, "result", result_path, {"steps": step.get("name")})
            return {
                "step": step.get("name"),
                "output": output,
                "path": str(result_path),
                "statuses": statuses,
            }

        workers = max(1, int(self.config.get("execution_concurrency", 1)))
        if workers > 1 and len(steps) > 1:
            async def _run_all() -> list[dict[str, Any]]:
                tasks = [asyncio.to_thread(_run, step) for step in steps]
                return await asyncio.gather(*tasks)

            recorded = asyncio.run(_run_all())
        else:
            recorded = [_run(step) for step in steps]
        monitor.finalize()
        return recorded

