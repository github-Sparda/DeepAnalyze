"""Pipeline 变体工具函数.

从原 graph.py 中提取的 Pipeline 变体相关工具函数.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def variant_method_family(variant: str) -> str:
    """获取变体的方法家族.

    Args:
        variant: 变体名称

    Returns:
        方法家族名称
    """
    variant_map: dict[str, str] = {
        "path_a": "statistical_inference",
        "path_b": "machine_learning",
        "path_c": "embedding",
        "bootstrap": "statistical_inference",
        "permutation": "statistical_inference",
        "cross_validation": "machine_learning",
        "ensemble": "machine_learning",
    }
    return variant_map.get(variant, "statistical_inference")


def pick_path_c_variant(
    path_a_result: dict[str, Any],
    path_b_result: dict[str, Any],
    conflict_threshold: float = 0.3,
) -> dict[str, Any]:
    """选择 Path C 变体.

    Args:
        path_a_result: Path A 结果
        path_b_result: Path B 结果
        conflict_threshold: 冲突阈值

    Returns:
        Path C 选择结果
    """
    if not isinstance(path_a_result, dict):
        path_a_result = {}
    if not isinstance(path_b_result, dict):
        path_b_result = {}

    a_status = str(path_a_result.get("status", "")).strip().lower()
    b_status = str(path_b_result.get("status", "")).strip().lower()

    a_confidence = float(path_a_result.get("confidence", 0.5))
    b_confidence = float(path_b_result.get("confidence", 0.5))

    # 如果两者都成功，检查是否存在冲突
    if a_status == "success" and b_status == "success":
        a_effect = float(path_a_result.get("effect_size", 0))
        b_effect = float(path_b_result.get("effect_size", 0))

        # 效应方向相反表示冲突
        if a_effect * b_effect < 0:
            return {
                "need_path_c": True,
                "reason": "effect_direction_conflict",
                "path_a_effect": a_effect,
                "path_b_effect": b_effect,
            }

        # 效应大小差异过大
        if abs(a_effect - b_effect) > conflict_threshold:
            return {
                "need_path_c": True,
                "reason": "effect_size_discrepancy",
                "path_a_effect": a_effect,
                "path_b_effect": b_effect,
            }

    # 如果其中一个失败，可能需要 Path C
    if a_status != "success" and b_status != "success":
        return {
            "need_path_c": True,
            "reason": "both_paths_failed",
        }

    # 选择置信度更高的路径
    if a_confidence >= b_confidence:
        return {
            "need_path_c": False,
            "selected_path": "path_a",
            "confidence": a_confidence,
        }
    else:
        return {
            "need_path_c": False,
            "selected_path": "path_b",
            "confidence": b_confidence,
        }


def status_vote(results: list[dict[str, Any]]) -> dict[str, Any]:
    """状态投票.

    Args:
        results: 结果列表

    Returns:
        投票结果
    """
    if not isinstance(results, list) or not results:
        return {"status": "unknown", "confidence": 0.0}

    votes: dict[str, int] = {}
    for result in results:
        if isinstance(result, dict):
            status = str(result.get("status", "unknown")).strip().lower()
            votes[status] = votes.get(status, 0) + 1

    if not votes:
        return {"status": "unknown", "confidence": 0.0}

    # 选择票数最多的状态
    max_votes = max(votes.values())
    total_votes = sum(votes.values())
    winner = [s for s, v in votes.items() if v == max_votes][0]

    return {
        "status": winner,
        "confidence": max_votes / total_votes if total_votes > 0 else 0.0,
        "votes": votes,
    }


def run_path_c_adjudication(
    path_a_result: dict[str, Any],
    path_b_result: dict[str, Any],
    path_c_result: dict[str, Any],
) -> dict[str, Any]:
    """运行 Path C 裁决.

    Args:
        path_a_result: Path A 结果
        path_b_result: Path B 结果
        path_c_result: Path C 结果

    Returns:
        裁决结果
    """
    if not isinstance(path_a_result, dict):
        path_a_result = {}
    if not isinstance(path_b_result, dict):
        path_b_result = {}
    if not isinstance(path_c_result, dict):
        path_c_result = {}

    # 收集所有路径的结果
    all_results = [path_a_result, path_b_result, path_c_result]

    # 状态投票
    vote_result = status_vote(all_results)

    # 计算平均效应量
    effects = [
        float(r.get("effect_size", 0))
        for r in all_results
        if isinstance(r, dict)
    ]
    avg_effect = sum(effects) / len(effects) if effects else 0.0

    # 计算平均置信度
    confidences = [
        float(r.get("confidence", 0))
        for r in all_results
        if isinstance(r, dict)
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "status": vote_result.get("status", "unknown"),
        "confidence": avg_confidence,
        "effect_size": avg_effect,
        "vote_result": vote_result,
        "paths_considered": ["path_a", "path_b", "path_c"],
    }


def maybe_run_pipeline_variants(
    session_dir: Path,
    hypothesis_id: str,
    enable_path_c: bool = True,
) -> dict[str, Any]:
    """可能运行 Pipeline 变体.

    Args:
        session_dir: 会话目录
        hypothesis_id: 假设ID
        enable_path_c: 是否启用 Path C

    Returns:
        变体运行结果
    """
    result_dir = session_dir / "result"

    # 加载 Path A 结果
    path_a_file = result_dir / f"{hypothesis_id}_path_a.json"
    path_a = load_json_if_exists(path_a_file)

    # 加载 Path B 结果
    path_b_file = result_dir / f"{hypothesis_id}_path_b.json"
    path_b = load_json_if_exists(path_b_file)

    result: dict[str, Any] = {
        "hypothesis_id": hypothesis_id,
        "path_a": path_a,
        "path_b": path_b,
        "path_c": {},
        "final_status": "unknown",
    }

    # 检查是否需要 Path C
    if enable_path_c:
        pick_result = pick_path_c_variant(path_a, path_b)
        result["path_c_needed"] = pick_result.get("need_path_c", False)

        if result["path_c_needed"]:
            # 加载 Path C 结果
            path_c_file = result_dir / f"{hypothesis_id}_path_c.json"
            path_c = load_json_if_exists(path_c_file)
            result["path_c"] = path_c

            # 运行裁决
            adjudication = run_path_c_adjudication(path_a, path_b, path_c)
            result["adjudication"] = adjudication
            result["final_status"] = adjudication.get("status", "unknown")
        else:
            selected = pick_result.get("selected_path", "path_a")
            result["selected_path"] = selected
            selected_result = path_a if selected == "path_a" else path_b
            result["final_status"] = selected_result.get("status", "unknown")
    else:
        # 简单的多数投票
        vote_result = status_vote([path_a, path_b])
        result["final_status"] = vote_result.get("status", "unknown")

    return result
