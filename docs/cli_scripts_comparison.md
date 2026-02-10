# DeepAnalyze CLI 脚本对比分析

## 📋 脚本文件清单

### 核心分析脚本
1. **`run_complete_docs/analysis.sh`** - 一站式数据分析脚本
2. **`run_complete_demo.sh`** - CLI完整演示脚本  
3. **`demo.sh`** - CLI模式演示脚本

## 🔍 详细对比分析

### 1. `run_complete_docs/analysis.sh` vs `run_complete_demo.sh`

| 特性 | `run_complete_docs/analysis.sh` | `run_complete_demo.sh` |
|------|---------------------------|------------------------|
| **目标** | 一站式数据分析流程 | CLI功能完整演示 |
| **执行方式** | 单步完整分析 | 分步骤演示 |
| **输出格式** | 交互式会话结果 | JSON文件输出 |
| **重点展示** | 分析结果本身 | 分析过程分解 |

#### `run_complete_docs/analysis.sh` 特点：
```bash
# 一步完成所有分析
python direct_cli.py --analyze "$DATA_FILE" \
    --docs/analysis-types descriptive inferential correlation quality \
    --report \
    --report-type analytical \
    --visualize
```
- **优势**: 简洁高效，适合快速获得分析结果
- **适用场景**: 日常数据分析任务，追求效率

#### `run_complete_demo.sh` 特点：
```bash
# 分步骤执行，每步输出到文件
python direct_cli.py quality --data-file "$DATA_FILE" --output-file "$OUTPUT_DIR/quality_report.json"
python direct_cli.py analyze --data-file "$DATA_FILE" --type descriptive --output-file "$OUTPUT_DIR/descriptive_docs/analysis.json"
python direct_cli.py analyze --data-file "$DATA_FILE" --type correlation --output-file "$OUTPUT_DIR/correlation_docs/analysis.json"
```
- **优势**: 过程透明，结果可追溯
- **适用场景**: 学习演示，教学用途

### 2. `demo.sh` 与其他脚本的关系

`demo.sh` 是最基础的演示脚本，展示CLI的基本使用方法：
```bash
# 展示基本功能
python direct_cli.py --analyze test_data.csv --results
python direct_cli.py --analyze test_data.csv --visualize  
python direct_cli.py --analyze test_data.csv --report
```

## 📊 脚本使用场景建议

### 🎯 选择指南

**日常数据分析** → 使用 `run_complete_docs/analysis.sh`
- 需要快速获得分析结果
- 不关心中间过程
- 追求操作简便

**学习和演示** → 使用 `run_complete_demo.sh`  
- 需要了解分析过程
- 要求结果可追溯
- 适合教学展示

**功能探索** → 使用 `demo.sh`
- 初次接触CLI功能
- 想了解基本命令
- 验证环境配置

## 🔧 技术实现差异

### 命令参数对比

| 功能 | `run_complete_docs/analysis.sh` | `run_complete_demo.sh` |
|------|---------------------------|------------------------|
| 数据分析 | `--analyze` | `analyze` 子命令 |
| 可视化 | `--visualize` | 未包含 |
| 报告生成 | `--report` | 未包含 |
| 质量检查 | 集成在分析类型中 | 独立的 `quality` 子命令 |
| 输出方式 | 会话存储 | JSON文件输出 |

### 依赖文件

**共同依赖**：
- 数据文件：`../../data/examples/simpson_paradox_docs/analysis/data/Simpson.csv`
- CLI脚本：`direct_cli.py`

**独有依赖**：
- `run_complete_demo.sh` 需要：`test_data.csv`（在 `src/cli/` 目录下）

## 📝 文档覆盖情况

### 现有文档提及情况

经查证，目前主要文档中：
- ✅ `README.md` - 提到了CLI的基本使用
- ✅ `README_ZH.md` - 介绍了三种CLI模式
- ✅ `README_CLI_USAGE.md` - 详细说明了CLI功能
- ❌ 以上文档均未具体提及这三个脚本文件

### 建议改进

1. **在README中添加脚本说明**：
   ```markdown
   ## 🚀 快速启动脚本
   
   ### 一键分析脚本
   ```bash
   ./run_complete_docs/analysis.sh    # 一站式数据分析
   ./run_complete_demo.sh        # 分步骤演示分析
   ./demo.sh                     # 基础功能演示
   ```
   ```

2. **在CLI文档中补充**：
   - 各脚本的使用场景
   - 参数配置说明
   - 输出结果解释

## 🎯 结论

三个脚本各有定位，互为补充：
- **`run_complete_docs/analysis.sh`**: 生产级一键分析工具
- **`run_complete_demo.sh`**: 教学级分步演示工具  
- **`demo.sh`**: 入门级基础演示工具

建议根据具体使用场景选择合适的脚本，避免重复开发功能相似的脚本。
