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

    def plan(
        self,
        datasets: Iterable[dict[str, Any]],
        goals: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        instructions: list[dict[str, Any]] = []
        goal_phrases = [
            str(goal).lower()
            for goal in (goals or [])
            if isinstance(goal, str)
        ]
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
            dataset_goal = str(dataset.get("goal") or "").strip().lower()
            dataset_phrases = goal_phrases.copy()
            if dataset_goal:
                dataset_phrases.append(dataset_goal)
            numeric = df.select_dtypes(include="number").columns.tolist()
            categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
            datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
            if not datetime_cols:
                for col in df.columns:
                    lower = col.lower()
                    if "date" in lower or "time" in lower:
                        datetime_cols.append(col)
            dataset_name = dataset.get("file") or path.name

            def prefers(*keywords: str) -> bool:
                for phrase in dataset_phrases:
                    for keyword in keywords:
                        if keyword.lower() in phrase:
                            return True
                return False

            def add_instruction(entry: dict[str, Any]) -> bool:
                if len(instructions) >= self.max_items:
                    return False
                instructions.append(entry)
                return True

            def build_distribution(col: str) -> dict[str, Any]:
                return {
                    "type": "distribution",
                    "dataset": dataset_name,
                    "dataset_path": str(path),
                    "columns": [col],
                    "goal": f"Understand the distribution of {col}",
                }

            def build_correlation(cols: list[str]) -> dict[str, Any]:
                return {
                    "type": "correlation",
                    "dataset": dataset_name,
                    "dataset_path": str(path),
                    "columns": cols,
                    "goal": "Inspect relationships among related numeric fields",
                }

            def build_comparison(cat: str, num: str) -> dict[str, Any]:
                return {
                    "type": "comparison",
                    "dataset": dataset_name,
                    "dataset_path": str(path),
                    "columns": [cat, num],
                    "goal": f"Compare {num} across categories of {cat}",
                }

            def build_trend(date_col: str, num: str) -> dict[str, Any]:
                return {
                    "type": "trend",
                    "dataset": dataset_name,
                    "dataset_path": str(path),
                    "columns": [date_col, num],
                    "goal": f"Trace {num} over {date_col}",
                }

            def build_table(cols: list[str]) -> dict[str, Any]:
                return {
                    "type": "table",
                    "dataset": dataset_name,
                    "dataset_path": str(path),
                    "columns": cols,
                    "goal": f"Preview sample rows of {dataset_name}",
                }

            added_types: set[str] = set()
            prioritized = [
                (
                    "trend",
                    lambda: bool(datetime_cols) and bool(numeric),
                    lambda: build_trend(datetime_cols[0], numeric[0]),
                    ("trend", "time", "seasonal", "growth"),
                ),
                (
                    "correlation",
                    lambda: len(numeric) >= 2,
                    lambda: build_correlation(numeric[:min(4, len(numeric))]),
                    ("correlation", "relationship", "association"),
                ),
                (
                    "comparison",
                    lambda: bool(categorical) and bool(numeric),
                    lambda: build_comparison(categorical[0], numeric[0]),
                    ("compare", "segment", "rank"),
                ),
                (
                    "distribution",
                    lambda: bool(numeric),
                    lambda: build_distribution(numeric[0]),
                    ("distribution", "spread", "variation"),
                ),
            ]
            for name, condition, builder, keywords in prioritized:
                if len(instructions) >= self.max_items:
                    break
                if name in added_types:
                    continue
                if condition() and prefers(*keywords):
                    if add_instruction(builder()):
                        added_types.add(name)
            for name, condition, builder, _ in prioritized:
                if len(instructions) >= self.max_items:
                    break
                if name in added_types:
                    continue
                if condition():
                    if add_instruction(builder()):
                        added_types.add(name)
            if len(instructions) < self.max_items and len(df.columns) > 0:
                cols = list(df.columns[: min(4, len(df.columns))])
                add_instruction(build_table(cols))
        return instructions


def load_dataframe(path: Path) -> pd.DataFrame | None:
    return _load_dataframe(path)
