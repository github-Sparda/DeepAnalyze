# DeepAnalyze 目录结构重构方案

## 🎯 设计原则
1. **单一职责** - 每个目录有明确且唯一的功能定位
2. **层次清晰** - 按照功能域划分，避免跨层级引用
3. **易于维护** - 结构直观，新人容易理解和使用
4. **向前兼容** - 提供迁移路径，不影响现有功能

## 📁 新目录结构设计

```
DeepAnalyze/
├── src/                          # 核心源码（原src/core/）
│   ├── core/                     # 核心分析引擎
│   ├── api/                      # API接口（原API/）
│   ├── cli/                      # 命令行工具（原src/cli/）
│   ├── web/                      # Web界面（原src/web/）
│   ├── jupyter/                  # Jupyter支持（原src/jupyter/）
│   └── utils/                    # 工具库
│
├── data/                         # 所有数据相关文件
│   ├── data/exampless/                 # 示例数据集（合并data/examples/和data/examples/benchmarks/）
│   │   ├── student_loan/         # 学生贷款分析示例
│   │   ├── simpson_paradox/      # Simpson悖论示例
│   │   └── benchmarks/           # 基准测试数据
│   ├── sessions/                 # 用户会话数据（统一data/sessions/active/）
│   │   ├── active/               # 活跃会话
│   │   └── data/sessions/archivedd/             # 归档会话
│   └── data/cache/                    # 缓存数据（合并data/cache/和data/cache/temporary/）
│       ├── semantic/             # 语义缓存
│       ├── disk/                 # 磁盘缓存
│       └── data/cache/temporary/            # 临时文件
│
├── docs/guides/                         # 所有文档（合并docs/guides/和docs/analysis/）
│   ├── docs/design/                   # 设计文档（原docs/design/）
│   ├── specs/                    # 技术规范（原docs/specs/specs/）
│   ├── guides/                   # 使用指南
│   ├── api/                      # API文档
│   └── tutorials/                # 教程示例
│
├── outputs/                      # 生成产物（统一outputs/功能）
│   ├── reports/                  # 分析报告
│   ├── visualizations/           # 可视化图表
│   ├── exports/                  # 导出文件
│   └── outputs/logs/                     # 运行日志（原outputs/logs/）
│
├── scripts/                      # 辅助脚本
│   ├── dev/                      # 开发辅助脚本
│   ├── deploy/                   # 部署脚本
│   ├── maintenance/              # 维护脚本
│   └── tests/                    # 测试脚本
│
├── tests/                        # 测试代码
├── assets/                       # 静态资源
├── config/                       # 配置文件
└── .gitignore                    # 版本控制忽略文件
```

## 🔄 迁移映射关系

### 源目录 → 目标目录
```
src/core/           → src/core/
src/api/                  → API/
src/cli/             → src/cli/
src/web/            → src/web/
src/jupyter/         → src/jupyter/

data/examples/              → data/data/exampless/
data/examples/benchmarks/           → data/data/exampless/benchmarks/
data/sessions/active/            → data/sessions/active/
scripts/data/sessions/active/    → data/sessions/active/
src/cli/data/sessions/active/   → data/sessions/active/

data/cache/                → data/data/cache/
data/cache/temporary/                 → data/data/cache/data/cache/temporary/
outputs/              → outputs/
outputs/logs/                 → outputs/outputs/logs/

docs/guides/                 → docs/guides/guides/
docs/analysis/             → docs/guides/docs/analysis/
docs/design/               → docs/guides/docs/design/
docs/specs/             → docs/guides/specs/

data/sessions/archived/              → data/sessions/data/sessions/archivedd/
```

## 🛠️ 迁移实施计划

### 第一阶段：准备工作
1. 创建新的目录结构框架
2. 备份重要数据
3. 编写迁移脚本

### 第二阶段：数据迁移
1. 移动文件到新位置
2. 更新代码中的路径引用
3. 更新配置文件路径

### 第三阶段：文档更新
1. 更新README和其他文档
2. 更新导入路径说明
3. 提供迁移指南

### 第四阶段：验证测试
1. 运行单元测试
2. 验证CLI功能
3. 测试Web界面

## ⚠️ 注意事项

1. **路径引用更新**：需要全局搜索替换Python代码、配置文件、文档中的旧路径
2. **相对路径处理**：注意相对路径的层级变化
3. **权限保持**：迁移过程中保持文件权限不变
4. **软链接处理**：如有软链接需要重新建立
5. **版本控制**：提交前做好分支管理

## 📋 待办事项清单

- [ ] 创建新目录结构框架
- [ ] 编写自动化迁移脚本
- [ ] 更新所有代码中的路径引用
- [ ] 更新配置文件路径
- [ ] 修改文档和README
- [ ] 运行全面测试验证
- [ ] 清理旧目录结构
- [ ] 更新开发者文档