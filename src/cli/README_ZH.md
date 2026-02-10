# DeepAnalyze 命令行界面（CLI）

DeepAnalyze 提供三种 CLI 模式，满足不同使用场景需求：

## 🚀 快速开始

### 模式选择

**1. 统一入口模式（推荐）**
```bash
# 启动统一 CLI，选择模式
python unified_cli.py --help

# API 模式 - 需要运行服务器
python unified_cli.py --api-mode

# 直接模式 - 无需服务器
python unified_cli.py --direct-mode
```

**2. API 模式**
需要先启动 DeepAnalyze API 服务器：
```bash
cd ../../src/api
python start_server.py
```

然后运行 CLI：
```bash
# 英文版
python api_cli.py

# 中文版  
python api_cli_ZH.py
```

**3. 直接模式**
无需启动服务器，直接调用模块功能：
```bash
# 交互模式
python direct_cli.py

# 批处理模式
python direct_cli.py --analyze data.csv --visualize --report
```

### 先决条件

请先在 `src/api/config.py` 或 `.env` 中配置可用的 OpenAI 兼容 LLM 服务地址（仅 API 模式需要）。

## 📋 命令列表

### 统一 CLI 模式选择
```bash
# 选择 API 模式（需要服务器）
python unified_cli.py --api-mode [选项...]

# 选择直接模式（无需服务器）  
python unified_cli.py --direct-mode [选项...]
```

### API 模式命令

#### 基础命令
- `help` - 显示帮助信息  
- `quit` / `exit` - 退出程序  
- `clear` - 清除对话历史  
- `clear-all` - 清除所有内容，包括已上传的文件

#### 文件管理
- `files` - 查看已上传的文件  
- `upload <文件路径>` - 上传新文件  
- `delete <文件ID>` - 删除指定文件  
- `download <文件ID> [保存路径]` - 下载文件

#### 系统与历史记录
- `status` - 显示系统状态  
- `history` - 显示对话历史  
- `fid` - 显示所有文件名及其完整 ID

### 直接模式命令

#### 基础操作
- `help` - 显示帮助信息
- `info` - 显示会话信息  
- `clear` - 清除会话数据
- `quit`/`exit`/`q` - 退出程序

#### 数据分析
- `analyze <文件路径> [分析类型...]` - 直接分析数据文件
- `viz [图表类型]` - 基于分析结果生成可视化
- `report [报告类型]` - 基于分析结果生成报告
- `results` - 列出分析结果和洞察

#### 支持的选项
- 图表类型：`auto`, `bar`, `line`, `scatter`, `histogram`, `pie`
- 报告类型：`analytical`, `executive`, `technical`
- 分析类型：`descriptive`, `inferential`, `predictive`, `prescriptive`

## 💬 使用示例

### 统一 CLI 使用
```bash
# 交互式选择模式
python unified_cli.py

# 直接指定 API 模式
python unified_cli.py --api-mode --interactive

# 直接指定直接模式
python unified_cli.py --direct-mode --interactive

# 批处理分析（直接模式）
python unified_cli.py --direct-mode --analyze data.csv --visualize --report
```

### API 模式使用示例

#### 基础聊天
```
> 分析此数据集并生成洞察
```

#### 文件上传与分析
```
> upload data.csv
✅ 文件已上传：file-abc123...

> 分析已上传的数据并创建可视化图表
📊 正在生成分析...
📈 已创建图表：docs/analysis.png, trends.png
📝 已生成报告：report.md
```

### 直接模式使用示例

#### 批处理分析
```bash
# 单步完成数据分析全流程
python direct_cli.py --analyze sales_data.csv --visualize --report

# 指定分析类型和输出格式
python direct_cli.py --analyze data.csv --analysis-types descriptive inferential --chart-type bar --report-type executive
```

#### 交互式分析
```
DirectCLI> analyze employee_data.csv
📊 Analyzing data: employee_data.csv
✅ Analysis completed successfully!

DirectCLI> viz bar
🎨 Generating visualization...
✅ Visualization generated successfully!

DirectCLI> report executive  
📋 Generating report...
✅ Report generated successfully!
```

#### AI 助手咨询
```
DirectCLI> 帮我分析这些销售数据的主要趋势
🤖 Consulting AI assistant...
✅ AI assistant responded!

[显示 AI 分析结果]
```

### 流式响应

CLI 会自动以流式方式显示响应，在 DeepAnalyze 分析数据并生成洞察时实时展示进度。

## 🔧 配置说明

CLI 默认连接到 `http://localhost:48200/v1` 的 DeepAnalyze API 服务器。端口可在 `src/api/config.py` 中调整（见 `API_PUBLIC_BASE_V1`）。

命令历史将分别保存至 `~/.deeppanalyze_history_en`（英文版）或 `~/.deeppanalyze_history_zh`（中文版）。
