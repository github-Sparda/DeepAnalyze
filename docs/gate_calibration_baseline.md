# Gate Calibration Baseline

## Session
- baseline: `outputs/serum_orchestrated_harden_check2/workspace/serum_1771732095`

## Snapshot
- gate_status_counts: {'pass': 0, 'partial': 3, 'fail': 0}
- gate_rule_types: ['correlation_structure', 'predictive_performance', 'significance_and_effect']
- quality_score: {'quant_metric_ge_2_rate': 1.0, 'quantitative_coverage': 1.0, 'hypothesis_closure_rate': 1.0, 'conflict_explain_rate': 1.0}

## Failed Check Distribution
- corr_edge_ge_1: 1
- has_corr_edge_support: 1
- has_effect_metric: 1
- path_consistency: 1
- primary_performance_ge_0_6: 1

## Candidate Calibration Paths
- 若 `secondary_performance_ge_min` 高频失败，可按场景切换 `exploratory` 档进行探索性判定，并在报告中强制标注“探索级结论”。
- 若 `corr_edge_ge_min` 高频失败，可引入稀疏网络或放宽边阈值作为第三路径（不替代一致性约束）。
- 若显著性指标达标但 effect 证据不足，优先补效应量与置信区间产物。


## Conclusion Density (Per Hypothesis)
| Hypothesis | Numeric Sentences | Total Sentences | Density |
|---|---:|---:|---:|
