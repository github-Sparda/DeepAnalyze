from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


WORKSPACE_DIRS = {
    "input": "input",
    "plan": "plan",
    "code": "code",
    "result": "result",
    "report": "report",
    "log": "outputs_logs",
    "meta": "meta",
    "charts": "charts",
}


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def init_data_sessions_active(data_sessions_active_dir: str | Path) -> dict[str, Path]:
    base = Path(data_sessions_active_dir)
    base.mkdir(parents=True, exist_ok=True)
    dirs = {name: ensure_dir(base / rel) for name, rel in WORKSPACE_DIRS.items()}
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        write_json(manifest_path, [])
    return dirs


def _load_manifest(data_sessions_active_dir: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(data_sessions_active_dir) / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def record_artifact(
    data_sessions_active_dir: str | Path,
    path: str | Path,
    kind: str,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    entry = {
        "path": str(path),
        "kind": kind,
        "source": source,
        "timestamp": int(time.time()),
        "metadata": metadata or {},
    }
    manifest = _load_manifest(data_sessions_active_dir)
    manifest.append(entry)
    write_json(Path(data_sessions_active_dir) / "manifest.json", manifest)


def record_node_log(
    data_sessions_active_dir: str | Path,
    node_name: str,
    payload: dict[str, Any],
) -> Path:
    log_dir = ensure_dir(Path(data_sessions_active_dir) / WORKSPACE_DIRS["log"] / "nodes")
    timestamp = int(time.time() * 1000)
    path = log_dir / f"{node_name}_{timestamp}.json"
    write_json(path, payload)
    return path


def record_run_summary(data_sessions_active_dir: str | Path, summary: dict[str, Any]) -> Path:
    meta_dir = ensure_dir(Path(data_sessions_active_dir) / WORKSPACE_DIRS["meta"])
    path = meta_dir / "run_summary.json"
    write_json(path, summary)
    return path


def record_role_output(
    data_sessions_active_dir: str | Path,
    role_id: str,
    status: str,
    output: dict[str, Any] | None = None,
    error: str | None = None,
    duration_sec: float | None = None,
    inputs: list[str] | None = None,
    artifacts: list[str] | None = None,
) -> Path:
    meta_dir = ensure_dir(Path(data_sessions_active_dir) / WORKSPACE_DIRS["meta"])
    manifest_path = meta_dir / "role_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = []
    else:
        manifest = []
    entry = {
        "role_id": role_id,
        "status": status,
        "duration_sec": duration_sec,
        "error": error,
        "inputs": inputs or [],
        "artifacts": artifacts or [],
        "output_keys": sorted(list((output or {}).keys())),
        "timestamp": int(time.time()),
    }
    manifest.append(entry)
    write_json(manifest_path, manifest)
    return manifest_path


def hash_file(path: str | Path) -> str:
    p = Path(path)
    digest = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_run_metadata(data_sessions_active_dir: str | Path, metadata: dict[str, Any]) -> Path:
    meta_dir = ensure_dir(Path(data_sessions_active_dir) / WORKSPACE_DIRS["meta"])
    path = meta_dir / "run_metadata.json"
    write_json(path, metadata)
    return path


def write_text(path: str | Path, content: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def write_json(path: str | Path, payload: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def artifact_dir(data_sessions_active_dir: str | Path, plan_id: str, role: str) -> Path:
    return ensure_dir(Path(data_sessions_active_dir) / "artifacts" / plan_id / role)


def copy_artifact(source_path: str | Path, dest_dir: str | Path) -> Path:
    src = Path(source_path)
    dest = ensure_dir(dest_dir) / src.name
    if src.resolve() != dest.resolve():
        dest.write_bytes(src.read_bytes())
    return dest
