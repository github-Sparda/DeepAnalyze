from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .pipelines import pipeline_registry, PipelineSpec, PipelineVariant


@dataclass
class ScoredVariant:
    pipeline_id: str
    variant: PipelineVariant
    score: float
    reason: str


def _has_time_columns(columns: list[str]) -> bool:
    lowered = [c.lower() for c in columns]
    return any("time" in c or "date" in c for c in lowered)


def _has_group_columns(columns: list[str]) -> bool:
    lowered = [c.lower() for c in columns]
    return any(c in {"group", "label", "class", "target"} for c in lowered)


def _has_latlon(columns: list[str]) -> bool:
    lowered = [c.lower() for c in columns]
    has_lat = "lat" in lowered or "latitude" in lowered
    has_lon = "lon" in lowered or "longitude" in lowered
    return has_lat and has_lon


def _has_label(columns: list[str]) -> bool:
    lowered = [c.lower() for c in columns]
    return any(c in {"label", "target", "y"} for c in lowered)


def _has_batch(columns: list[str]) -> bool:
    lowered = [c.lower() for c in columns]
    return any("batch" in c for c in lowered)


def _has_event(columns: list[str]) -> bool:
    lowered = [c.lower() for c in columns]
    return any("event" in c or "status" in c for c in lowered)


def _input_capabilities(data_profile: dict[str, Any]) -> set[str]:
    columns = data_profile.get("column_names", []) if isinstance(data_profile, dict) else []
    caps = set()
    if data_profile.get("numeric_columns"):
        caps.add("numeric_columns")
    if _has_group_columns(columns):
        caps.add("group_column")
        caps.add("label_column")
    if _has_time_columns(columns):
        caps.add("time_column")
    if _has_latlon(columns):
        caps.add("lat_lon")
    if _has_batch(columns):
        caps.add("batch_column")
    if _has_event(columns):
        caps.add("event_column")
    if any(str(c).lower() in {"treatment", "treat", "arm"} for c in columns):
        caps.add("treatment_column")
    return caps


def shortlist_pipelines(data_profile: dict[str, Any], goals: list[str] | None = None) -> list[PipelineSpec]:
    goals = [g.lower() for g in (goals or [])]
    columns = data_profile.get("column_names", []) if isinstance(data_profile, dict) else []
    numeric_cols = data_profile.get("numeric_columns", []) if isinstance(data_profile, dict) else []
    selected: list[PipelineSpec] = []
    registry = pipeline_registry()

    if numeric_cols:
        selected.extend(
            [
                registry["key_feature_screening"],
                registry["correlation_exploration"],
                registry["robust_uncertainty"],
            ]
        )
    if _has_group_columns(columns):
        selected.extend([registry["differential_testing"], registry["subgroup_analysis"]])
    if _has_time_columns(columns):
        selected.append(registry["time_series"])
        if _has_event(columns):
            selected.append(registry["survival_analysis"])
    if _has_latlon(columns):
        selected.append(registry["geospatial"])
    if _has_batch(columns):
        selected.append(registry["batch_effect"])
    if _has_label(columns):
        selected.append(registry["model_evaluation"])
    if any("cluster" in g or "segment" in g for g in goals):
        selected.append(registry["clustering_dimensionality"])
    if any("causal" in g or "treatment" in g for g in goals):
        selected.append(registry["causal_inference"])

    seen = set()
    unique: list[PipelineSpec] = []
    for spec in selected:
        if spec.pipeline_id in seen:
            continue
        seen.add(spec.pipeline_id)
        unique.append(spec)
    return unique


def _score_variant(caps: set[str], variant: PipelineVariant) -> tuple[float, str]:
    score = 0.0
    reasons = []
    if variant.required_inputs:
        missing = [req for req in variant.required_inputs if req not in caps]
        if missing:
            return -1.0, f"missing inputs: {','.join(missing)}"
        score += 2.0
        reasons.append("inputs_ok")
    if variant.compatible_visuals:
        score += 0.5
        reasons.append("visuals_ok")
    if variant.required_artifacts:
        score += 0.5
        reasons.append("artifacts_ok")
    return score, ";".join(reasons)


def score_variants(data_profile: dict[str, Any], goals: list[str] | None = None) -> list[ScoredVariant]:
    caps = _input_capabilities(data_profile)
    scored: list[ScoredVariant] = []
    for pipeline in shortlist_pipelines(data_profile, goals):
        for variant in pipeline.variants:
            score, reason = _score_variant(caps, variant)
            if score >= 0:
                scored.append(ScoredVariant(pipeline.pipeline_id, variant, score, reason))
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def select_pipeline_variants(data_profile: dict[str, Any], goals: list[str] | None = None, top_k: int = 4) -> list[ScoredVariant]:
    scored = score_variants(data_profile, goals)
    return scored[:top_k]
