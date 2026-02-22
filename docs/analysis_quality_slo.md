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

## Gate Policy
- 若 `quant_metric_ge_2_rate < 0.5` 或 `hypothesis_closure_rate < 1.0`，报告结论默认降级为“需复核”。
