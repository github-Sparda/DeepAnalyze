# DeepAnalyze 中文说明文档

本文档面向项目维护与二次开发，重点说明代码结构、模块职责、运行形态与关键配置。若你只想快速上手，请直接阅读 `README.ZH.md`。

## 1. 代码结构与模块职责

```
DeepAnalyze/
├─ API/                 # OpenAI 风格 API 服务（FastAPI）
├─ assets/              # 文档图片与演示素材
├─ deepanalyze/         # 核心库与训练/推理相关代码
├─ demo/                # WebUI / JupyterUI / CLI 示例
├─ docker/              # 容器化部署相关文件
├─ example/             # API 调用示例脚本
├─ playground/          # 评测/对比与实验入口
├─ scripts/             # 训练/评测脚本入口
├─ deepanalyze.py       # Python 入口封装
├─ run.py               # 运行入口（可能用于调试/实验）
├─ requirements.txt     # 推理依赖
└─ README.md            # 英文说明
```

### 关键目录说明

- `API/`  
  提供 OpenAI 风格的 `/v1/chat/completions`、`/v1/files` 等接口。  

- `demo/`  
- `demo/chat`：Web UI（浏览器交互，默认端口 4000，见 `API/config.py` `FRONTEND_PORT`）  
  - `demo/jupyter`：Jupyter Lab 交互界面  
  - `demo/cli`：终端交互 UI  

- `example/`  
  提供 requests / openai SDK 的调用示例，适合自动化测试或集成。

- `deepanalyze/`  
  模型与训练/推理相关代码，包含适配脚本与训练框架集成。

- `playground/`  
  评测与实验入口，适合对比不同模型或流程。

## 2. 功能概览

- 端到端数据科学任务：数据准备、分析、建模、可视化、报告生成。
- 多数据源支持：结构化（CSV/Excel/DB）、半结构化（JSON/YAML/XML）、非结构化（Markdown/TXT）。
- 多交互方式：Web UI / Jupyter UI / CLI / OpenAI 风格 API。
- 文件上传与结果回传：支持文件上传、生成图表/报告并可下载。

## 3. 核心运行形态

DeepAnalyze 的默认推理路径是：

2) 再启动 API 服务（`API/start_server.py`）  
3) UI 或 CLI 通过 API 调用模型能力

## 4. 关键配置与端口

端口与服务地址统一在 `API/config.py` 中设置，其他模块应通过该文件引用。

API 服务默认端口（见 `API/README.md`）：

- API：`http://localhost:48200`
- 文件下载：`http://localhost:48100`

## 4.1 报告导出与递归深度

可在 `.env` 中设置以下参数：

- `DEEPANALYZE_REPORT_FORMAT`：`html`/`markdown`/`pdf`/`docx`，默认 `html`
- `DEEPANALYZE_REPORT_EXPORT_MODE`：`academic_redraw`/`html_convert`/`html_print`
- `DEEPANALYZE_REPORT_LANGUAGE`：报告语言（默认 `zh`）
- `DEEPANALYZE_MAX_DEPTH`：递归深度（默认 `1`，最大 `3`）

## 5. 常见使用入口

- Web UI：`demo/chat`
- Jupyter UI：`demo/jupyter`
- CLI：`demo/cli`
- API：`API/`

## 6. 示例数据与提示词格式

在 `README.md` 中给出了典型的 prompt 结构示例，核心要素包括：

- 任务指令（Instruction）
- 多个文件的元信息（name/size）
- workspace 指向实际数据目录

## 7. 适合的自动化测试点

- `/v1/chat/completions`：最关键的稳定性与结果一致性测试
- `/v1/files`：文件上传/下载/删除流
- `/health`：服务存活与端口可达性

如需编写自动化测试，可以复用 `example/` 中的脚本作为基线。
