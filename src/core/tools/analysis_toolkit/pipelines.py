from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineStep:
    name: str
    method: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineVariant:
    variant_id: str
    description: str
    steps: list[PipelineStep]
    compatible_visuals: list[str] = field(default_factory=list)


@dataclass
class PipelineSpec:
    pipeline_id: str
    description: str
    variants: list[PipelineVariant]


def pipeline_registry() -> dict[str, PipelineSpec]:
    return {
        "key_feature_screening": PipelineSpec(
            pipeline_id="key_feature_screening",
            description="筛选关键特征并给出统计依据",
            variants=[
                PipelineVariant(
                    variant_id="t_test_volcano",
                    description="两组差异检验 + 火山图",
                    steps=[
                        PipelineStep("stats_tests", "t_test"),
                        PipelineStep("multiple_testing", "bh_fdr"),
                        PipelineStep("feature_selection", "variance"),
                        PipelineStep("viz_manhattan_volcano", "volcano"),
                    ],
                    compatible_visuals=["volcano"],
                ),
                PipelineVariant(
                    variant_id="anova_manhattan",
                    description="多组差异检验 + 曼哈顿图",
                    steps=[
                        PipelineStep("stats_tests", "anova"),
                        PipelineStep("multiple_testing", "bh_fdr"),
                        PipelineStep("feature_selection", "effect_size"),
                        PipelineStep("viz_manhattan_volcano", "manhattan"),
                    ],
                    compatible_visuals=["manhattan"],
                ),
            ],
        ),
        "correlation_exploration": PipelineSpec(
            pipeline_id="correlation_exploration",
            description="相关性结构与网络可视化",
            variants=[
                PipelineVariant(
                    variant_id="corr_heatmap",
                    description="相关矩阵 + 热图",
                    steps=[
                        PipelineStep("correlation", "pearson"),
                        PipelineStep("viz_heatmap_cluster", "heatmap"),
                    ],
                    compatible_visuals=["heatmap"],
                ),
                PipelineVariant(
                    variant_id="corr_network",
                    description="相关矩阵 + 网络图",
                    steps=[
                        PipelineStep("correlation", "spearman"),
                        PipelineStep("viz_network", "network"),
                    ],
                    compatible_visuals=["network"],
                ),
            ],
        ),
    }


def list_pipelines() -> list[str]:
    return list(pipeline_registry().keys())
