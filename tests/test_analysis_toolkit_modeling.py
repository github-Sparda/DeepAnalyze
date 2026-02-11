from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.tools.analysis_toolkit import model_train, model_eval


def test_model_train_eval_centroid(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "Group": ["Normal1", "Normal2", "Generalized1", "Generalized2"],
            "peak1": [0.1, 0.12, 0.9, 0.95],
            "peak2": [0.05, 0.06, 0.8, 0.85],
        }
    )
    input_path = tmp_path / "sample.csv"
    df.to_csv(input_path, index=False)

    train_result = model_train.run(input_path, tmp_path)
    assert train_result["status"] == "ok"
    model_path = tmp_path / "result" / "model_results.json"
    assert model_path.exists()

    eval_result = model_eval.run(input_path, tmp_path, model_path=model_path)
    assert eval_result["status"] == "ok"
    eval_path = tmp_path / "result" / "model_eval.json"
    payload = json.loads(eval_path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})
    assert "majority_accuracy" in metrics
    assert "centroid_accuracy" in metrics
