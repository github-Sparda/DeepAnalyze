from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import load_table, numeric_columns, write_json, normalize_output_dir


def _kmeans(data: np.ndarray, k: int = 3, iterations: int = 10) -> np.ndarray:
    if data.size == 0:
        return np.array([])
    rng = np.random.default_rng(0)
    centroids = data[rng.choice(data.shape[0], size=min(k, data.shape[0]), replace=False)]
    for _ in range(iterations):
        distances = ((data[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)
        for i in range(centroids.shape[0]):
            if np.any(labels == i):
                centroids[i] = data[labels == i].mean(axis=0)
    return labels


def run(input_path: str | Path, output_dir: str | Path, method: str = "kmeans", k: int = 3) -> dict[str, Any]:
    df = load_table(input_path)
    num_cols = numeric_columns(df)
    out_dir = normalize_output_dir(output_dir, "result")
    if not num_cols:
        payload = {"status": "skipped", "reason": "no numeric columns"}
        write_json(out_dir / "clustering.json", payload)
        return {"module": "clustering", "status": "skipped", "output": str(out_dir / "clustering.json")}
    data = df[num_cols].fillna(0).to_numpy()
    labels = _kmeans(data, k=k)
    payload = {"method": method, "k": k, "labels": labels.tolist()}
    write_json(out_dir / "clustering.json", payload)
    return {"module": "clustering", "status": "ok", "output": str(out_dir / "clustering.json")}
