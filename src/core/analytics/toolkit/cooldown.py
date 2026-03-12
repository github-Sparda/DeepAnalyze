from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from src.core.common import ensure_dir, load_json, save_json


def record_failure(base_dir: str | Path, line_id: str, cooldown_seconds: int) -> None:
    path = Path(base_dir) / "meta" / "custom_lines" / "cooldown.json"
    ensure_dir(path.parent)
    payload = load_json(path, {})
    payload[line_id] = int(time.time()) + cooldown_seconds
    save_json(path, payload)


def in_cooldown(base_dir: str | Path, line_id: str) -> bool:
    path = Path(base_dir) / "meta" / "custom_lines" / "cooldown.json"
    payload = load_json(path, {})
    until = payload.get(line_id)
    if not until:
        return False
    return int(time.time()) < int(until)
