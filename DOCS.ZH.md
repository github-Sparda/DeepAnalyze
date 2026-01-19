# DeepAnalyze 中文说明文档

本文档面向项目维护与二次开发，重点说明代码结构、模块职责、运行形态与关键配置。若仅需快速上手，请阅读 `README.ZH.md`。

## 1. 代码结构与模块职责

```
DeepAnalyze/
├─ API/                 # OpenAI 风格 API 服务（FastAPI）
├─ assets/              # 文档图片与演示素材
├─ deepanalyze/         # 核心库（LangGraph 编排 / 报告 / 图表）
├─ demo/                # WebUI / JupyterUI / CLI 示例
├─ example/             # API 调用示例脚本
├─ playground/          # 评测/对比与实验入口
├─ scripts/             # 启动/停止服务脚本
├─ requirements.txt     # 推理依赖
└─ README.md            # 英文说明
```

### 核心模块

- `deepanalyze/orchestration/`
  LangGraph 编排主流程与状态管理（文件理解 → 规划 → 代码 → 执行 → 结果 → 报告）。
- `deepanalyze/reporting/`
  报告模板与导出（HTML/Markdown/PDF/DOCX，支持导出策略与模板配置）。
- `deepanalyze/visualization/`
  图表主题与绘图封装（学术风 / 仪表盘风）。

### 交互入口

- `API/`：OpenAI 风格 API（`/v1/chat/completions`、`/v1/files` 等）。
- `demo/backend.py`：WebUI 使用的 Demo 后端（支持 LangGraph 编排开关）。
- `demo/chat`：WebUI 前端（默认端口 4000，见 `API/config.py`）。
- `demo/jupyter`：Jupyter Lab 交互界面。
- `demo/cli`：CLI 终端交互界面。

## 2. 功能概览

- 端到端数据科学任务：数据准备、分析、建模、可视化、报告生成。
- 多数据源支持：CSV/Excel/JSON/YAML/XML/TXT/Markdown 等。
- 多交互方式：WebUI / JupyterUI / CLI / OpenAI 风格 API。
- 文件上传与结果回传：支持上传、生成图表/报告并下载。

## 3. 核心流程

默认流程为：读文件 → 规划 → 代码生成 → 执行 → 结果分析 → 报告输出。
启用 LangGraph 编排后可控制递归深度（默认 1，上限 3）。

## 4. 运行形态与启动方式

- API Server（标准 OpenAI 风格）
  - `API/start_server.py`，对外提供 `/v1/*` 接口。
- WebUI Demo
  - `scripts/start_services.sh` 或 `demo/start.sh` 启动 Demo 后端 + 前端。
- JupyterUI
  - `demo/jupyter/server.py` 负责连接 Jupyter Lab 并执行代码。
- CLI
  - `demo/cli/api_cli.py` / `demo/cli/api_cli_ZH.py`，默认调用 API Server。

## 5. 关键配置（.env 与 API/config.py）

### 模型与服务
- `DEEPANALYZE_VLLM_BASE_URL`：上游模型 API 地址（兼容 OpenAI 协议）
- `DEEPANALYZE_VLLM_API_KEY`：API Key
- `DEEPANALYZE_MODEL_PATH` / `DEFAULT_MODEL`：模型名称

### 编排与递归
- `DEEPANALYZE_USE_ORCHESTRATOR`：是否启用 LangGraph 编排
- `DEEPANALYZE_MAX_DEPTH`：递归深度（默认 1，上限 3）

### 报告导出
- `DEEPANALYZE_REPORT_FORMAT`：`html`/`markdown`/`pdf`/`docx`
- `DEEPANALYZE_REPORT_EXPORT_MODE`：`academic_redraw`/`html_convert`/`html_print`
- `DEEPANALYZE_REPORT_LANGUAGE`：报告语言（默认 `zh`）
- `DEEPANALYZE_REPORT_TITLE`/`SUBTITLE`/`AUTHOR`/`LOGO`/`TOC`/`FOOTER`

### 图表风格
- `DEEPANALYZE_VISUAL_STYLE`：`academic`/`dashboard`
- `DEEPANALYZE_VISUAL_INTERACTIVE`：是否输出交互图（Plotly）

### 端口
- API：`http://localhost:48200`
- 文件下载：`http://localhost:48100`
- WebUI：`http://localhost:4000`（默认）

## 6. 报告与图表说明

- 报告导出使用 `deepanalyze/reporting/exporter.py`，HTML 为默认输出。
- PDF 依赖 `weasyprint`，若缺失会降级输出提示文本。
- DOCX 基于 HTML 纯文本转换，适合基础输出。
- 图表主题在 `deepanalyze/visualization/theme.py` 中定义，Plotly 为交互优先库。

## 7. 工作目录与日志

- `workspace/`：会话工作区（上传文件、生成文件、报告输出等）。
- `logs/`：运行日志（脚本启动时生成）。
- 可通过 `DEEPANALYZE_DEBUG_STREAM` 输出 LLM 流式调试日志。

## 8. 自动化验证建议

- `/v1/chat/completions`：流式与非流式输出
- `/v1/files`：上传/下载/删除
- WebUI：前端流式显示与停止任务
- 编排模式：递归深度为 2 时是否增量生成结果
