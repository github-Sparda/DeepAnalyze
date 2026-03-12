"""计划处理工具函数.

从原 graph.py 中提取的计划解析、渲染和处理相关工具函数.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def parse_plan_markdown(plan: str) -> dict[str, Any]:
    """解析计划 Markdown 文本为结构化数据.

    Args:
        plan: Markdown 格式的计划文本

    Returns:
        解析后的计划数据结构
    """
    lines = plan.splitlines()
    current_hid: str | None = None
    hypotheses: list[dict[str, Any]] = []
    steps: list[str] = []
    artifacts: list[str] = []

    for line in lines:
        header_match = re.match(r"^###\s*(H\d+)\s*", line)
        if header_match:
            if current_hid and steps:
                hypotheses.append(
                    {
                        "id": current_hid,
                        "steps": steps.copy(),
                        "expected_artifacts": artifacts.copy(),
                    }
                )
            current_hid = header_match.group(1)
            steps = []
            artifacts = []
            continue

        if current_hid is None:
            continue

        step_match = re.match(r"^\d+\.\s*\[?([^\]]+)\]?", line)
        if step_match:
            steps.append(step_match.group(1).strip())

        artifact_match = re.match(r"^\s*-\s*输出[:：]?\s*(.+)", line)
        if artifact_match:
            artifacts.extend(
                [a.strip() for a in artifact_match.group(1).split(",") if a.strip()]
            )

    if current_hid and steps:
        hypotheses.append(
            {
                "id": current_hid,
                "steps": steps.copy(),
                "expected_artifacts": artifacts.copy(),
            }
        )

    return {"hypotheses": hypotheses}


def extract_plan_table_hypotheses(plan: str) -> dict[str, str]:
    """从计划文本中提取假设表格信息.

    Args:
        plan: 计划 Markdown 文本

    Returns:
        假设ID到描述的映射
    """
    result: dict[str, str] = {}
    lines = plan.splitlines()
    in_table = False
    headers: list[str] = []

    for line in lines:
        if "|" in line and "H" in line and "假设" in line:
            in_table = True
            headers = [h.strip() for h in line.split("|") if h.strip()]
            continue

        if in_table and line.strip().startswith("|"):
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 2:
                hid_match = re.match(r"(H\d+)", cells[0])
                if hid_match:
                    hid = hid_match.group(1)
                    desc = cells[1] if len(cells) > 1 else ""
                    result[hid] = desc

    return result


def extract_hypothesis_descriptions(plan: str) -> dict[str, str]:
    """从计划文本中提取假设描述.

    Args:
        plan: 计划 Markdown 文本

    Returns:
        假设ID到描述的映射
    """
    result: dict[str, str] = {}
    lines = plan.splitlines()
    current_hid: str | None = None

    for line in lines:
        header_match = re.match(r"^###\s*(H\d+)\s*[\-\:]?\s*(.+)", line)
        if header_match:
            current_hid = header_match.group(1)
            desc = header_match.group(2).strip()
            result[current_hid] = desc
            continue

        if current_hid and line.strip() and not line.startswith("#"):
            if current_hid not in result:
                result[current_hid] = line.strip()

    return result


def extract_hypothesis_table_steps_artifacts(plan: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """从计划文本中提取假设的步骤和产物.

    Args:
        plan: 计划 Markdown 文本

    Returns:
        (步骤映射, 产物映射)
    """
    steps_map: dict[str, list[str]] = {}
    artifacts_map: dict[str, list[str]] = {}
    lines = plan.splitlines()
    current_hid: str | None = None
    current_steps: list[str] = []
    current_artifacts: list[str] = []

    for line in lines:
        header_match = re.match(r"^###\s*(H\d+)", line)
        if header_match:
            if current_hid:
                steps_map[current_hid] = current_steps.copy()
                artifacts_map[current_hid] = current_artifacts.copy()
            current_hid = header_match.group(1)
            current_steps = []
            current_artifacts = []
            continue

        if current_hid is None:
            continue

        step_match = re.match(r"^\d+\.\s*(.+)", line)
        if step_match:
            current_steps.append(step_match.group(1).strip())

        artifact_match = re.match(r"^\s*-\s*输出[:：]?\s*(.+)", line)
        if artifact_match:
            current_artifacts.extend(
                [a.strip() for a in artifact_match.group(1).split(",") if a.strip()]
            )

    if current_hid:
        steps_map[current_hid] = current_steps
        artifacts_map[current_hid] = current_artifacts

    return steps_map, artifacts_map


def normalize_plan_json(plan_json: dict[str, Any]) -> dict[str, Any]:
    """规范化计划 JSON 数据结构.

    Args:
        plan_json: 原始计划 JSON

    Returns:
        规范化后的计划 JSON
    """
    if not isinstance(plan_json, dict):
        return {"hypotheses": []}

    hypotheses = plan_json.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return {"hypotheses": []}

    normalized: list[dict[str, Any]] = []
    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            continue

        hid = str(hyp.get("id", "")).strip()
        if not hid:
            continue

        normalized_hyp = {
            "id": hid,
            "title": str(hyp.get("title", "")).strip(),
            "hypothesis_type": str(hyp.get("hypothesis_type", "difference")).strip(),
            "description": str(hyp.get("description", "")).strip(),
            "steps": [],
            "expected_artifacts": [],
            "validation_paths": [],
        }

        steps = hyp.get("steps", [])
        if isinstance(steps, list):
            normalized_hyp["steps"] = [str(s).strip() for s in steps if s]

        artifacts = hyp.get("expected_artifacts", [])
        if isinstance(artifacts, list):
            normalized_hyp["expected_artifacts"] = [str(a).strip() for a in artifacts if a]

        paths = hyp.get("validation_paths", [])
        if isinstance(paths, list):
            normalized_hyp["validation_paths"] = paths

        normalized.append(normalized_hyp)

    return {"hypotheses": normalized}


def render_plan_markdown_from_json(plan_json: dict[str, Any]) -> str:
    """将计划 JSON 渲染为 Markdown 文本.

    Args:
        plan_json: 计划 JSON 数据

    Returns:
        Markdown 格式的计划文本
    """
    if not isinstance(plan_json, dict):
        return ""

    hypotheses = plan_json.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return ""

    lines: list[str] = []
    lines.append("# 分析计划")
    lines.append("")

    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            continue

        hid = hyp.get("id", "")
        title = hyp.get("title", "")
        lines.append(f"### {hid} {title}")
        lines.append("")

        description = hyp.get("description", "")
        if description:
            lines.append(description)
            lines.append("")

        steps = hyp.get("steps", [])
        if steps:
            lines.append("**分析步骤：**")
            for i, step in enumerate(steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        artifacts = hyp.get("expected_artifacts", [])
        if artifacts:
            lines.append("**预期产物：**")
            for artifact in artifacts:
                lines.append(f"- {artifact}")
            lines.append("")

    return "\n".join(lines)


def synthesize_plan_from_hypothesis_results(
    results: dict[str, Any],
    prior_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """从假设结果合成新的计划.

    Args:
        results: 假设结果数据
        prior_plan: 先前的计划（可选）

    Returns:
        合成后的计划 JSON
    """
    rows = results.get("hypotheses", []) if isinstance(results, dict) else []
    if not isinstance(rows, list):
        rows = []

    hypotheses: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        hid = str(row.get("hypothesis_id", "")).strip()
        if not hid:
            continue

        hyp = {
            "id": hid,
            "title": str(row.get("title", "") or row.get("hypothesis", "")).strip(),
            "hypothesis_type": str(row.get("hypothesis_type", "difference")).strip(),
            "description": str(row.get("description", "")).strip(),
            "steps": [],
            "expected_artifacts": [],
            "validation_paths": [],
        }

        status = str(row.get("status", "")).strip().lower()
        if status == "rejected":
            continue

        hypotheses.append(hyp)

    if prior_plan and isinstance(prior_plan, dict):
        prior_hypotheses = prior_plan.get("hypotheses", [])
        if isinstance(prior_hypotheses, list):
            existing_ids = {h["id"] for h in hypotheses}
            for hyp in prior_hypotheses:
                if isinstance(hyp, dict) and hyp.get("id") not in existing_ids:
                    hypotheses.append(hyp)

    return {"hypotheses": hypotheses}