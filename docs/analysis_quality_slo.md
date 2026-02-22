# Analysis Quality SLO

## SLO Targets
- 每假设至少 2 个定量指标引用（`quant_metric_ge_2_rate` 目标 >= 0.8，最终目标 1.0）。
- 每假设至少 1 条显著性证据 + 1 条效应量证据（场景不满足时必须降级并说明原因）。
- 假设闭环率（定义→方法→执行→结果→结论→后续）目标 = 1.0。
- `inconclusive/failed` 必须包含 `reason_code` 与 `recovery_action`（目标 = 1.0）。
- 空泛句率（`fluff_sentence_rate`）目标 < 0.2。

## Measurement Source
- `meta/analysis_quality_score.json`
- `meta/reason_code_summary.json`
- `meta/evidence_trace.json`
- `meta/report_substance_audit.json`

## Gate Policy
- 若 `quant_metric_ge_2_rate < 0.5` 或 `hypothesis_closure_rate < 1.0`，报告结论默认降级为“需复核”。
- 若 `meta/hypothesis_set_consistency.json.satisfied=false`，禁止输出最终结论章节。
- 若 gate 为 `partial/fail`，必须携带 `reason_code + recovery_action`。

## Report Substance Audit (新增口径)
- `basis_coverage`: 假设节包含“依据：”段的覆盖率。
- `conflict_coverage`: 假设节包含“反证/冲突：”段的覆盖率。
- `boundary_coverage`: 假设节包含“边界：”段的覆盖率。
- `next_step_coverage`: 假设节包含“下一步：”段的覆盖率。
- `missing_elements_by_hypothesis`: 每个假设缺失的结构化要素列表。

## Gate Rule Typing
- `significance_and_effect`：显著性 + 效应量双证据。
- `predictive_performance`：主性能 + 交叉验证性能。
- `correlation_structure`：相关强度 + 边支撑证据。
- `embedding_structure`：聚类/嵌入结构证据。
- `generic_evidence`：通用定量证据兜底。

## Calibration Profiles
- `strict`: 生产级门槛，优先减少假阳性结论。
- `standard`: 默认门槛，平衡覆盖率与稳定性。
- `exploratory`: 探索级门槛，仅用于先导分析，报告中必须标注“探索级结论”。
