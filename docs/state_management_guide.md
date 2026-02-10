# 统一状态管理系统使用文档

## 概述
DeepAnalyze统一状态管理系统提供了会话级别的状态持久化、恢复和管理功能，支持多用户、多会话的并发访问。

## 核心特性

### 1. 会话管理
- 自动会话ID生成
- 会话元数据管理（创建时间、最后访问时间、用户ID、标签等）
- 会话生命周期管理（创建、查询、删除）

### 2. 状态持久化
- 内存缓存 + 磁盘持久化双重保障
- 自动序列化和反序列化
- 线程安全访问控制

### 3. 并发支持
- 内置线程锁机制
- 支持多线程并发访问
- 数据一致性保证

## 使用方法

### 基本使用

```python
from src/core.state.manager import StateManager

# 创建状态管理器
manager = StateManager()

# 创建新会话
session_id = manager.create_session(
    session_name="我的数据分析",
    user_id="user123",
    tags=["docs/analysis", "finance"]
)

# 获取会话状态
state = manager.get_state(session_id)

# 更新状态
updates = {
    "input_files": ["sales_data.csv"],
    "docs/analysis_results": "已完成趋势分析",
    "hypotheses": ["销售额呈上升趋势"]
}
success = manager.update_state(session_id, updates)

# 保存完整状态
full_state = manager.get_state(session_id)
manager.save_state(session_id, full_state)
```

### 便捷函数使用

```python
from src/core.state.manager import (
    create_new_session,
    get_session_state,
    update_session_state
)

# 创建会话
session_id = create_new_session(
    session_name="快速分析",
    tags=["quick"]
)

# 更新状态
success = update_session_state(session_id, {
    "progress": "50%",
    "current_step": "data_cleaning"
})

# 获取状态
state = get_session_state(session_id)
```

### 会话查询和管理

```python
# 列出所有会话
all_sessions = manager.list_sessions()

# 按用户查询
user_sessions = manager.list_sessions(user_id="user123")

# 按标签查询
docs/analysis_sessions = manager.list_sessions(tags=["docs/analysis"])

# 获取会话信息
session_info = manager.get_session_info(session_id)

# 删除会话
manager.delete_session(session_id)
```

## 状态结构

系统使用`OrchestrationState`类型定义状态结构，包含以下主要字段：

```python
{
    "session_id": str,           # 会话ID
    "run_id": str,              # 运行ID
    "data/sessions/active_dir": str,       # 工作目录
    "input_files": list,        # 输入文件列表
    "plan": str,                # 分析计划
    "hypotheses": list,         # 假设列表
    "docs/analysis_results": str,    # 分析结果
    "report": str,              # 生成报告
    "artifacts": list,          # 生成的工件
    "visualizations": list,     # 可视化结果
    "errors": list,             # 错误信息
    # ... 更多字段
}
```

## 最佳实践

### 1. 会话命名
```python
# 推荐：使用描述性名称
session_id = manager.create_session(
    session_name="2024年Q1销售数据分析",
    tags=["quarterly", "sales", "2024"]
)

# 不推荐：使用无意义名称
session_id = manager.create_session(session_name="分析1")
```

### 2. 状态更新
```python
# 推荐：批量更新
updates = {
    "current_step": "data_docs/analysis",
    "progress": "75%",
    "last_updated": datetime.now().isoformat()
}
manager.update_state(session_id, updates)

# 不推荐：频繁的小更新
manager.update_state(session_id, {"progress": "70%"})
manager.update_state(session_id, {"progress": "75%"})
```

### 3. 错误处理
```python
# 检查操作结果
if not manager.update_state(session_id, updates):
    print("状态更新失败")
    # 处理错误情况

# 验证会话存在
state = manager.get_state(session_id)
if state is None:
    print("会话不存在")
    # 创建新会话或处理错误
```

## 性能优化

### 1. 缓存机制
系统内置内存缓存，频繁访问的会话状态会缓存在内存中，提高访问速度。

### 2. 并发访问
使用线程锁确保并发访问的安全性，支持多线程同时操作不同会话。

### 3. 持久化策略
- 状态变化时自动保存到磁盘
- 支持从磁盘恢复状态
- 元数据单独存储，提高查询效率

## 故障排除

### 常见问题

1. **导入错误**
```bash
# 确保正确的PYTHONPATH设置
export PYTHONPATH=/path/to/DeepAnalyze:$PYTHONPATH
```

2. **权限问题**
```bash
# 确保工作目录有写权限
chmod 755 data/sessions/active/
```

3. **并发冲突**
```python
# 使用try-except处理并发异常
try:
    manager.update_state(session_id, updates)
except Exception as e:
    print(f"更新失败: {e}")
```

## API参考

### StateManager类

#### `create_session(session_id=None, user_id=None, session_name=None, tags=None)`
创建新会话

#### `get_state(session_id)`
获取会话状态

#### `save_state(session_id, state)`
保存会话状态

#### `update_state(session_id, updates)`
更新会话状态

#### `delete_session(session_id)`
删除会话

#### `list_sessions(user_id=None, tags=None)`
列出会话

#### `get_session_info(session_id)`
获取会话信息

### 便捷函数

- `create_new_session()`: 创建新会话
- `get_session_state()`: 获取会话状态  
- `save_session_state()`: 保存会话状态
- `update_session_state()`: 更新会话状态
- `get_state_manager()`: 获取全局管理器实例

---
*文档版本: 1.0*
*最后更新: 2026-02-07*