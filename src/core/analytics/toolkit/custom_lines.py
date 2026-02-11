from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .common import ensure_dir, write_json

LINES_FILE = "lines.json"
STATS_FILE = "stats.json"
SUMMARY_FILE = "line_summary.json"
CANDIDATES_FILE = "promotion_candidates.json"


def _storage_dir(base_dir: str | Path) -> Path:
    return ensure_dir(Path(base_dir) / "meta" / "custom_lines")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def list_lines(base_dir: str | Path) -> list[dict[str, Any]]:
    storage = _storage_dir(base_dir)
    return _load_json(storage / LINES_FILE, [])


def register_line(base_dir: str | Path, line_def: dict[str, Any]) -> dict[str, Any]:
    storage = _storage_dir(base_dir)
    lines = _load_json(storage / LINES_FILE, [])
    line_id = line_def.get("line_id") or f"line_{int(time.time())}"
    line_def = {**line_def, "line_id": line_id, "created_at": line_def.get("created_at", int(time.time()))}
    lines.append(line_def)
    write_json(storage / LINES_FILE, lines)
    return line_def


def load_line(base_dir: str | Path, line_id: str) -> dict[str, Any] | None:
    for line in list_lines(base_dir):
        if line.get("line_id") == line_id:
            return line
    return None


def _load_stats(base_dir: str | Path) -> dict[str, Any]:
    storage = _storage_dir(base_dir)
    return _load_json(storage / STATS_FILE, {})


def record_usage(base_dir: str | Path, line_id: str, success: bool, failure_reason: str | None = None) -> None:
    stats = _load_stats(base_dir)
    entry = stats.get(line_id) or {"runs": 0, "success": 0, "failures": [], "last_failure_at": None}
    entry["runs"] += 1
    if success:
        entry["success"] += 1
    else:
        entry["failures"].append(failure_reason or "unknown")
        entry["last_failure_at"] = int(time.time())
    stats[line_id] = entry
    storage = _storage_dir(base_dir)
    write_json(storage / STATS_FILE, stats)


def summarize_lines(base_dir: str | Path) -> dict[str, Any]:
    stats = _load_stats(base_dir)
    summary = []
    for line_id, entry in stats.items():
        runs = entry.get("runs", 0)
        success = entry.get("success", 0)
        rate = float(success) / runs if runs else 0.0
        summary.append({"line_id": line_id, "runs": runs, "success_rate": rate})
    summary.sort(key=lambda x: (x["success_rate"], x["runs"]), reverse=True)
    payload = {"updated_at": int(time.time()), "lines": summary}
    storage = _storage_dir(base_dir)
    write_json(storage / SUMMARY_FILE, payload)
    return payload


def promotion_candidates(base_dir: str | Path, min_runs: int, min_success_rate: float) -> dict[str, Any]:
    summary = summarize_lines(base_dir)
    candidates = [
        line
        for line in summary.get("lines", [])
        if line.get("runs", 0) >= min_runs and line.get("success_rate", 0.0) >= min_success_rate
    ]
    payload = {"updated_at": int(time.time()), "candidates": candidates}
    storage = _storage_dir(base_dir)
    write_json(storage / CANDIDATES_FILE, payload)
    return payload


def maybe_summarize(
    base_dir: str | Path,
    interval_days: int,
    min_runs: int,
    min_success_rate: float,
) -> dict[str, Any]:
    storage = _storage_dir(base_dir)
    summary_path = storage / SUMMARY_FILE
    if summary_path.exists():
        try:
            last = json.loads(summary_path.read_text(encoding="utf-8")).get("updated_at", 0)
        except Exception:
            last = 0
    else:
        last = 0
    if (int(time.time()) - int(last)) < interval_days * 86400:
        return _load_json(summary_path, {"lines": []})
    promotion_candidates(base_dir, min_runs, min_success_rate)
    return summarize_lines(base_dir)


def promote_line(base_dir: str | Path, line_id: str) -> dict[str, Any]:
    line = load_line(base_dir, line_id)
    if not line:
        raise ValueError(f"Line ID not found: {line_id}")
    promoted_path = Path(__file__).with_name("promoted_lines.json")
    promoted = _load_json(promoted_path, [])
    if not isinstance(promoted, list):
        promoted = []
    if any(item.get("line_id") == line_id for item in promoted if isinstance(item, dict)):
        return {"status": "skipped", "reason": "already_promoted", "line_id": line_id}
    promoted.append(line)
    write_json(promoted_path, promoted)
    return {"status": "ok", "line_id": line_id, "path": str(promoted_path)}
