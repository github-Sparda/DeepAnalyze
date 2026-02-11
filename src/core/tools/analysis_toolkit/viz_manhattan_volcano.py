from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import default_output, write_json, normalize_output_dir


def run(input_path: str | Path, output_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
    out_dir = normalize_output_dir(output_dir, "result")
    payload = default_output("viz_manhattan_volcano", "not_implemented", "Module stub. Implement in follow-up.")
    write_json(out_dir / "viz_manhattan_volcano.json", payload)
    return payload
