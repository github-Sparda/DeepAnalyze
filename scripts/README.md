# Service Scripts

These scripts start/stop the DeepAnalyze demo backend + frontend only (no LLM model).

## Start

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

## Stop

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

## Status

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

## Restart

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

## Configuration

All ports/hosts are configured in `/home/huangzw/Project/DeepAnalyze/.env` and loaded by `API/config.py`.
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
