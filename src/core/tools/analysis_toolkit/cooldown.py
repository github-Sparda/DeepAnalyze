from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import json


def _load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def record_failure(base_dir: str | Path, line_id: str, cooldown_seconds: int) -> None:
    path = Path(base_dir) / "meta" / "custom_lines" / "cooldown.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load(path, {})
    payload[line_id] = int(time.time()) + cooldown_seconds
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def in_cooldown(base_dir: str | Path, line_id: str) -> bool:
    path = Path(base_dir) / "meta" / "custom_lines" / "cooldown.json"
    payload = _load(path, {})
    until = payload.get(line_id)
    if not until:
        return False
    return int(time.time()) < int(until)
