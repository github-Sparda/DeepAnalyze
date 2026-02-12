# Report Assembly Gap Matrix

## Baseline Sessions
- 完整成功会话：`outputs/serum_orchestrated_fullcheck3/workspace/serum_1770862948`
- 部分缺失产物会话：`outputs/serum_orchestrated/workspace/serum_1770784762`
- 路径异常会话：`outputs/serum_orchestrated_fullcheck2/workspace/serum_1770862570`

## Gap Matrix
| 问题 | 根因 | 修复策略 | 验收标准 |
|---|---|---|---|
| 图表/iframe 偶发不显示 | 路径绝对化、非法 scheme、缺失文件未降级 | 增加路径健康检查；渲染失败输出 warning；写入 `meta/render_manifest.json` | 报告中失败资源有原因说明；`render_manifest.json` 可追踪 |
| 正文有“空泛分析” | 解释段未强制引用定量指标 | 增加 quant 缺失降级与分析来源标签；LLM 输出增加定量 grounding 检查 | 假设节缺 quant 时自动 `inconclusive`；解释段包含指标名/数值 |
| 大纲污染正文 | outline 被直接当结果 | 引入 `outline_mode`，默认 `structure_only`；冲突输出注记 | 默认不再引用 outline 原文；冲突时有“冲突注记” |
| 图表重复展示 | 正文和附件重复渲染 | 正文记录 `used_visuals`，附件仅显示未使用资源 | 同一图不在正文/附件重复两次 |
| 附件不可读 | 多格式缺少预览能力 | 附件统一预览：txt/md/json/csv/html/pdf；pdf 增加 fallback link | 五类附件可预览或可打开原文件 |
| 假设对照不完整 | 缺少 A/B 对照与冲突说明 | 假设节固定输出路径对照表与一致性解释 | 每个假设都有 A/B 状态、冲突原因与结论等级 |

## Current Validation Snapshot
- 模块测试：
  - `tests/test_analysis_closure_artifacts.py`
  - `tests/test_report_assembler_visuals.py`
- 状态：通过（含 A/B 对照渲染、pdf 预览 fallback、路径异常降级、outline 冲突保护）。
