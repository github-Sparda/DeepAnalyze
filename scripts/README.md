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

## Orchestrator Outputs (新增)

当启用编排分析后，新增关键产物：

- `meta/completion_validation.json`：完成态校验结果（是否允许确定性结论）
- `meta/iteration_lineage.json`：递归迭代链路与触发原因
- `result/path_adjudication.json`：A/B 冲突后 Path-C 自动裁决记录
- `result/ml_repro_bundle_index.json`：预测类假设复现包索引

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
