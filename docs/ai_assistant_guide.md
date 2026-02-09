# AI助手增强功能使用文档

## 概述
DeepAnalyze增强版AI助手提供了智能化的对话体验，具备上下文理解、意图识别、记忆管理等功能。

## 核心特性

### 1. 智能意图识别
- 自动识别6种主要意图类型
- 提供置信度评分
- 支持中英文混合识别

### 2. 上下文管理
- 短期/长期/混合上下文模式
- 智能上下文压缩和优化
- 跨会话记忆保持

### 3. 记忆系统
- 多类型记忆存储（对话、事实、偏好、技能、上下文）
- 智能记忆搜索和检索
- 重要性评分和自动清理

### 4. 多样化响应风格
- 分析型、技术型、执行型、对话型四种风格
- 根据意图自动选择合适风格
- 支持用户偏好设置

## 使用方法

### 基本对话

```python
from src/core.assistant.engine import chat_with_assistant, ContextMode

# 简单对话
response = chat_with_assistant(
    session_id="user_session_123",
    message="请分析这份销售数据"
)

print(f"助手回复: {response['content']}")
print(f"识别意图: {response['intent']}")
print(f"置信度: {response['confidence']:.2f}")
```

### 高级用法

```python
from src/core.assistant.engine import (
    AIAssistantEngine,
    ContextMode,
    ResponseStyle
)

# 创建助手引擎
engine = AIAssistantEngine()

# 使用特定上下文模式和响应风格
response = engine.process_message(
    session_id="advanced_session",
    user_message="帮我生成数据分析代码",
    context_mode=ContextMode.LONG_TERM,
    style_preference=ResponseStyle.TECHNICAL
)
```

### 上下文管理

```python
from src/core.assistant.context_manager import ContextManager, MemoryType

cm = ContextManager()

# 添加消息到上下文
cm.add_message("session_123", "user", "我想分析销售趋势")

# 添加记忆
cm.add_memory(
    "session_123",
    MemoryType.PREFERENCE,
    "preferred_chart_type",
    "折线图",
    importance_score=0.8
)

# 搜索相关记忆
memories = cm.search_memories(
    "session_123",
    query="分析",
    memory_types=[MemoryType.PREFERENCE, MemoryType.CONTEXTUAL]
)
```

## 意图类型详解

### DATA_ANALYSIS (数据分析)
```python
# 触发关键词: 分析, 统计, 趋势, 相关性, 回归
response = chat_with_assistant("session_123", "分析销售数据的趋势")
# 返回详细的分析方法和步骤建议
```

### CODE_GENERATION (代码生成)
```python
# 触发关键词: 代码, 编程, python, 脚本
response = chat_with_assistant("session_123", "生成处理CSV的Python代码")
# 返回完整可运行的代码示例
```

### VISUALIZATION (可视化)
```python
# 触发关键词: 图表, 可视化, 绘图
response = chat_with_assistant("session_123", "创建销售趋势图表")
# 返回图表类型建议和实现方法
```

### REPORT_GENERATION (报告生成)
```python
# 触发关键词: 报告, 文档, 总结, 结论
response = chat_with_assistant("session_123", "生成季度分析报告")
# 返回报告结构和核心内容建议
```

### HELP_REQUEST (帮助请求)
```python
# 触发关键词: 怎么, 如何, 帮助, 教程
response = chat_with_assistant("session_123", "怎么上传数据文件？")
# 返回清晰的操作指导
```

### GENERAL_CHAT (一般聊天)
```python
# 其他类型的对话
response = chat_with_assistant("session_123", "今天天气怎么样？")
# 返回友好的通用回应
```

## 响应风格说明

### ANALYTICAL (分析型)
- 详细的方法论和步骤说明
- 专业的统计和分析术语
- 适合深入的技术讨论

### TECHNICAL (技术型)
- 具体的代码实现和参数说明
- 技术细节和最佳实践
- 适合开发人员和工程师

### EXECUTIVE (执行型)
- 高层视角的总结和建议
- 商业价值和行动导向
- 适合管理层和决策者

### CONVERSATIONAL (对话型)
- 友好自然的语言表达
- 循序渐进的解释说明
- 适合初学者和一般用户

## 记忆系统使用

### 记忆类型
```python
from src/core.assistant.context_manager import MemoryType

# 对话历史记忆
MemoryType.CONVERSATION

# 事实信息记忆
MemoryType.FACT

# 用户偏好记忆
MemoryType.PREFERENCE

# 技能知识记忆
MemoryType.SKILL

# 上下文信息记忆
MemoryType.CONTEXTUAL
```

### 记忆管理示例
```python
# 存储用户偏好
cm.add_memory(
    session_id,
    MemoryType.PREFERENCE,
    "report_style",
    "学术风格",
    importance_score=0.9
)

# 存储分析事实
cm.add_memory(
    session_id,
    MemoryType.FACT,
    "data_columns",
    ["date", "sales", "region"],
    importance_score=0.8
)

# 搜索相关记忆
relevant_memories = cm.search_memories(
    session_id,
    "报告",
    [MemoryType.PREFERENCE]
)
```

## 性能优化

### 上下文长度控制
```python
# 设置最大上下文长度
context = cm.create_conversation_context(
    session_id,
    max_context_length=8000  # token数限制
)

# 系统会自动压缩和优化长上下文
```

### 批量处理
```python
# 处理多个消息
messages = ["消息1", "消息2", "消息3"]
responses = []

for msg in messages:
    response = chat_with_assistant(session_id, msg)
    responses.append(response)
```

## 错误处理

### 异常处理
```python
try:
    response = chat_with_assistant(session_id, user_message)
    if 'error' in response:
        print(f"处理出错: {response['error']}")
        # 处理错误情况
except Exception as e:
    print(f"系统错误: {e}")
    # 回退处理逻辑
```

### 会话管理
```python
# 清除会话上下文
success = cm.clear_context(session_id)
if success:
    print("会话上下文已清除")
```

## 最佳实践

### 1. 会话管理
```python
# 为每个用户创建独立会话
session_id = f"user_{user_id}_session_{timestamp}"

# 定期清理过期会话
# 可以基于最后访问时间清理
```

### 2. 消息设计
```python
# 提供清晰具体的请求
good_message = "请分析2024年Q1销售数据，重点关注北区和南区的业绩对比"
bad_message = "分析数据"

# 包含必要上下文信息
complete_message = "基于之前上传的sales_2024.csv文件，分析各产品线的销售趋势"
```

### 3. 记忆优化
```python
# 合理设置重要性评分
# 高频使用: 0.8-0.9
# 中等重要: 0.5-0.7
# 低重要性: 0.1-0.4

# 定期清理低价值记忆
# 系统会自动清理，也可手动调用
```

## src/api参考

### 主要类和函数

#### AIAssistantEngine
- `process_message()`: 处理用户消息
- `chat_with_assistant()`: 便捷对话函数

#### ContextManager
- `create_conversation_context()`: 创建对话上下文
- `add_message()`: 添加消息
- `get_context_messages()`: 获取格式化消息
- `add_memory()`: 添加记忆
- `search_memories()`: 搜索记忆

#### 枚举类型
- `IntentType`: 意图类型
- `ResponseStyle`: 响应风格
- `ContextMode`: 上下文模式
- `MemoryType`: 记忆类型

---
*文档版本: 1.0*
*最后更新: 2026-02-07*