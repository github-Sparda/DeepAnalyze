from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import matplotlib.pyplot as plt
import pandas as pd

from .common import normalize_output_dir
from .viz_theme import apply_theme


def _load_embedding(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".json":
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            coords = payload.get("coords") if isinstance(payload, dict) else None
            if coords:
                df = pd.DataFrame(coords)
            else:
                df = pd.DataFrame(payload)
        except Exception:
            df = pd.read_json(p)
    else:
        df = pd.read_csv(p)
    if df.shape[1] >= 2:
        df = df.iloc[:, :2]
        df.columns = ["x", "y"]
    return df


def run(
    input_path: str | Path,
    output_dir: str | Path,
    labels_path: str | Path | None = None,
    name: str = "embedding_scatter",
    theme: dict[str, Any] | None = None,
) -> dict[str, Any]:
    df = _load_embedding(input_path)
    if df.empty or df.shape[1] < 2:
        return {"module": "viz_embedding", "status": "skipped", "message": "embedding missing"}
    labels = None
    if labels_path:
        p = Path(labels_path)
        if p.exists():
            try:
                payload = pd.read_json(p)
                if "labels" in payload.columns:
                    labels = payload["labels"].tolist()
                elif "labels" in payload:
                    labels = payload["labels"]
            except Exception:
                pass
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots(figsize=(5, 4))
    if labels and len(labels) == len(df):
        ax.scatter(df["x"], df["y"], c=labels, s=12, cmap="viridis")
    else:
        ax.scatter(df["x"], df["y"], s=12)
    ax.set_title("Embedding Scatter")
    path = out_dir / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_embedding", "status": "ok", "output": str(path)}
