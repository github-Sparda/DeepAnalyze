# Hardcoded Anti-Patterns Inventory

## Scope
- `src/core/orchestration`
- `src/core/reporting`
- `src/core/analytics/toolkit`

## Findings

1. Deterministic hypothesis template hardcoding
- Location: `src/core/orchestration/hypothesis_engine.py`
- Pattern: 固定 H1/H2/H3/H4 语义与步骤编排。
- Risk: 对非同类数据域泛化能力弱，可能产生不合理假设链。
- Proposed fix: 迁移到 intent/pipeline registry 驱动；按数据能力动态生成假设簇。

2. Method-family infer by keyword lists
- Location: `src/core/orchestration/graph.py` (`_infer_method_family`)
- Pattern: 通过少量中英关键词硬映射 method_family。
- Risk: 新领域词汇覆盖不足，路径分类偏差。
- Proposed fix: 引入方法词典 + pipeline metadata 推断优先，关键词仅兜底。

3. Group-column naming assumptions
- Location: `src/core/analytics/toolkit/model_train.py`, `model_eval.py`, `common.py`
- Pattern: 对 `group/label/target` 等列名存在先验依赖。
- Risk: 非标准数据集需人工重命名，自动流程鲁棒性下降。
- Proposed fix: 提供可配置分组列选择策略，支持 profile/用户配置优先。

4. Predictive completeness lexical checks
- Location: `src/core/reporting/assembler.py` (`_predictive_completeness_missing`)
- Pattern: 通过 step 名称关键词判断“是否使用模型”。
- Risk: 自定义模型步骤命名下误判。
- Proposed fix: 统一使用 `ml_repro_bundle` + model metadata 作为主依据。

5. Coverage/filter defaults
- Location: `src/core/orchestration/hypothesis_engine.py`
- Pattern: 默认 Top-K/筛选模式内嵌在代码。
- Risk: 任务差异场景下解释偏差。
- Proposed fix: 迁移到配置层并在报告中显式回填。

## Status
- 本轮已部分缓解：
  - 报告侧 predictive completeness 已接入 `ml_repro_bundle`。
  - 计划缺失时改为 execution/profile 的通用 deterministic fallback。
- 本轮新增完成：
  - 假设标题/默认语义迁移到 `hypothesis_profile_registry.json`（可覆盖）。
  - group column / label mapping 迁移到 `analysis_runtime.json`（可覆盖）。
  - gate 高冲突阈值调整与 run_audit 结果产物要求支持运行时配置。
- 仍待后续深入：
  - 进一步削减以 H1/H2/H3/H4 顺序推断业务语义的残留逻辑。
  - 将更多 artifact 期待与恢复动作从代码常量迁移到统一 registry。
