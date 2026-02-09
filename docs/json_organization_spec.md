# DeepAnalyze JSON文件组织规范

## 目录结构规范

```
/home/huangzw/Project/DeepAnalyze/
├── outputs/                    # 统一的分析产物目录
│   ├── sessions/              # 会话相关文件
│   │   ├── metadata/         # 会话元数据（限制数量）
│   │   └── artifacts/        # 会话分析产物
│   ├── cli_docs/analysis/         # CLI工具分析结果
│   │   └── {session_id}/     # 按会话ID组织
│   │       ├── descriptive_docs/analysis.json
│   │       ├── correlation_docs/analysis.json  
│   │       └── quality_report.json
│   ├── validation_reports/   # 验证脚本报告
│   │   └── {timestamp}_{purpose}/
│   │       ├── hypotheses.json
│   │       ├── exploratory_docs/analysis.json
│   │       ├── programming_docs/analysis.json
│   │       └── final_report.json
│   └── data/examples/benchmarks/           # Playground数据
├── data/cache/temporary/                     # 临时文件目录
│   ├── cli_tests/           # CLI测试临时文件
│   └── validation_data/cache/temporary/     # 验证脚本临时文件
└── data/sessions/archived/                  # 归档的历史文件
    └── old_sessions/        # 旧会话文件归档
```

## 文件命名规范

### 会话相关文件
- `metadata.json` - 会话元数据
- `session_{timestamp}_{random}.json` - 会话产物

### 分析产物文件
- `descriptive_docs/analysis.json` - 描述性统计分析
- `correlation_docs/analysis.json` - 相关性分析
- `quality_report.json` - 数据质量报告
- `hypotheses.json` - 假设生成结果
- `exploratory_docs/analysis.json` - 探索性分析
- `programming_docs/analysis.json` - 编程分析
- `detailed_docs/analysis.json` - 详细分析
- `final_report.json` - 最终报告

### 时间戳格式
使用ISO 8601格式: `YYYYMMDD_HHMMSS`

### 示例文件名
- `20260209_093000_descriptive_docs/analysis.json`
- `validation_20260209_093000_hypotheses.json`

## 清理策略

### 会话文件保留规则
- data/sessions/active目录：保留最近50个会话
- scripts/data/sessions/active目录：保留最近10个会话
- src/cli/data/sessions/active目录：保留最近50个会话

### 归档规则
- 超过保留数量的会话移动到data/sessions/archived/old_sessions/
- 定期清理data/sessions/archived目录中超过30天的文件

### 临时文件清理
- data/cache/temporary/目录下的文件超过7天自动清理
- 每次测试运行前清空对应临时目录

## 使用建议

1. **新分析产物**应保存到outputs/对应的子目录
2. **临时测试文件**应保存到data/cache/temporary/目录
3. **长期保存的报告**应保存到outputs/validation_reports/
4. **会话相关文件**应遵循会话ID命名规范

## 自动化脚本

定期运行清理脚本：
```bash
# 清理会话文件
./scripts/cleanup_sessions.sh

# 清理临时文件  
./scripts/cleanup_data/cache/temporary.sh

# 统计文件数量
./scripts/count_json_files.sh
```