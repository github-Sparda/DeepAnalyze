from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from deepanalyze.orchestration.io_utils import ensure_dir, write_json
from deepanalyze.orchestration.plan_store import ArtifactRegistry


def _is_plotly(fig: Any) -> bool:
    return hasattr(fig, "write_html") and hasattr(fig, "to_json")


def _normalize_matplotlib(fig: Any) -> Figure | None:
    if isinstance(fig, Figure):
        return fig
    if isinstance(fig, Axes):
        return fig.figure
    return None


def _write_matplotlib_html(fig: Figure, html_path: Path, png_path: Path) -> None:
    fig.savefig(png_path, dpi=200)
    payload = base64.b64encode(png_path.read_bytes()).decode("ascii")
    html_path.write_text(
        f"<html><body><img src='data:image/png;base64,{payload}' /></body></html>",
        encoding="utf-8",
    )


def _write_plotly_html(fig: Any, html_path: Path) -> None:
    fig.write_html(str(html_path))


def _write_plotly_png(fig: Any, png_path: Path) -> None:
    try:
        fig.write_image(str(png_path))
    except Exception:
        fig_json = fig.to_json()
        placeholder = plt.figure(figsize=(6, 3))
        plt.text(0.5, 0.5, "Plotly PNG export unavailable", ha="center", va="center")
        plt.axis("off")
        placeholder.tight_layout()
        placeholder.savefig(png_path, dpi=200)
        plt.close(placeholder)
        png_path.with_suffix(".json").write_text(fig_json, encoding="utf-8")


def _append_log(log_path: Path, entries: list[dict[str, Any]]) -> None:
    existing: list[dict[str, Any]] = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing.extend(entries)
    write_json(log_path, existing)


def visualization_writer(
    fig: Any,
    workspace_dir: str | Path,
    plan_id: str,
    style: str = "academic",
    name: str | None = None,
    formats: Iterable[str] | None = None,
    registry: ArtifactRegistry | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    formats = list(formats or ("png", "html"))
    timestamp = int(time.time() * 1000)
    base = name or "visual"
    output_dir = ensure_dir(Path(workspace_dir) / "artifacts" / plan_id / "visualizations" / style)
    registry = registry or ArtifactRegistry(Path(workspace_dir))
    entries: list[dict[str, Any]] = []

    is_plotly = _is_plotly(fig)
    mpl_fig = _normalize_matplotlib(fig)
    for fmt in formats:
        output_path = output_dir / f"{base}_{timestamp}.{fmt}"
        if fmt == "html":
            if is_plotly:
                _write_plotly_html(fig, output_path)
            elif mpl_fig:
                png_path = output_path.with_suffix(".png")
                _write_matplotlib_html(mpl_fig, output_path, png_path)
            else:
                output_path.write_text("<html><body>No visualization</body></html>", encoding="utf-8")
        elif fmt == "png":
            if is_plotly:
                _write_plotly_png(fig, output_path)
            elif mpl_fig:
                mpl_fig.savefig(output_path, dpi=200)
            else:
                placeholder = plt.figure(figsize=(6, 3))
                plt.text(0.5, 0.5, "Visualization unavailable", ha="center", va="center")
                plt.axis("off")
                placeholder.tight_layout()
                placeholder.savefig(output_path, dpi=200)
                plt.close(placeholder)
        else:
            continue

        entry = {
            "plan_id": plan_id,
            "style": style,
            "format": fmt,
            "path": str(output_path),
            "timestamp": timestamp,
            "metadata": metadata or {},
        }
        entries.append(entry)
        registry.register(
            plan_id,
            "visualization",
            output_path,
            {"style": style, "format": fmt, **(metadata or {})},
            status="ok",
        )

    log_dir = ensure_dir(Path(workspace_dir) / "logs" / "visualizations")
    log_path = log_dir / f"{plan_id}.json"
    _append_log(log_path, entries)
    return entries
