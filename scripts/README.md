# Scripts Directory

This directory contains various utility scripts for the DeepAnalyze project.

## Service Management Scripts

These scripts start/stop the DeepAnalyze orchestrator backend + WebUI only (no LLM model).

### Start
```bash
./scripts/start_services.sh
```

Start backend only:
```bash
./scripts/start_services.sh backend
```

Start frontend only:
```bash
./scripts/start_services.sh frontend
```

### Stop
```bash
./scripts/stop_services.sh
```

Stop backend only:
```bash
./scripts/stop_services.sh backend
```

Stop frontend only:
```bash
./scripts/stop_services.sh frontend
```

### Status
```bash
./scripts/status_services.sh
```

Check backend only:
```bash
./scripts/status_services.sh backend
```

Check frontend only:
```bash
./scripts/status_services.sh frontend
```

### Restart
```bash
./scripts/restart_services.sh
```

Restart backend only:
```bash
./scripts/restart_services.sh backend
```

Restart frontend only:
```bash
./scripts/restart_services.sh frontend
```

## Utility Scripts

## Classification Criteria
- `reusable-utility`: Safe for repeated use in dev/ops workflows.
- `one-shot-fix`: Intended for single-run remediation or migration; store in `scripts/one-shot/`.
- `demo-example`: Demonstrates usage but should not be treated as validation.
- `validation-test`: Verifies functionality or data integrity.
- `mock-simulation`: Uses synthetic data or template outputs without asserting functionality; these should be removed.

### Main Tools
- `deepanalyze_cli.py` - Main CLI interface for DeepAnalyze (reusable-utility)
- `config_manager.py` - Configuration management tool (reusable-utility)

### Testing and Validation
- `test_analysis_pipeline.py` - AnalysisPipeline smoke test on sample data (validation-test)
- `test_progress_system.py` - Progress system testing (validation-test)
- `test_semantic_cache.py` - Semantic cache testing (validation-test)
- `validate_artifacts.py` - Artifact validation (validation-test)
- `validate_refactor.py` - Refactoring validation (validation-test)
- `validate_semantic_cache.py` - Semantic cache validation (validation-test)

### Demo and Examples
- `analysis_pipeline.py` - Standalone analysis pipeline demo for local validation (demo-example)

## Temporary Scripts

暂无 one-shot 目录；需要临时修复脚本时请先评估是否可复用。

## Configuration

All ports/hosts are configured in `/home/huangzw/Project/DeepAnalyze/.env` and loaded by `src/api/config.py`.
Key variables:

- `DEEPANALYZE_VLLM_BASE_URL`
- `DEEPANALYZE_VLLM_API_KEY`
- `DEEPANALYZE_API_HOST`
- `DEEPANALYZE_API_PUBLIC_HOST`
- `DEEPANALYZE_API_PORT`
- `DEEPANALYZE_FILE_SERVER_HOST`
- `DEEPANALYZE_FILE_SERVER_PORT`
- `DEEPANALYZE_FRONTEND_HOST`
- `DEEPANALYZE_FRONTEND_PORT`
- `DEEPANALYZE_WEBSOCKET_HOST`
- `DEEPANALYZE_WEBSOCKET_PORT`
- `DEEPANALYZE_USE_ORCHESTRATOR`
- `DEEPANALYZE_MAX_DEPTH`
- `DEEPANALYZE_REPORT_FORMAT`
- `DEEPANALYZE_REPORT_LANGUAGE`
- `DEEPANALYZE_REPORT_EXPORT_MODE`
- `DEEPANALYZE_REPORT_TITLE`
- `DEEPANALYZE_REPORT_SUBTITLE`
- `DEEPANALYZE_REPORT_AUTHOR`
- `DEEPANALYZE_REPORT_LOGO`
- `DEEPANALYZE_REPORT_TOC`
- `DEEPANALYZE_REPORT_FOOTER`
- `DEEPANALYZE_PATHC_CONFLICT_THRESHOLD`  # Path-C 冲突触发阈值（默认 0.3）

可选运行时配置文件：

- `config/analysis_runtime.json`
- `config/hypothesis_profile_registry.json`

## Orchestrator Outputs (新增)

当启用编排分析后，新增关键产物：

- `meta/completion_validation.json`：完成态校验结果（是否允许确定性结论）
- `meta/closure_status/*.json`：关键阶段步骤级闭环状态（success / recovered / recoverable_failed / failed / skipped）
- `meta/recovery_trace/*.json`：关键阶段恢复轨迹
- `meta/plan_validation/file_summary_fallback.json`：文件摘要节点降级记录（可选）
- `meta/plan_validation/report_llm_fallback.json`：报告装配降级记录（可选）
- `meta/iteration_lineage.json`：递归迭代链路与触发原因
- `meta/research_digest.json`：递归前/最终阶段的短摘要，用于第二轮规划
- `meta/depth_focus_selection.json`：第二轮优先级选择结果（closure_followup / escalated_research）
- `meta/depth_delta.json`：第二轮相对第一轮是否带来实质深度增益
- `result/path_adjudication.json`：A/B 冲突后 Path-C 自动裁决记录
- `result/ml_repro_bundle_index.json`：预测类假设复现包索引
- `meta/analysis_quality_score.json`：新增 `closure_source` 字段表示闭环率判定口径
- `result/validation_failures.json`：按阶段聚合的阻塞失败项，用于报告与审计
- `result/differential_features_table.csv`：差异性假设的高优先级特征明细表（含 p/q 值、效应量、排序字段）
- `result/model_performance_comparison.csv`：预测假设的模型与基线对照指标
- `result/feature_importance_rf.json`：随机森林路径的特征重要性明细
- `plots/roc_curve.png` / `plots/pr_curve.png`：预测路径的真实评估曲线
- `plots/clustermap.png` / `plots/tsne_umap_plot.png`：相关/低维结构路径的辅助图表
- `result/hypothesis_matrix.json`：最终统一假设状态矩阵（基础证据、路径闭环、gate 判定合并口径）

预测类复现包目录示例：

- `result/ml_repro/h2/model_spec.json`
- `result/ml_repro/h2/data_split.json`
- `result/ml_repro/h2/metrics.json`
- `result/ml_repro/h2/training_log.txt`

## Testing (common 环境)

```bash
conda activate common
pytest -q tests/test_conflict_auto_path_c_adjudication.py tests/test_ml_repro_bundle_contract.py tests/test_completion_validator_states.py
```
### Analysis Tools
- `demo_cli_wrapper.py` - CLI demonstration wrapper for one-command analysis (demo-example)
- `run_serum_cli_analysis.py` - Serum dataset end-to-end CLI analysis runner (validation-test)

### Orchestrated Runner
- `run_serum_orchestrated_analysis.py` - 全流程编排分析入口（validation-test）

示例：
```bash
conda activate common
python scripts/run_serum_orchestrated_analysis.py --max-depth 2 --output-dir outputs/serum_orchestrated
```

参数补充：
- `--strict-llm-check`：启动时 LLM 连通性检查失败即退出；默认关闭，默认会继续进入可降级执行模式。
- `--strict-fallback-mode`：启用强兜底质量门槛（默认开启）；当 LLM 不可用且门槛未通过时，优先跳过低可信步骤/报告，而非生成弱质量结果。
- `--no-strict-fallback-mode`：关闭强兜底门槛，允许更宽松的兜底行为（不推荐生产使用）。

多轮递进说明：

- `--max-depth 1`：仅执行首轮分析。
- `--max-depth > 1`：第二轮不会盲目扩写，而会优先读取 `research_digest` 和 `depth_focus_selection`：
  - 若首轮仍有高价值未闭环假设，则进入 `closure_followup`
  - 若首轮已有稳定发现，则可进入 `escalated_research`
  - 若没有明确增益空间，则停止递归并在 `depth_delta.json` 中说明“无实质深度增益”
