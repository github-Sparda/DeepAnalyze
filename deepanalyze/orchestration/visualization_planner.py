from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Any, Iterable


def _load_dataframe(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    suffix = path.suffix.lower()
    try:
        if suffix in {".csv"}:
            return pd.read_csv(path)
        if suffix in {".tsv"}:
            return pd.read_csv(path, sep="\t")
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        if suffix in {".json"}:
            return pd.read_json(path)
    except Exception:
        return None
    return None


class VisualizationPlanner:
    def __init__(self, workspace_dir: Path, max_items: int = 6) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.max_items = max_items

    def plan(self, datasets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        instructions: list[dict[str, Any]] = []
        for dataset in datasets:
            if len(instructions) >= self.max_items:
                break
            path_str = dataset.get("path", "")
            if not path_str:
                continue
            path = Path(path_str)
            df = _load_dataframe(path)
            if df is None or df.empty:
                continue
            numeric = df.select_dtypes(include="number").columns.tolist()
            categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

            if numeric:
                instructions.append(
                    {
                        "type": "distribution",
                        "dataset": dataset.get("file", path.name),
                        "dataset_path": str(path),
                        "columns": [numeric[0]],
                        "goal": "Understand distribution of primary numeric column",
                    }
                )
            if len(numeric) >= 2 and len(instructions) < self.max_items:
                instructions.append(
                    {
                        "type": "correlation",
                        "dataset": dataset.get("file", path.name),
                        "dataset_path": str(path),
                        "columns": numeric[:4],
                        "goal": "Inspect relationships among numeric variables",
                    }
                )
            if numeric and categorical and len(instructions) < self.max_items:
                instructions.append(
                    {
                        "type": "comparison",
                        "dataset": dataset.get("file", path.name),
                        "dataset_path": str(path),
                        "columns": [categorical[0], numeric[0]],
                        "goal": "Compare numeric metric across key categories",
                    }
                )
            if len(numeric) >= 2 and len(instructions) < self.max_items:
                instructions.append(
                    {
                        "type": "trend",
                        "dataset": dataset.get("file", path.name),
                        "dataset_path": str(path),
                        "columns": numeric[:2],
                        "goal": "Trace trends over sequential numeric fields",
                    }
                )
            if len(instructions) < self.max_items:
                instructions.append(
                    {
                        "type": "table",
                        "dataset": dataset.get("file", path.name),
                        "dataset_path": str(path),
                        "columns": list(df.columns[:4]),
                        "goal": "Show sample rows for reference",
                    }
                )
        return instructions


def load_dataframe(path: Path) -> pd.DataFrame | None:
    return _load_dataframe(path)
