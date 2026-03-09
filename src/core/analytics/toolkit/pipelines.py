from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
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
    required_inputs: list[str] = field(default_factory=list)
    compatible_visuals: list[str] = field(default_factory=list)
    blocked_visuals: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)
    artifact_aliases: dict[str, list[str]] = field(default_factory=dict)
    capability_tags: list[str] = field(default_factory=list)
    equivalence_rules: list[str] = field(default_factory=list)
    fallback_variant: str | None = None


@dataclass
class PipelineSpec:
    pipeline_id: str
    description: str
    variants: list[PipelineVariant]


def _load_promoted_variants() -> list[PipelineVariant]:
    path = Path(__file__).with_name("promoted_lines.json")
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    variants: list[PipelineVariant] = []
    for line in payload:
        if not isinstance(line, dict):
            continue
        line_id = line.get("line_id") or line.get("id")
        steps = []
        for step in line.get("steps", []):
            if not isinstance(step, dict):
                continue
            name = step.get("name")
            method = step.get("method") or "default"
            params = step.get("params") or {}
            if name:
                steps.append(PipelineStep(name, method, params))
        if not line_id or not steps:
            continue
        variants.append(
            PipelineVariant(
                variant_id=str(line_id),
                description=str(line.get("description", "Promoted custom line")),
                steps=steps,
                required_inputs=list(line.get("required_inputs", [])),
                compatible_visuals=list(line.get("compatible_visuals", [])),
                required_artifacts=list(line.get("required_artifacts", [])),
                quality_gates=list(line.get("quality_gates", [])),
                artifact_aliases={
                    str(key): [str(item) for item in value]
                    for key, value in (line.get("artifact_aliases", {}) or {}).items()
                    if str(key)
                    and isinstance(value, list)
                },
                capability_tags=list(line.get("capability_tags", [])),
                equivalence_rules=list(line.get("equivalence_rules", [])),
                fallback_variant=None,
            )
        )
    return variants


def pipeline_registry() -> dict[str, PipelineSpec]:
    registry = {
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
                    required_inputs=["group_column"],
                    compatible_visuals=["volcano"],
                    required_artifacts=["stats_results.json", "feature_selection.json", "volcano_plot.png"],
                    quality_gates=["result:stats_results.json", "result:feature_selection.json", "plots:volcano_plot.png"],
                    artifact_aliases={"volcano_plot.png": ["manhattan_plot.png"]},
                    capability_tags=["differential_evidence", "visual_differential"],
                    equivalence_rules=["allow_capability_equivalence"],
                    fallback_variant="u_test_volcano",
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
                    required_inputs=["group_column"],
                    compatible_visuals=["manhattan"],
                    required_artifacts=["stats_results.json", "manhattan_plot.png"],
                    quality_gates=["result:stats_results.json", "plots:manhattan_plot.png"],
                    artifact_aliases={"manhattan_plot.png": ["volcano_plot.png"]},
                    capability_tags=["differential_evidence", "visual_differential"],
                    equivalence_rules=["allow_capability_equivalence"],
                ),
                PipelineVariant(
                    variant_id="u_test_volcano",
                    description="U-test + BH + rank selection + 火山图",
                    steps=[
                        PipelineStep("stats_tests", "u_test"),
                        PipelineStep("multiple_testing", "bh_fdr"),
                        PipelineStep("feature_selection", "rank"),
                        PipelineStep("viz_manhattan_volcano", "volcano"),
                    ],
                    required_inputs=["group_column"],
                    compatible_visuals=["volcano"],
                    required_artifacts=["stats_results.json", "volcano_plot.png"],
                    quality_gates=["result:stats_results.json", "plots:volcano_plot.png"],
                    artifact_aliases={"volcano_plot.png": ["manhattan_plot.png"]},
                    capability_tags=["differential_evidence", "visual_differential"],
                    equivalence_rules=["allow_capability_equivalence"],
                ),
                PipelineVariant(
                    variant_id="effect_size_heatmap",
                    description="效应量筛选 + 相关性过滤 + 热力图聚类树",
                    steps=[
                        PipelineStep("feature_selection", "effect_size"),
                        PipelineStep("correlation", "pearson"),
                        PipelineStep("viz_heatmap_cluster", "heatmap_cluster"),
                    ],
                    required_inputs=["numeric_columns"],
                    compatible_visuals=["heatmap_cluster"],
                    required_artifacts=["feature_selection.json", "correlation.json", "heatmap_cluster.png"],
                    quality_gates=["result:feature_selection.json", "result:correlation.json", "plots:heatmap_cluster.png"],
                    artifact_aliases={"heatmap_cluster.png": ["heatmap.png", "cluster.png"]},
                    capability_tags=["correlation_structure", "visual_cluster_heatmap"],
                    equivalence_rules=["allow_capability_equivalence"],
                ),
            ],
        ),
        "differential_testing": PipelineSpec(
            pipeline_id="differential_testing",
            description="差异检验与显著性评估",
            variants=[
                PipelineVariant(
                    variant_id="t_test_box",
                    description="t-test + BH + 箱线图",
                    steps=[
                        PipelineStep("stats_tests", "t_test"),
                        PipelineStep("multiple_testing", "bh_fdr"),
                        PipelineStep("viz_comparison", "box"),
                    ],
                    required_inputs=["group_column"],
                    compatible_visuals=["box"],
                    required_artifacts=["stats_results.json"],
                    quality_gates=["result:stats_results.json"],
                ),
                PipelineVariant(
                    variant_id="u_test_violin",
                    description="U-test + BH + 小提琴图",
                    steps=[
                        PipelineStep("stats_tests", "u_test"),
                        PipelineStep("multiple_testing", "bh_fdr"),
                        PipelineStep("viz_comparison", "violin"),
                    ],
                    required_inputs=["group_column"],
                    compatible_visuals=["violin"],
                    required_artifacts=["stats_results.json"],
                    quality_gates=["result:stats_results.json"],
                ),
                PipelineVariant(
                    variant_id="anova_posthoc",
                    description="ANOVA + posthoc + 条形图",
                    steps=[
                        PipelineStep("stats_tests", "anova"),
                        PipelineStep("viz_comparison", "bar"),
                    ],
                    required_inputs=["group_column"],
                    compatible_visuals=["bar"],
                    required_artifacts=["stats_results.json"],
                    quality_gates=["result:stats_results.json"],
                ),
                PipelineVariant(
                    variant_id="chi_square",
                    description="卡方检验 + stacked_bar",
                    steps=[
                        PipelineStep("stats_tests", "chi_square"),
                        PipelineStep("viz_comparison", "bar"),
                    ],
                    required_inputs=["group_column"],
                    required_artifacts=["stats_results.json"],
                    quality_gates=["result:stats_results.json"],
                ),
            ],
        ),
        "correlation_exploration": PipelineSpec(
            pipeline_id="correlation_exploration",
            description="相关性结构探索",
            variants=[
                PipelineVariant(
                    variant_id="corr_heatmap",
                    description="Pearson + 热图",
                    steps=[
                        PipelineStep("correlation", "pearson"),
                        PipelineStep("viz_heatmap_cluster", "heatmap"),
                    ],
                    compatible_visuals=["heatmap"],
                    required_artifacts=["correlation.json", "heatmap.png"],
                    quality_gates=["result:correlation.json", "plots:heatmap.png"],
                ),
                PipelineVariant(
                    variant_id="corr_network",
                    description="Spearman + 网络图",
                    steps=[
                        PipelineStep("correlation", "spearman"),
                        PipelineStep("viz_network", "network"),
                    ],
                    compatible_visuals=["network"],
                    required_artifacts=["correlation.json", "network.png"],
                    quality_gates=["result:correlation.json", "plots:network.png"],
                ),
                PipelineVariant(
                    variant_id="corr_cluster",
                    description="相关矩阵 + 聚类树",
                    steps=[
                        PipelineStep("correlation", "pearson"),
                        PipelineStep("viz_heatmap_cluster", "cluster"),
                    ],
                    compatible_visuals=["heatmap_cluster"],
                    required_artifacts=["correlation.json", "cluster.png"],
                    quality_gates=["result:correlation.json", "plots:cluster.png"],
                    artifact_aliases={"cluster.png": ["clustermap.png", "heatmap_cluster.png"]},
                    capability_tags=["correlation_structure", "visual_cluster_heatmap"],
                    equivalence_rules=["allow_capability_equivalence"],
                ),
            ],
        ),
        "robust_uncertainty": PipelineSpec(
            pipeline_id="robust_uncertainty",
            description="稳健统计与不确定性",
            variants=[
                PipelineVariant(
                    variant_id="robust_bootstrap",
                    description="稳健统计 + bootstrap",
                    steps=[
                        PipelineStep("robust_stats", "mad"),
                        PipelineStep("bootstrap", "mean_ci"),
                    ],
                    compatible_visuals=["errorbar"],
                    required_artifacts=["robust_stats.json", "bootstrap.json"],
                    quality_gates=["result:robust_stats.json", "result:bootstrap.json"],
                ),
                PipelineVariant(
                    variant_id="robust_monte_carlo",
                    description="稳健统计 + Monte Carlo",
                    steps=[
                        PipelineStep("robust_stats", "mad"),
                        PipelineStep("monte_carlo", "normal_sim"),
                    ],
                    compatible_visuals=["density"],
                    required_artifacts=["robust_stats.json", "monte_carlo.json"],
                    quality_gates=["result:robust_stats.json", "result:monte_carlo.json"],
                ),
            ],
        ),
        "subgroup_analysis": PipelineSpec(
            pipeline_id="subgroup_analysis",
            description="亚组分析",
            variants=[
                PipelineVariant(
                    variant_id="subgroup_means",
                    description="亚组均值 + 对比图",
                    steps=[
                        PipelineStep("subgroup_analysis", "means"),
                        PipelineStep("viz_comparison", "box"),
                    ],
                    required_inputs=["group_column"],
                    compatible_visuals=["box"],
                    required_artifacts=["subgroup_analysis.json"],
                    quality_gates=["result:subgroup_analysis.json"],
                ),
                PipelineVariant(
                    variant_id="subgroup_trend",
                    description="亚组趋势 + 分面网格",
                    steps=[
                        PipelineStep("subgroup_analysis", "trend"),
                        PipelineStep("viz_facet_grid", "facet"),
                    ],
                    required_inputs=["group_column"],
                    compatible_visuals=["facet"],
                    required_artifacts=["subgroup_analysis.json"],
                    quality_gates=["result:subgroup_analysis.json"],
                ),
            ],
        ),
        "clustering_dimensionality": PipelineSpec(
            pipeline_id="clustering_dimensionality",
            description="聚类与降维",
            variants=[
                PipelineVariant(
                    variant_id="pca_kmeans",
                    description="PCA + KMeans + scatter",
                    steps=[
                        PipelineStep("dimensionality", "pca"),
                        PipelineStep("clustering", "kmeans"),
                        PipelineStep("viz_multivariate", "scatter"),
                    ],
                    compatible_visuals=["scatter"],
                    required_artifacts=["clustering.json"],
                ),
                PipelineVariant(
                    variant_id="umap_hdbscan",
                    description="UMAP + HDBSCAN + scatter",
                    steps=[
                        PipelineStep("dimensionality", "umap"),
                        PipelineStep("clustering", "hdbscan"),
                        PipelineStep("viz_multivariate", "scatter"),
                    ],
                    compatible_visuals=["scatter"],
                    required_artifacts=["clustering.json"],
                ),
                PipelineVariant(
                    variant_id="tsne_hier",
                    description="tSNE + hierarchical + scatter",
                    steps=[
                        PipelineStep("dimensionality", "tsne"),
                        PipelineStep("clustering", "hierarchical"),
                        PipelineStep("viz_multivariate", "scatter"),
                    ],
                    compatible_visuals=["scatter"],
                    required_artifacts=["clustering.json"],
                ),
            ],
        ),
        "anomaly_detection": PipelineSpec(
            pipeline_id="anomaly_detection",
            description="异常检测",
            variants=[
                PipelineVariant(
                    variant_id="iqr_distribution",
                    description="IQR + 分布图",
                    steps=[
                        PipelineStep("outlier_detection", "iqr"),
                        PipelineStep("viz_gallery", "distribution"),
                    ],
                    compatible_visuals=["distribution"],
                    required_artifacts=["outlier_detection.json"],
                    quality_gates=["result:outlier_detection.json"],
                ),
                PipelineVariant(
                    variant_id="zscore_hist",
                    description="zscore + 直方图",
                    steps=[
                        PipelineStep("outlier_detection", "zscore"),
                        PipelineStep("viz_gallery", "hist"),
                    ],
                    required_artifacts=["outlier_detection.json"],
                    quality_gates=["result:outlier_detection.json"],
                ),
            ],
        ),
        "time_series": PipelineSpec(
            pipeline_id="time_series",
            description="时间序列分析",
            variants=[
                PipelineVariant(
                    variant_id="trend_seasonality",
                    description="趋势/季节性 + 轨迹图",
                    steps=[
                        PipelineStep("time_series", "decompose"),
                        PipelineStep("viz_longitudinal", "line"),
                    ],
                    required_inputs=["time_column"],
                    compatible_visuals=["line"],
                    required_artifacts=["time_series.json"],
                ),
                PipelineVariant(
                    variant_id="arima_residual",
                    description="ARIMA baseline + 残差诊断",
                    steps=[
                        PipelineStep("time_series", "arima"),
                        PipelineStep("viz_stat_diagnostic", "residual"),
                    ],
                    required_inputs=["time_column"],
                    compatible_visuals=["residual"],
                    required_artifacts=["time_series.json"],
                ),
            ],
        ),
        "causal_inference": PipelineSpec(
            pipeline_id="causal_inference",
            description="因果推断",
            variants=[
                PipelineVariant(
                    variant_id="psm_ate",
                    description="倾向评分匹配 + ATE",
                    steps=[
                        PipelineStep("causal_inference", "psm"),
                        PipelineStep("viz_comparison", "bar"),
                    ],
                    required_inputs=["treatment_column"],
                    compatible_visuals=["bar"],
                    required_artifacts=["causal_inference.json"],
                ),
                PipelineVariant(
                    variant_id="ipw_sensitivity",
                    description="IPW + 敏感性分析",
                    steps=[
                        PipelineStep("causal_inference", "ipw"),
                        PipelineStep("viz_stat_diagnostic", "tornado"),
                    ],
                    required_inputs=["treatment_column"],
                    required_artifacts=["causal_inference.json"],
                ),
            ],
        ),
        "batch_effect": PipelineSpec(
            pipeline_id="batch_effect",
            description="批次效应检测与校正",
            variants=[
                PipelineVariant(
                    variant_id="batch_pca",
                    description="批次效应检测 + PCA 对比",
                    steps=[
                        PipelineStep("batch_effect", "detect"),
                        PipelineStep("viz_multivariate", "scatter"),
                    ],
                    required_inputs=["batch_column"],
                    required_artifacts=["batch_effect.json"],
                ),
                PipelineVariant(
                    variant_id="batch_heatmap",
                    description="批次校正 + 热力对比",
                    steps=[
                        PipelineStep("batch_effect", "correct"),
                        PipelineStep("viz_heatmap_cluster", "heatmap"),
                    ],
                    required_inputs=["batch_column"],
                    required_artifacts=["batch_effect.json"],
                ),
            ],
        ),
        "survival_analysis": PipelineSpec(
            pipeline_id="survival_analysis",
            description="生存分析",
            variants=[
                PipelineVariant(
                    variant_id="km_logrank",
                    description="KM + log-rank + 曲线",
                    steps=[
                        PipelineStep("survival_analysis", "km"),
                        PipelineStep("viz_longitudinal", "line"),
                    ],
                    required_inputs=["time_column", "event_column"],
                    required_artifacts=["survival_analysis.json"],
                ),
                PipelineVariant(
                    variant_id="cox_forest",
                    description="Cox 回归 + 风险比表",
                    steps=[
                        PipelineStep("survival_analysis", "cox"),
                        PipelineStep("viz_stat_diagnostic", "forest"),
                    ],
                    required_inputs=["time_column", "event_column"],
                    required_artifacts=["survival_analysis.json"],
                ),
            ],
        ),
        "model_evaluation": PipelineSpec(
            pipeline_id="model_evaluation",
            description="模型评估与可解释性",
            variants=[
                PipelineVariant(
                    variant_id="logistic_roc",
                    description="logistic + ROC/PR + calibration",
                    steps=[
                        PipelineStep("model_train", "logistic"),
                        PipelineStep("model_eval", "roc_pr"),
                    ],
                    required_inputs=["label_column"],
                    required_artifacts=[
                        "model_results.json",
                        "model_eval.json",
                        "model_performance_comparison.csv",
                        "roc_curve.png",
                        "pr_curve.png",
                    ],
                    quality_gates=[
                        "result:model_results.json",
                        "result:model_eval.json",
                        "result:model_performance_comparison.csv",
                        "plots:roc_curve.png",
                        "plots:pr_curve.png",
                    ],
                ),
                PipelineVariant(
                    variant_id="rf_importance",
                    description="random_forest + 特征重要性",
                    steps=[
                        PipelineStep("model_train", "random_forest"),
                        PipelineStep("model_eval", "importance"),
                    ],
                    required_inputs=["label_column"],
                    required_artifacts=[
                        "model_results.json",
                        "model_eval.json",
                        "feature_importance.json",
                        "feature_importance_plot.png",
                    ],
                    quality_gates=[
                        "result:model_results.json",
                        "result:model_eval.json",
                        "result:feature_importance.json",
                        "plots:feature_importance_plot.png",
                    ],
                ),
            ],
        ),
        "geospatial": PipelineSpec(
            pipeline_id="geospatial",
            description="地理可视化",
            variants=[
                PipelineVariant(
                    variant_id="geo_heatmap",
                    description="地理热力图",
                    steps=[PipelineStep("viz_geospatial", "heatmap")],
                    required_inputs=["lat_lon"],
                    compatible_visuals=["geo_heatmap"],
                )
            ],
        ),
        "distribution_fit": PipelineSpec(
            pipeline_id="distribution_fit",
            description="分布拟合与正态性",
            variants=[
                PipelineVariant(
                    variant_id="qq_hist",
                    description="分布拟合 + QQ + 直方图",
                    steps=[
                        PipelineStep("robust_stats", "distribution"),
                        PipelineStep("viz_stat_diagnostic", "qq"),
                        PipelineStep("viz_gallery", "hist"),
                    ],
                    required_artifacts=["robust_stats.json"],
                ),
                PipelineVariant(
                    variant_id="normality_density",
                    description="正态性检验 + 密度图",
                    steps=[
                        PipelineStep("robust_stats", "normality"),
                        PipelineStep("viz_gallery", "density"),
                    ],
                    required_artifacts=["robust_stats.json"],
                ),
            ],
        ),
    }
    promoted_variants = _load_promoted_variants()
    if promoted_variants:
        registry["promoted_custom_lines"] = PipelineSpec(
            pipeline_id="promoted_custom_lines",
            description="人工确认后的自增长执行线",
            variants=promoted_variants,
        )
    return registry


def list_pipelines() -> list[str]:
    return list(pipeline_registry().keys())
