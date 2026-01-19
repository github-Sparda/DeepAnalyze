from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import ensure_dir, write_json
from .plan_store import ArtifactRegistry


class DocumentManager:
    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.documents_dir = ensure_dir(self.workspace_dir / "documents")
        self.artifact_registry = ArtifactRegistry(self.workspace_dir)

    @property
    def manifest_path(self) -> Path:
        return self.documents_dir / "manifest.json"

    def _read_plan_meta(self, plan_id: str) -> dict[str, Any]:
        plan_dir = ensure_dir(self.workspace_dir / "plans" / plan_id)
        meta_path = plan_dir / "meta.json"
        if not meta_path.exists():
            return {}
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _plan_summary(self, plan_id: str) -> dict[str, Any]:
        entries = self.artifact_registry.list(plan_id)
        summary: dict[str, int] = {}
        for entry in entries:
            kind = entry.get("kind", "unknown")
            summary[kind] = summary.get(kind, 0) + 1
        manifest_entries = [
            {
                "path": entry.get("path", ""),
                "kind": entry.get("kind", ""),
                "metadata": entry.get("metadata", {}),
                "timestamp": entry.get("timestamp"),
            }
            for entry in entries
        ]
        return {
            "plan_id": plan_id,
            "plan_meta": self._read_plan_meta(plan_id),
            "summary": summary,
            "entries": manifest_entries,
        }

    def _list_reports(self) -> list[dict[str, Any]]:
        report_dir = self.workspace_dir / "report"
        results = []
        if not report_dir.exists():
            return results
        for path in sorted(report_dir.iterdir()):
            if not path.is_file():
                continue
            results.append(
                {
                    "name": path.name,
                    "relative_path": str(path.relative_to(self.workspace_dir)),
                    "is_html": path.suffix.lower() in {".html", ".htm"},
                    "size": path.stat().st_size,
                    "updated_at": int(path.stat().st_mtime),
                }
            )
        return results

    def _list_tables(self) -> list[dict[str, Any]]:
        result_dir = self.workspace_dir / "result"
        tables: list[dict[str, Any]] = []
        if not result_dir.exists():
            return tables
        for path in sorted(result_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".json", ".csv", ".tsv"}:
                continue
            tables.append(
                {
                    "name": path.name,
                    "relative_path": str(path.relative_to(self.workspace_dir)),
                    "type": path.suffix.lower().lstrip("."),
                    "size": path.stat().st_size,
                    "updated_at": int(path.stat().st_mtime),
                }
            )
        return tables

    def _relative_path(self, raw: str) -> str:
        if not raw:
            return ""
        try:
            return str(Path(raw).relative_to(self.workspace_dir))
        except Exception:
            return raw

    def _with_relative_paths(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        processed = []
        for entry in entries:
            relative = self._relative_path(entry.get("path", ""))
            processed.append({**entry, "relative_path": relative})
        return processed

    def _collect_visualizations(self, plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        visuals: list[dict[str, Any]] = []
        for plan in plans:
            plan_id = plan.get("plan_id", "")
            for entry in plan.get("entries", []):
                if entry.get("kind") != "visualization":
                    continue
                visuals.append(
                    {
                        "plan_id": plan_id,
                        "path": entry.get("path", ""),
                        "relative_path": entry.get("relative_path", ""),
                        "metadata": entry.get("metadata", {}),
                        "timestamp": entry.get("timestamp"),
                    }
                )
        return visuals

    def manifest(self) -> dict[str, Any]:
        manifest: dict[str, Any] = {
            "updated_at": int(time.time()),
            "plans": [],
            "reports": [],
            "tables": [],
            "artifact_counts": {},
            "visualizations": [],
        }
        artifacts_root = self.workspace_dir / "artifacts"
        if artifacts_root.exists():
            for plan_dir in sorted(
                [p for p in artifacts_root.iterdir() if p.is_dir()],
                key=lambda p: p.name,
            ):
                manifest["plans"].append(self._plan_summary(plan_dir.name))
        for plan in manifest["plans"]:
            plan["entries"] = self._with_relative_paths(plan.get("entries", []))
        artifact_counts: Counter[str] = Counter()
        for plan in manifest["plans"]:
            artifact_counts.update(plan.get("summary", {}))

        manifest["artifact_counts"] = dict(artifact_counts)
        manifest["reports"] = self._list_reports()
        manifest["tables"] = self._list_tables()
        manifest["visualizations"] = self._collect_visualizations(manifest["plans"])
        write_json(self.manifest_path, manifest)
        return manifest

    def load_manifest(self) -> dict[str, Any]:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self.manifest()
