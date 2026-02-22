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
