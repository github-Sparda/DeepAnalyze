# DeepAnalyze Direct CLI 使用说明

## 概述

这是一个直接调用 DeepAnalyze 各个核心模块功能的命令行工具，无需启动 src/api 服务器即可直接使用数据分析、可视化、报告生成等功能。

## 🚀 快速开始

### 基本用法

```bash
# 分析数据文件
python scripts/src/core_cli.py --file data.csv --analyze

# 指定分析类型
python scripts/src/core_cli.py --file data.csv --analyze --types descriptive inferential

# 生成可视化图表
python scripts/src/core_cli.py --visualize data.csv

# 与AI助手对话
python scripts/src/core_cli.py --chat "分析这份数据的主要特征"

# 生成报告
python scripts/src/core_cli.py --report-title "分析报告" --report-content "报告内容"

# 进入交互模式
python scripts/src/core_cli.py --interactive
```

## 📋 可用命令

### 数据分析命令
```bash
# 基本数据分析
python scripts/src/core_cli.py --file data.csv --analyze

# 指定分析类型
python scripts/src/core_cli.py --file data.csv --analyze --types descriptive
python scripts/src/core_cli.py --file data.csv --analyze --types inferential predictive
```

支持的分析类型：
- `descriptive` - 描述性统计分析
- `inferential` - 推断性统计分析  
- `predictive` - 预测分析
- `diagnostic` - 诊断分析
- `prescriptive` - 规范性分析

### 可视化命令
```bash
# 生成数据可视化图表
python scripts/src/core_cli.py --visualize data.csv
```

### AI助手命令
```bash
# 与AI助手对话
python scripts/src/core_cli.py --chat "请分析这些数据的趋势"
```

### 报告生成命令
```bash
# 生成分析报告
python scripts/src/core_cli.py --report-title "销售分析报告" --report-content "这里是报告的详细内容"
```

### 交互模式
```bash
# 进入交互式命令行界面
python scripts/src/core_cli.py --interactive
```

在交互模式下可用的命令：
- `modules` - 显示可用模块
- `session` - 显示当前会话
- `analyze <file_path>` - 分析数据文件
- `visualize <file_path>` - 生成可视化图表
- `chat <message>` - 与AI助手对话
- `report <title> <content>` - 生成报告
- `help` - 显示帮助信息
- `quit`/`exit` - 退出程序

## 📁 模块功能说明

### 1. 数据分析模块 (analytics)
- 直接调用 `analyze_dataset()` 函数
- 支持多种分析类型
- 自动生成数据摘要和洞察

### 2. 状态管理模块 (state)
- 自动创建和管理分析会话
- 跟踪分析状态和结果

### 3. 可视化模块 (visualization)
- 调用 `render_distribution()` 等绘图函数
- 生成统计图表和分布图
- 支持学术风格和仪表板风格

### 4. AI助手模块 (assistant)
- 调用 AI 助手引擎
- 支持自然语言查询和分析

### 5. 报告生成模块 (reporting)
- 创建结构化分析报告
- 支持多种报告格式

## 🎯 使用示例

### 示例1：简单数据分析
```bash
python scripts/src/core_cli.py --file sales_data.csv --analyze --types descriptive
```

### 示例2：生成可视化
```bash
python scripts/src/core_cli.py --visualize employee_data.csv
```

### 示例3：交互式分析
```bash
python scripts/src/core_cli.py --interactive
>>> analyze customer_data.csv
>>> visualize customer_data.csv  
>>> chat "基于这些数据给出业务建议"
>>> report "客户分析报告" "详细分析内容..."
```

## ⚙️ 配置要求

- Python 3.8+
- 必需依赖包已在项目 requirements.txt 中列出
- 部分可视化功能需要 matplotlib、seaborn、plotly 等库

## 📝 注意事项

1. **字体警告**：可视化时可能会出现字体找不到的警告，但这不会影响图表生成
2. **会话管理**：每次运行都会自动创建新的分析会话
3. **文件路径**：请使用相对路径或绝对路径指定数据文件
4. **内存使用**：大数据集分析时请注意内存使用情况

## 🔧 故障排除

常见问题及解决方案：

1. **模块导入失败**：确保在项目根目录运行命令
2. **数据文件不存在**：检查文件路径是否正确
3. **可视化失败**：确认安装了必要的绘图库
4. **AI助手无响应**：某些功能可能需要配置相应的 src/api 密钥

## 📚 相关文档

- [src/api CLI 使用说明](../src/cli/README.md) - 基于 src/api 的 CLI 工具
- [Jupyter CLI 使用说明](../src/jupyter/README.md) - Jupyter 界面 CLI
- [技术文档索引](../DOCS.ZH.md) - 完整技术文档