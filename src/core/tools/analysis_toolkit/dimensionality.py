from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, numeric_columns, write_json, normalize_output_dir


def _run_tsne(data: np.ndarray, n_components: int) -> list[list[float]] | None:
    try:
        from sklearn.manifold import TSNE  # type: ignore
    except Exception:
        return None
    tsne = TSNE(n_components=n_components, init="random", random_state=0, perplexity=5)
    coords = tsne.fit_transform(data).tolist()
    return coords


def run(input_path: str | Path, output_dir: str | Path, method: str = "pca", n_components: int = 2) -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not num_cols:
        payload = {"status": "skipped", "reason": "no numeric columns"}
        write_json(out_dir / "dimensionality.json", payload)
        return {"module": "dimensionality", "status": "skipped", "output": str(out_dir / "dimensionality.json")}
    data = df[num_cols].fillna(0).to_numpy()
    output_name = "dimensionality.json"
    coords: list[list[float]] | None = None
    if method == "tsne":
        coords = _run_tsne(data, n_components)
        output_name = "dimensionality_tsne.json"
    if coords is None:
        data_centered = data - data.mean(axis=0, keepdims=True)
        u, s, vt = np.linalg.svd(data_centered, full_matrices=False)
        coords = (u[:, :n_components] * s[:n_components]).tolist()
    payload = {"method": method, "components": n_components, "coords": coords}
    out_path = out_dir / output_name
    write_json(out_path, payload)
    return {"module": "dimensionality", "status": "ok", "output": str(out_path)}
