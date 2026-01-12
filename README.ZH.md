# DeepAnalyze 中文 README

DeepAnalyze 是面向数据科学任务的智能分析系统，能够在尽量少的人工干预下完成数据准备、探索分析、建模、可视化与报告生成，支持多种数据形态并提供多种交互入口（Web/Jupyter/CLI/API）。

## 亮点与特点

- **端到端数据科学**：从数据清洗、分析到报告产出的一体化能力
- **多数据源支持**：CSV/Excel/JSON/YAML/XML/TXT/Markdown 等
- **多交互方式**：Web UI / Jupyter UI / CLI / OpenAI 风格 API
- **文件上传与生成结果**：自动产出图表、报告文件并支持下载
- **开源与可扩展**：模型、代码、训练数据均可扩展

## 项目结构速览

```
DeepAnalyze/
├─ API/          # OpenAI 风格 API 服务
├─ demo/         # Web/Jupyter/CLI 界面
├─ example/      # API 调用示例脚本
├─ deepanalyze/  # 核心库与训练/推理相关代码
├─ assets/       # 文档图示
├─ scripts/      # 训练/评测脚本
└─ playground/   # 评测与实验入口
```

如需更详细的结构说明，请看 `DOCS.ZH.md`。

## 快速开始（推理）

### 1) 安装依赖

建议使用独立环境：

```bash
conda create -n deepanalyze python=3.12 -y
conda activate deepanalyze
pip install -r requirements.txt
```

### 2) 启动模型（vLLM）

```bash
vllm serve DeepAnalyze-8B --host 0.0.0.0 --port 48000
```

### 3) 启动 API 服务

```bash
cd /home/huangzw/Project/DeepAnalyze/API
python start_server.py
```

默认端口（可在 `API/config.py` 中统一调整）：

- vLLM：`http://localhost:48000`
- API：`http://localhost:48200`
- 文件服务：`http://localhost:48100`

## Web UI

端口/地址统一在 `API/config.py` 中配置，如需修改请以该文件为准。

```bash
cd /home/huangzw/Project/DeepAnalyze/demo/chat
npm install
cd ..
bash start.sh
```

浏览器访问：`http://localhost:4000`（端口可在 `API/config.py` 中调整）

如需修改部署 IP，请调整：

- `demo/backend.py`
- `demo/chat/lib/config.ts`

## Jupyter UI

Jupyter 界面位于 `demo/jupyter`，适合习惯 Notebook 的用户。

## CLI

```bash
cd /home/huangzw/Project/DeepAnalyze/API
python start_server.py  # 先启动 API

cd /home/huangzw/Project/DeepAnalyze/demo/cli
python api_cli.py       # 英文
# 或
python api_cli_ZH.py    # 中文
```

## OpenAI 风格 API

### 1) 上传文件

```bash
FILE_RESPONSE=$(curl -s -X POST "http://localhost:48200/v1/files" \
    -F "file=@data.csv" \
    -F "purpose=file-extract")

FILE_ID=$(echo $FILE_RESPONSE | jq -r '.id')
```

### 2) 发送分析请求

```bash
curl -X POST http://localhost:48200/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d "{
        \"model\": \"DeepAnalyze-8B\",
        \"messages\": [
          {
            \"role\": \"user\",
            \"content\": \"生成一份数据分析报告\",
            \"file_ids\": [\"$FILE_ID\"]
          }
        ],
        \"temperature\": 0.4
      }"
```

更多 API 细节见 `API/README.md`。

## Python 调用示例

```python
from deepanalyze import DeepAnalyzeVLLM

prompt = \"\"\"# Instruction
生成一份数据分析报告。

# Data
File 1: {\"name\": \"person.csv\", \"size\": \"10.6KB\"}
File 2: {\"name\": \"enrolled.csv\", \"size\": \"20.4KB\"}\"\"\"

workspace = \"/path/to/your/data_dir\"
deepanalyze = DeepAnalyzeVLLM(\"/path/to/DeepAnalyze-8B\")
answer = deepanalyze.generate(prompt, workspace=workspace)
print(answer[\"reasoning\"])
```

## 示例与测试

- `example/exampleRequest.py`：requests 调用示例
- `example/exampleOpenAI.py`：OpenAI SDK 调用示例

## 常见问题

**Q: 是否必须使用 vLLM？**  
A: 目前 API 形态默认依赖 vLLM 作为模型服务。

**Q: 是否支持文件上传与结果文件下载？**  
A: 支持。文件上传 `/v1/files`，生成文件通过文件服务端口下载。

## 贡献

欢迎提交 PR、用例和改进建议。具体贡献方式见 `CONTRIBUTION.md`。
