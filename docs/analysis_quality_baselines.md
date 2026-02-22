# Analysis Quality Baselines

## Session Set (Phase A)
- 全链路会话（差异/相关/模型/聚类）：`outputs/serum_orchestrated_fullcheck3/workspace/serum_1770862948`
- 部分缺失产物会话：`outputs/serum_orchestrated/workspace/serum_1770784762`
- 路径异常会话：`outputs/serum_orchestrated_fullcheck2/workspace/serum_1770862570`
- 双路径冲突会话：使用单测构造样本（`tests/test_analysis_closure_artifacts.py::test_multipath_status_partial_when_primary_failed`）
- 数据稀疏会话：使用单测构造样本（空/低覆盖 artifact 组合）

## Baseline Objectives
- 验证 `meta/analysis_quality_score.json` 可生成并包含四项指标。
- 验证 `meta/evidence_trace.json` 可追踪“假设 -> 指标 -> 来源”。
- 验证 `meta/reason_code_summary.json` 在 partial/failed/inconclusive 状态下产出恢复建议。

## Session Update (2026-02-22)
- 全流程验收会话：`outputs/serum_orchestrated_harden_check2/workspace/serum_1771732095`
- 关键结果：
  - `meta/hypothesis_set_consistency.json.satisfied = true`
  - `result/expected_artifact_validation.json` 非法项总数 = 0
  - `meta/analysis_quality_score.json`:
    - `quant_metric_ge_2_rate = 1.0`
    - `quantitative_coverage = 1.0`
    - `hypothesis_closure_rate = 1.0`
    - `conflict_explain_rate = 1.0`
  - `meta/quality_consistency_errors.json.valid = true`
- 报告结构验收：
  - 包含“研究目标与原始假设 / 假设验证与结果分析 / 跨假设综合讨论 / 结论与建议”
  - 假设节包含“阈值判定结果 + 规则类型 + 局限与下一步”

## Session Update (2026-02-22, Calibration)
- 全流程验收会话：`outputs/serum_orchestrated_calibration_check/workspace/serum_1771738347`
- Gate 验收：
  - `pass=1, partial=2, fail=0`（标准档位）
  - 规则类型覆盖：`significance_and_effect / predictive_performance / correlation_structure`
  - `calibration_context` 含冲突率触发信息（`high_conflict_adjustment=true`）
- 质量与一致性：
  - `meta/hypothesis_set_consistency.json.satisfied = true`
  - `meta/analysis_quality_score.json` 四项指标均为 `1.0`
  - `meta/report_substance_audit.json` 已生成（含 `basis/conflict/boundary/next_step` 覆盖率与缺口列表）
