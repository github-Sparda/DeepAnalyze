from __future__ import annotations

from typing import Any

ROLE_MAP: dict[str, str] = {
    "understand_files": "DataIngest",
    "data_quality": "DataQuality",
    "plan_visualizations": "Visualization",
    "plan_analysis": "Hypothesis",
    "parallel_generation": "CodeGen",
    "execution_guard": "RunGuard",
    "code_repair": "CodeRepair",
    "analyze_results": "Insights",
    "pipeline_guard": "RunGuard",
    "artifact_validator": "RunGuard",
    "generate_visualizations": "Visualization",
    "refine_hypotheses": "Hypothesis",
    "decide_recurse": "RunGuard",
    "advance_depth": "RunGuard",
    "report_outline": "ReportAssembly",
    "generate_report": "ReportAssembly",
    "finalize_run": "RunGuard",
}


def role_id_for_node(node_name: str) -> str:
    return ROLE_MAP.get(node_name, node_name)


def role_output_stub(role_id: str, output: dict[str, Any]) -> dict[str, Any]:
    return {
        "role_id": role_id,
        "output_keys": sorted(list(output.keys())),
    }
