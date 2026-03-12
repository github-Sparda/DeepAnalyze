"""审计和遥测工具函数.

从原 graph.py 中提取的审计和遥测相关工具函数.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .json_utils import load_json_if_exists


def telemetry_context(node_name: str, state: dict[str, Any]) -> dict[str, Any]:
    """生成遥测上下文.

    Args:
        node_name: 节点名称
        state: 当前状态

    Returns:
        遥测上下文数据
    """
    return {
        "node": node_name,
        "timestamp": int(time.time()),
        "depth": state.get("depth", 0),
        "iteration": state.get("iteration_count", 0),
        "session_id": state.get("session_id", ""),
    }


def cleanup_dir_contents(dir_path: Path, keep_files: list[str] | None = None) -> int:
    """清理目录内容.

    Args:
        dir_path: 目录路径
        keep_files: 保留的文件列表

    Returns:
        删除的文件数量
    """
    if not dir_path.exists():
        return 0

    keep_set = set(keep_files or [])
    deleted = 0

    for item in dir_path.iterdir():
        if item.name in keep_set:
            continue

        try:
            if item.is_file():
                item.unlink()
                deleted += 1
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
                deleted += 1
        except Exception:
            pass

    return deleted


def rollback_plan_outputs(session_dir: Path, plan_ids: list[str]) -> dict[str, Any]:
    """回滚计划输出.

    Args:
        session_dir: 会话目录
        plan_ids: 计划ID列表

    Returns:
        回滚结果统计
    """
    result_dir = session_dir / "result"
    rolled_back: list[str] = []
    failed: list[str] = []

    for hid in plan_ids:
        # 查找相关的输出文件
        pattern = f"{hid}_*.json"
        for file_path in result_dir.glob(pattern):
            try:
                # 备份并删除
                backup_path = file_path.with_suffix(".json.bak")
                file_path.rename(backup_path)
                rolled_back.append(str(file_path.name))
            except Exception:
                failed.append(str(file_path.name))

    return {
        "rolled_back": rolled_back,
        "failed": failed,
        "count": len(rolled_back),
    }


def run_audit(session_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """运行审计.

    Args:
        session_dir: 会话目录
        state: 当前状态

    Returns:
        审计结果
    """
    audit_result: dict[str, Any] = {
        "timestamp": int(time.time()),
        "session_id": state.get("session_id", ""),
        "depth": state.get("depth", 0),
        "checks": {},
    }

    # 检查关键文件是否存在
    checks = {
        "plan_exists": (session_dir / "plan" / "analysis_plan.json").exists(),
        "results_exist": (session_dir / "result" / "hypothesis_results.json").exists(),
        "evidence_exists": (session_dir / "result" / "hypothesis_evidence.json").exists(),
        "report_exists": (session_dir / "report" / "report.md").exists(),
    }
    audit_result["checks"] = checks
    audit_result["all_passed"] = all(checks.values())

    return audit_result


def build_evidence_trace(
    session_dir: Path,
    hypothesis_id: str,
) -> dict[str, Any]:
    """构建证据追踪链.

    Args:
        session_dir: 会话目录
        hypothesis_id: 假设ID

    Returns:
        证据追踪链
    """
    result_dir = session_dir / "result"

    trace: dict[str, Any] = {
        "hypothesis_id": hypothesis_id,
        "artifacts": [],
        "dependencies": [],
    }

    # 收集相关产物
    patterns = [
        f"{hypothesis_id}_*.json",
        f"{hypothesis_id}_*.csv",
        f"{hypothesis_id}_*.png",
    ]

    for pattern in patterns:
        for file_path in result_dir.glob(pattern):
            trace["artifacts"].append({
                "name": file_path.name,
                "path": str(file_path.relative_to(session_dir)),
                "size": file_path.stat().st_size if file_path.exists() else 0,
            })

    # 加载证据包获取依赖关系
    evidence_path = result_dir / "hypothesis_evidence_pack.json"
    evidence_pack = load_json_if_exists(evidence_path)

    if isinstance(evidence_pack, dict) and "hypotheses" in evidence_pack:
        for hyp in evidence_pack.get("hypotheses", []):
            if isinstance(hyp, dict) and hyp.get("hypothesis_id") == hypothesis_id:
                trace["dependencies"] = hyp.get("dependencies", [])
                trace["evidence_sources"] = hyp.get("evidence_sources", [])
                break

    return trace


def build_reason_code_summary(session_dir: Path) -> dict[str, Any]:
    """构建原因代码摘要.

    Args:
        session_dir: 会话目录

    Returns:
        原因代码摘要
    """
    result_dir = session_dir / "result"

    # 加载门控报告
    gate_path = result_dir / "hypothesis_gate_report.json"
    gate_report = load_json_if_exists(gate_path)

    summary: dict[str, Any] = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "reason_codes": {},
    }

    if not isinstance(gate_report, dict):
        return summary

    hypotheses = gate_report.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return summary

    summary["total"] = len(hypotheses)

    for hyp in hypotheses:
        if not isinstance(hyp, dict):
            continue

        status = str(hyp.get("gate_status", "")).strip().lower()
        if status == "pass":
            summary["passed"] += 1
        else:
            summary["failed"] += 1

        reason = str(hyp.get("reason_code", "unknown")).strip()
        summary["reason_codes"][reason] = summary["reason_codes"].get(reason, 0) + 1

    return summary


def build_analysis_quality_score(session_dir: Path) -> dict[str, Any]:
    """构建分析质量评分.

    Args:
        session_dir: 会话目录

    Returns:
        质量评分
    """
    result_dir = session_dir / "result"

    scores: dict[str, float] = {}

    # 检查证据包质量
    evidence_path = result_dir / "hypothesis_evidence_pack.json"
    evidence_pack = load_json_if_exists(evidence_path)
    if isinstance(evidence_pack, dict):
        scores["evidence_completeness"] = evidence_pack.get("completeness_score", 0.0)

    # 检查门控报告质量
    gate_path = result_dir / "hypothesis_gate_report.json"
    gate_report = load_json_if_exists(gate_path)
    if isinstance(gate_report, dict):
        hypotheses = gate_report.get("hypotheses", [])
        if isinstance(hypotheses, list) and hypotheses:
            passed = sum(1 for h in hypotheses if isinstance(h, dict) and h.get("gate_status") == "pass")
            scores["gate_pass_rate"] = passed / len(hypotheses)

    # 检查多路径质量
    multipath_path = result_dir / "hypothesis_multipath.json"
    multipath = load_json_if_exists(multipath_path)
    if isinstance(multipath, dict):
        scores["multipath_consistency"] = multipath.get("consistency_score", 0.0)

    # 计算总体质量分
    if scores:
        overall = sum(scores.values()) / len(scores)
    else:
        overall = 0.0

    return {
        "overall": overall,
        "details": scores,
    }


def quality_consistency_errors(state: dict[str, Any]) -> list[str]:
    """检查质量一致性错误.

    Args:
        state: 当前状态

    Returns:
        错误列表
    """
    errors: list[str] = []

    if not isinstance(state, dict):
        return errors

    # 检查执行错误
    exec_errors = state.get("execution_errors", [])
    if isinstance(exec_errors, list) and exec_errors:
        errors.extend([f"execution: {e}" for e in exec_errors if isinstance(e, str)])

    # 检查重试耗尽
    if state.get("execution_retry_exhausted"):
        errors.append("execution_retry_exhausted")

    # 检查闭环失败
    closure_status = state.get("closure_status", {})
    if isinstance(closure_status, dict):
        for phase, status in closure_status.items():
            if isinstance(status, dict) and status.get("status") in ["failed", "recoverable_failed"]:
                errors.append(f"closure_failed: {phase}")

    return errors


def build_completion_validation(state: dict[str, Any]) -> dict[str, Any]:
    """构建完成态验证.

    Args:
        state: 当前状态

    Returns:
        完成态验证结果
    """
    if not isinstance(state, dict):
        return {"complete": False, "reason": "invalid_state"}

    # 检查必需字段
    required_fields = ["plan_json", "hypothesis_results", "hypothesis_evidence"]
    missing = [f for f in required_fields if not state.get(f)]

    if missing:
        return {
            "complete": False,
            "reason": f"missing_fields: {missing}",
        }

    # 检查质量一致性错误
    errors = quality_consistency_errors(state)
    if errors:
        return {
            "complete": False,
            "reason": "quality_errors",
            "errors": errors,
        }

    # 检查深度限制
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 1)
    if depth >= max_depth:
        return {
            "complete": True,
            "reason": "max_depth_reached",
        }

    return {
        "complete": True,
        "reason": "all_checks_passed",
    }
