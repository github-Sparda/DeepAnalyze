"""配置加载工具函数.

从原 graph.py 中提取的配置相关工具函数.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def load_analysis_runtime_config(session_dir: Path | None = None) -> dict[str, Any]:
    """加载分析运行时配置.

    从多个候选位置加载配置,合并默认值和用户配置.

    Args:
        session_dir: 会话目录路径

    Returns:
        合并后的配置字典
    """
    defaults = {
        "required_result_artifacts": [
            "analysis_results.md",
            "stats_results.json",
            "correlation.json",
            "feature_selection.json",
            "hypothesis_evidence.json",
            "hypothesis_evidence_pack.json",
            "hypothesis_evidence_pack_validation.json",
            "hypothesis_contrast.json",
            "hypothesis_multipath.json",
            "hypothesis_validation_contract.json",
            "hypothesis_gate_report.json",
            "expected_artifact_validation.json",
            "hypothesis_matrix.json",
            "coverage_report.json",
            "visual_binding.json",
            "model_eval.json",
            "cv_results.json",
        ]
    }
    candidates: list[Path] = []
    if isinstance(session_dir, Path):
        candidates.append(session_dir / "config" / "analysis_runtime.json")
    candidates.append(Path("config") / "analysis_runtime.json")
    for path in candidates:
        payload = load_json_if_exists(path)
        if not payload:
            continue
        merged = dict(defaults)
        merged.update(payload)
        return merged
    return defaults