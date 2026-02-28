from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.analytics.resources import resolve_hypothesis_profile
from src.core.analytics.toolkit.common import (
    detect_group_column,
    load_analysis_runtime_config,
    select_group_labels,
)
from src.core.orchestration import hypothesis_engine


def test_group_detection_and_selection_are_configurable(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "analysis_runtime.json").write_text(
        json.dumps(
            {
                "group_column_candidates": ["cohort_name"],
                "group_selection": {
                    "reference_labels": ["Healthy"],
                    "preferred_case_labels": ["Disease"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    runtime = load_analysis_runtime_config(tmp_path)
    df = pd.DataFrame({"cohort_name": ["Healthy", "Disease_A", "Other_B"], "x": [1, 2, 3]})
    group_col = detect_group_column(df, runtime_config=runtime)
    assert group_col == "cohort_name"
    labels, info = select_group_labels(df[group_col], runtime_config=runtime)
    assert sorted(labels.dropna().unique().tolist()) == ["Disease", "Healthy"]
    assert info["method"] == "reference_vs_others"


def test_hypothesis_profile_registry_is_configurable(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "hypothesis_profile_registry.json").write_text(
        json.dumps(
            {
                "difference": {
                    "title": "自定义差异验证",
                    "hypothesis": "存在自定义差异假设。",
                    "claim": "自定义差异证据",
                    "primary_method_family": "parametric_test",
                    "secondary_method_family": "nonparametric_or_fdr",
                    "visual_artifacts": ["plots/custom.png"],
                    "aliases": ["差异"],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    profile = resolve_hypothesis_profile(tmp_path, explicit_key="difference")
    assert profile["title"] == "自定义差异验证"
    assert profile["claim"] == "自定义差异证据"


def test_runtime_logic_no_longer_embeds_fixed_hypothesis_titles() -> None:
    source = Path(hypothesis_engine.__file__).read_text(encoding="utf-8")
    for token in ["H1: 差异检验", "H2: 关键特征筛选", "H3: 相关性结构", "H4: 降维/聚类"]:
        assert token not in source
