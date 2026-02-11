from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from .common import normalize_output_dir
from .viz_theme import apply_theme


def _load_features(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".json"}:
        return pd.read_json(p)
    return pd.read_csv(p)


def run(input_path: str | Path, output_dir: str | Path, top_k: int = 10, theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = _load_features(input_path)
    if df.empty:
        return {"module": "viz_top_features", "status": "skipped", "message": "empty features"}
    if "feature" not in df.columns:
        df = df.rename(columns={df.columns[0]: "feature"})
    score_col = "q_value" if "q_value" in df.columns else "p_value" if "p_value" in df.columns else None
    if score_col:
        df = df.sort_values(score_col).head(top_k)
    else:
        df = df.head(top_k)
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(df["feature"].astype(str), range(len(df)))
    ax.invert_yaxis()
    ax.set_title("Top Features")
    ax.set_xlabel("Rank")
    path = out_dir / "top_features_bar.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return {"module": "viz_top_features", "status": "ok", "output": str(path)}
