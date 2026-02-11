from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import normalize_output_dir
from src.core.visualization.plotter import render_chord_placeholder


def run(input_path: str, output_dir: str, **kwargs: Any) -> dict[str, Any]:
    out_dir = normalize_output_dir(output_dir, "plots")
    path = Path(out_dir) / "chord_placeholder.html"
    render_chord_placeholder(path, message="Chord diagram placeholder generated.")
    return {"module": "viz_chord", "status": "ok", "output": str(path)}
