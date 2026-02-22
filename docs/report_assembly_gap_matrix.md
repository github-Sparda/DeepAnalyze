# Report Assembly Gap Matrix

## Baseline Sessions
- 固定基线会话：`outputs/serum_orchestrated/workspace/serum_1771725360`
- 对照会话（历史渲染失败）：`outputs/serum_orchestrated_fullcheck3/workspace/serum_1770862948`
- 对照会话（路径异常）：`outputs/serum_orchestrated_fullcheck2/workspace/serum_1770862570`

## Gap Matrix
| 问题 | 根因 | 修复策略 | 验收标准 |
|---|---|---|---|
| 图表/iframe 偶发不显示 | 路径绝对化、非法 scheme、缺失文件未降级 | 增加路径健康检查；渲染失败输出 warning；写入 `meta/render_manifest.json` | 报告中失败资源有原因说明；`render_manifest.json` 可追踪 |
| 正文有“空泛分析” | 解释段未强制引用定量指标 | 增加 quant 缺失降级与分析来源标签；LLM 输出增加定量 grounding 检查 | 假设节缺 quant 时自动 `inconclusive`；解释段包含指标名/数值 |
| 大纲污染正文 | outline 被直接当结果 | 引入 `outline_mode`，默认 `structure_only`；冲突输出注记 | 默认不再引用 outline 原文；冲突时有“冲突注记” |
| 图表重复展示 | 正文和附件重复渲染 | 正文记录 `used_visuals`，附件仅显示未使用资源 | 同一图不在正文/附件重复两次 |
| 附件不可读 | 多格式缺少预览能力 | 附件统一预览：txt/md/json/csv/html/pdf；pdf 增加 fallback link | 五类附件可预览或可打开原文件 |
| 假设对照不完整 | 缺少 A/B 对照与冲突说明 | 假设节固定输出路径对照表与一致性解释 | 每个假设都有 A/B 状态、冲突原因与结论等级 |

## Repro Checklist (基线会话)
| 异常 | 复现命令 | 证据文件 | 期望行为 | 当前行为（修复前） |
|---|---|---|---|---|
| 假设错位 | `python scripts/reassemble_report.py --session outputs/serum_orchestrated/workspace/serum_1771725360` | `plan/analysis_plan.json` vs `result/hypothesis_gate_report.json` | H1..Hn 在 plan/evidence/gate/report 一致 | report 中出现顺序错位/缺失 |
| artifact 文本污染 | 同上 | `result/expected_artifact_validation.json` | expected_artifacts 仅路径字符串 | 混入自然语言句子 |
| 标签异常建模 | `pytest -q tests/test_analysis_toolkit_modeling.py` | `result/label_health_report.json` | 非法标签直接跳过建模并给原因 | 可能误触发建模 |
| 评分异常 | `pytest -q tests/test_analysis_closure_artifacts.py` | `meta/analysis_quality_score.json` | 评分与 evidence_pack 口径一致 | 旧版 list/dict 混算不一致 |
| 渲染退化 | `pytest -q tests/test_report_assembler_visuals.py` | `meta/render_manifest.json` | 失败资源可解释、附件有 fallback | file:// 模式下空白预览 |

## Problem-to-Module Mapping
| 模块域 | 责任文件 | 典型问题 |
|---|---|---|
| Planning parser | `src/core/orchestration/graph.py` | 假设标题误识别、schema 缺失字段、路径类型非法 |
| Multipath/evidence/gate | `src/core/orchestration/hypothesis_engine.py`, `src/core/analytics/resources/dictionaries.py` | A/B 路径判定粗糙、gate 缺规则分型 |
| Model label 治理 | `src/core/analytics/toolkit/common.py`, `src/core/analytics/toolkit/model_train.py`, `src/core/analytics/toolkit/model_eval.py` | 标签近似 ID、类别过多/过小、CV 不可行 |
| Report 结构与渲染 | `src/core/reporting/assembler.py`, `src/core/reporting/exporter.py` | 章节漂移、图表上下文缺失、附件渲染失败 |
| Quality score 口径 | `src/core/orchestration/graph.py` | quant_metric 统计口径不一致、run_audit 对齐缺失 |

## Current Validation Snapshot
- 模块测试：
  - `tests/test_analysis_closure_artifacts.py`
  - `tests/test_report_assembler_visuals.py`
- 状态：通过（含 A/B 对照渲染、pdf 预览 fallback、路径异常降级、outline 冲突保护）。
