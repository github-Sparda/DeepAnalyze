# 增强版报告生成和管理系统使用文档

## 概述
DeepAnalyze增强版报告系统提供了完整的报告生命周期管理，支持多种报告类型、模板系统、版本控制和多格式导出功能。

## 核心特性

### 1. 完整的报告生命周期
- 报告创建、编辑、审核、发布、归档
- 版本控制和变更历史追踪
- 元数据管理和标签系统

### 2. 多种报告类型
- 分析报告 (Analytical)
- 技术报告 (Technical)  
- 执行报告 (Executive)
- 研究报告 (Research)
- 摘要报告 (Summary)

### 3. 模板系统
- 预定义报告模板
- 自定义模板支持
- 变量替换和样式配置

### 4. 多格式导出
- HTML、PDF、Markdown、DOCX、JSON
- 样式定制和格式转换
- 批量导出功能

## 使用方法

### 基本报告操作

```python
from src/core.reporting.manager import (
    create_new_report,
    ReportType,
    ReportStatus
)

# 创建新报告
metadata = create_new_report(
    session_id="docs/analysis_session_001",
    title="2024年销售数据分析报告",
    content="# 销售分析\n\n详细分析内容...",
    report_type=ReportType.ANALYTICAL,
    data/cache/temporarylate_id="analytical",
    metadata={
        "author": "数据分析团队",
        "tags": ["销售", "分析", "2024"],
        "keywords": ["销售额", "增长率", "市场份额"],
        "data_sources": ["sales_db_2024"]
    }
)

print(f"报告创建成功: {metadata.title}")
print(f"报告ID: {metadata.report_id}")
```

### 报告管理操作

```python
from src/core.reporting.manager import ReportManager

manager = ReportManager()

# 获取报告
report = manager.get_report("session_001", "report_12345")
if report:
    print(f"标题: {report['metadata']['title']}")
    print(f"内容: {report['content']}")

# 列出会话中的所有报告
reports = manager.list_reports("session_001")
for report_meta in reports:
    print(f"- {report_meta.title} ({report_meta.status.value})")

# 更新报告
success = manager.update_report(
    "session_001",
    "report_12345",
    metadata_updates={
        "status": ReportStatus.REVIEW.value,
        "tags": ["已审核", "待发布"]
    }
)

# 删除报告
deleted = manager.delete_report("session_001", "report_12345")
```

### 报告导出功能

```python
from src/core.reporting.manager import ExportFormat

# 导出为不同格式
formats = [
    (ExportFormat.HTML, "网页版报告"),
    (ExportFormat.PDF, "PDF文档"),
    (ExportFormat.MARKDOWN, "Markdown格式"),
    (ExportFormat.DOCX, "Word文档"),
    (ExportFormat.JSON, "结构化数据")
]

for format_type, description in formats:
    export_path = manager.export_report(
        session_id="session_001",
        report_id="report_12345",
        format=format_type
    )
    if export_path:
        print(f"{description}已导出至: {export_path}")
```

## 报告类型详解

### 分析报告 (ANALYTICAL)
```python
metadata = create_new_report(
    session_id="session_001",
    title="市场趋势分析报告",
    content=docs/analysis_content,
    report_type=ReportType.ANALYTICAL,
    data/cache/temporarylate_id="analytical"
)
# 适用于：数据探索、统计分析、趋势研究
```

### 执行报告 (EXECUTIVE)
```python
metadata = create_new_report(
    session_id="session_001", 
    title="Q1业务执行报告",
    content=executive_content,
    report_type=ReportType.EXECUTIVE,
    data/cache/temporarylate_id="executive"
)
# 适用于：高层决策、业务汇报、战略规划
```

### 技术报告 (TECHNICAL)
```python
metadata = create_new_report(
    session_id="session_001",
    title="技术实现方案",
    content=technical_content,
    report_type=ReportType.TECHNICAL
)
# 适用于：技术文档、实施方案、架构设计
```

## 模板系统使用

### 预定义模板
```python
# 分析报告模板
data/cache/temporarylate = manager.default_data/cache/temporarylates["analytical"]
print(f"模板名称: {data/cache/temporarylate.name}")
print(f"包含章节: {data/cache/temporarylate.sections}")
print(f"可用变量: {list(data/cache/temporarylate.variables.keys())}")

# 执行报告模板
exec_data/cache/temporarylate = manager.default_data/cache/temporarylates["executive"]
```

### 自定义模板创建
```python
from src/core.reporting.manager import ReportTemplate

custom_data/cache/temporarylate = ReportTemplate(
    data/cache/temporarylate_id="custom_business",
    name="商业分析模板",
    description="专为商业分析设计的报告模板",
    report_type=ReportType.ANALYTICAL,
    sections=["执行摘要", "市场分析", "财务表现", "风险评估", "建议措施"],
    variables={
        "company_name": "公司名称",
        "docs/analysis_period": "分析期间",
        "currency": "货币单位"
    }
)

# 注册自定义模板
manager.default_data/cache/temporarylates["custom_business"] = custom_data/cache/temporarylate
```

## 元数据管理

### 报告元数据结构
```python
metadata_fields = {
    "report_id": "唯一标识符",
    "title": "报告标题",
    "author": "作者",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "report_type": "报告类型",
    "status": "报告状态",
    "version": "版本号",
    "tags": ["标签列表"],
    "keywords": ["关键词列表"],
    "data_sources": ["数据源列表"],
    "word_count": "字数统计",
    "page_count": "页数估算"
}
```

### 元数据更新
```python
# 批量更新元数据
metadata_updates = {
    "status": ReportStatus.APPROVED.value,
    "tags": ["已批准", "正式发布", "2024"],
    "keywords": ["销售", "分析", "季度", "增长"],
    "version": "2.0"
}

manager.update_report(
    "session_001",
    "report_12345",
    metadata_updates=metadata_updates
)
```

## 导出格式说明

### HTML导出
```python
export_path = manager.export_report(
    session_id="session_001",
    report_id="report_12345",
    format=ExportFormat.HTML
)
# 生成带有样式的完整HTML文档
```

### PDF导出
```python
export_path = manager.export_report(
    session_id="session_001", 
    report_id="report_12345",
    format=ExportFormat.PDF
)
# 生成专业的PDF文档（需要weasyprint支持）
```

### Markdown导出
```python
export_path = manager.export_report(
    session_id="session_001",
    report_id="report_12345", 
    format=ExportFormat.MARKDOWN
)
# 生成易于编辑的Markdown格式
```

### JSON导出
```python
export_path = manager.export_report(
    session_id="session_001",
    report_id="report_12345",
    format=ExportFormat.JSON
)
# 生成结构化数据，便于程序处理
```

## 最佳实践

### 1. 报告组织策略
```python
# 按项目组织报告
project_reports = {
    "sales_docs/analysis_2024": {
        "Q1_report": "report_q1_2024",
        "Q2_report": "report_q2_2024", 
        "annual_summary": "report_annual_2024"
    },
    "customer_docs/analysis": {
        "segmentation": "report_customer_segments",
        "behavior": "report_customer_behavior"
    }
}

# 按时间组织报告
time_based_organization = {
    "daily": ["daily_reports_2024_*"],
    "weekly": ["weekly_summary_*"],
    "monthly": ["monthly_docs/analysis_*"],
    "quarterly": ["q*_2024_*"]
}
```

### 2. 版本控制策略
```python
# 版本命名规范
version_naming = {
    "major": "重大修改，如1.0 → 2.0",
    "minor": "功能新增，如1.0 → 1.1", 
    "patch": "小修小补，如1.0.0 → 1.0.1"
}

# 变更记录
change_log = [
    "v1.0 - 初始版本发布",
    "v1.1 - 添加图表和可视化",
    "v1.2 - 优化分析方法和结论",
    "v2.0 - 重构报告结构，添加执行摘要"
]
```

### 3. 标签和分类策略
```python
# 推荐的标签分类
recommended_tags = {
    "内容类型": ["分析", "总结", "预测", "建议"],
    "业务领域": ["销售", "市场", "财务", "运营"],
    "时间维度": ["日报", "周报", "月报", "季报", "年报"],
    "状态标识": ["草稿", "审核中", "已发布", "已归档"],
    "受众群体": ["管理层", "技术团队", "业务部门", "外部客户"]
}
```

## 错误处理

### 常见错误及处理
```python
# 报告不存在
try:
    report = manager.get_report("session_001", "nonexistent")
    if not report:
        print("报告不存在，请检查报告ID")
except Exception as e:
    print(f"获取报告时出错: {e}")

# 会话无效
reports = manager.list_reports("invalid_session")
if not reports:
    print("会话中没有报告或会话无效")

# 导出失败
try:
    export_path = manager.export_report(
        "session_001", 
        "report_12345",
        ExportFormat.PDF
    )
    if not export_path:
        print("导出失败，请检查格式支持和权限")
except Exception as e:
    print(f"导出过程中出错: {e}")
```

## 性能优化

### 大量报告处理
```python
# 批量操作优化
def batch_create_reports(session_id, report_data_list):
    """批量创建报告"""
    created_reports = []
    for report_data in report_data_list:
        try:
            metadata = create_new_report(
                session_id=session_id,
                **report_data
            )
            created_reports.append(metadata)
        except Exception as e:
            print(f"创建报告失败: {e}")
    return created_reports

# 分页查询
def get_reports_paginated(session_id, page=1, page_size=20):
    """分页获取报告列表"""
    all_reports = manager.list_reports(session_id)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return all_reports[start_idx:end_idx]
```

## API参考

### 主要类和方法

#### ReportManager
- `create_report()`: 创建新报告
- `get_report()`: 获取报告详情
- `list_reports()`: 列出会话报告
- `update_report()`: 更新报告
- `delete_report()`: 删除报告
- `export_report()`: 导出报告

#### 枚举类型
- `ReportType`: 报告类型枚举
- `ReportStatus`: 报告状态枚举  
- `ExportFormat`: 导出格式枚举

#### 数据类
- `ReportMetadata`: 报告元数据
- `ReportTemplate`: 报告模板
- `ReportVersion`: 报告版本

---
*文档版本: 1.0*
*最后更新: 2026-02-07*