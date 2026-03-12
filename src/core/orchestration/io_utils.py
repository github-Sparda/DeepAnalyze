from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from src.core.common import ensure_dir, load_json, save_json


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


def init_data_sessions_active(data_sessions_active_dir: str | Path) -> dict[str, Path]:
    base = Path(data_sessions_active_dir)
    ensure_dir(base)
    dirs = {name: ensure_dir(base / rel) for name, rel in WORKSPACE_DIRS.items()}
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        save_json(manifest_path, [])
    return dirs


def _load_manifest(data_sessions_active_dir: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(data_sessions_active_dir) / "manifest.json"
    return load_json(manifest_path, [])


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
    manifest = load_json(manifest_path, [])
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
    """保存文本文件,自动创建父目录.
    
    注意: 此函数保留以向后兼容,新代码应使用 src.core.common.save_text
    """
    from src.core.common import save_text
    return save_text(path, content)


def write_json(path: str | Path, payload: Any) -> Path:
    """保存JSON文件,自动创建父目录.
    
    注意: 此函数保留以向后兼容,新代码应使用 src.core.common.save_json
    """
    return save_json(path, payload)


def artifact_dir(data_sessions_active_dir: str | Path, plan_id: str, role: str) -> Path:
    return ensure_dir(Path(data_sessions_active_dir) / "artifacts" / plan_id / role)


def artifact_link(source_path: str | Path, dest_dir: str | Path) -> Path:
    src = Path(source_path)
    dest = ensure_dir(dest_dir) / src.name
    if dest.resolve() == src.resolve():
        return dest
    try:
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(src)
    except Exception:
        # fallback to copy on unsupported filesystems
        dest.write_bytes(src.read_bytes())
    return dest


def copy_artifact(source_path: str | Path, dest_dir: str | Path) -> Path:
    src = Path(source_path)
    dest = ensure_dir(dest_dir) / src.name
    if src.resolve() != dest.resolve():
        dest.write_bytes(src.read_bytes())
    return dest
