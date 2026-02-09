# Scripts Directory

This directory contains various utility scripts for the DeepAnalyze project.

## Service Management Scripts

These scripts start/stop the DeepAnalyze demo backend + frontend only (no LLM model).

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

### Main Tools
- `deepanalyze_cli.py` - Main CLI interface for DeepAnalyze
- `config_manager.py` - Configuration management tool
- `full_process_validation.py` - Complete process validation
- `refactor_directories.py` - Directory refactoring utilities

### Testing and Validation
- `test_progress_system.py` - Progress system testing
- `test_semantic_cache.py` - Semantic cache testing
- `validate_artifacts.py` - Artifact validation
- `validate_refactor.py` - Refactoring validation
- `validate_semantic_cache.py` - Semantic cache validation

### Demo and Examples
- `demo_cli_usage.py` - CLI usage demonstration
- `demo_security_system.py` - Security system demonstration
- `visualization_demo.py` - Visualization demonstration

### Maintenance
- `clean_empty_workspace_dirs.py` - Clean empty workspace directories

## Temporary Scripts

Temporary and one-shot scripts are located in the [one-shot](./one-shot/) directory.
These scripts are typically used for one-time fixes or specific tasks.

See [one-shot/README.md](./one-shot/README.md) for details.

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
### Analysis Tools
- `demo_cli_wrapper.py` - CLI demonstration wrapper for one-command analysis
- `generate_complete_report.py` - Complete analysis report generator with visualizations
