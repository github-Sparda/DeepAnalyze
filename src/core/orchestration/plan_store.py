from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Tuple

from .io_utils import ensure_dir, write_json, write_text


class PlanStore:
    def __init__(self, data_sessions_active_dir: Path) -> None:
        self.data_sessions_active_dir = Path(data_sessions_active_dir)
        self.plans_dir = ensure_dir(self.data_sessions_active_dir / "plans")

    def _make_plan_id(self, plan_text: str) -> str:
        digest = hashlib.sha256(plan_text.encode("utf-8")).hexdigest()[:8]
        return f"plan_{int(time.time())}_{digest}"

    def _artifact_plan_dir(self, plan_id: str) -> Path:
        return ensure_dir(self.data_sessions_active_dir / "artifacts" / plan_id / "plan")

    def save_plan(
        self, plan_text: str, plan_json: dict[str, Any] | None = None, hypotheses: list[str] | None = None
    ) -> Tuple[str, Path]:
        plan_id = self._make_plan_id(plan_text)
        plan_dir = ensure_dir(self.plans_dir / plan_id)
        plan_md = plan_dir / "docs/analysis_plan.md"
        write_text(plan_md, plan_text)
        plan_meta: dict[str, Any] = {
            "plan_id": plan_id,
            "created_at": int(time.time()),
            "hypotheses": hypotheses or [],
        }
        if plan_json:
            plan_meta["structure"] = plan_json
            write_json(plan_dir / "docs/analysis_plan.json", plan_json)
        write_json(plan_dir / "meta.json", plan_meta)

        artifact_dir = self._artifact_plan_dir(plan_id)
        write_text(artifact_dir / "docs/analysis_plan.md", plan_text)
        if plan_json:
            write_json(artifact_dir / "docs/analysis_plan.json", plan_json)
        write_json(artifact_dir / "meta.json", plan_meta)

        return plan_id, plan_dir

    def save_followup(self, plan_id: str, followup: str) -> Path:
        plan_dir = ensure_dir(self.plans_dir / plan_id)
        followup_path = plan_dir / f"followup_{int(time.time())}.md"
        write_text(followup_path, followup)
        artifact_dir = self._artifact_plan_dir(plan_id)
        artifact_followup = artifact_dir / followup_path.name
        write_text(artifact_followup, followup)
        return followup_path

    def load_plan(self, plan_id: str) -> dict[str, Any]:
        plan_dir = self.plans_dir / plan_id
        payload: dict[str, Any] = {"plan_id": plan_id}
        plan_md = plan_dir / "docs/analysis_plan.md"
        plan_json = plan_dir / "docs/analysis_plan.json"
        meta_path = plan_dir / "meta.json"
        if plan_md.exists():
            payload["plan_text"] = plan_md.read_text(encoding="utf-8")
        if plan_json.exists():
            try:
                payload["plan_json"] = json.loads(plan_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload["plan_json"] = {}
        if meta_path.exists():
            try:
                payload["meta"] = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload["meta"] = {}
        return payload


class ArtifactRegistry:
    def __init__(self, data_sessions_active_dir: Path) -> None:
        self.data_sessions_active_dir = Path(data_sessions_active_dir)
        self.artifacts_dir = ensure_dir(self.data_sessions_active_dir / "artifacts")

    def _registry_path(self, plan_id: str) -> Path:
        plan_dir = ensure_dir(self.artifacts_dir / plan_id)
        return plan_dir / "registry.json"

    def artifact_dir(self, plan_id: str, role: str) -> Path:
        return ensure_dir(self.artifacts_dir / plan_id / role)

    def register(
        self,
        plan_id: str,
        kind: str,
        path: Path | str,
        metadata: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> None:
        entry = {
            "plan_id": plan_id,
            "kind": kind,
            "path": str(path),
            "timestamp": int(time.time()),
            "status": status or "ok",
            "metadata": metadata or {},
        }
        registry_path = self._registry_path(plan_id)
        existing = []
        if registry_path.exists():
            try:
                existing = json.loads(registry_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = []
        existing.append(entry)
        write_json(registry_path, existing)

    def list(self, plan_id: str, kind: str | None = None) -> list[dict[str, Any]]:
        path = self._registry_path(plan_id)
        if not path.exists():
            return []
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if kind:
            return [entry for entry in entries if entry.get("kind") == kind]
        return entries
