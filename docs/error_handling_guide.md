# 错误处理和恢复系统使用文档

## 概述
DeepAnalyze错误处理系统提供全面的错误管理、自动恢复和监控功能，确保系统稳定性和可靠性。

## 核心特性

### 1. 多级错误分类
- **严重程度**: LOW, MEDIUM, HIGH, CRITICAL
- **错误类别**: VALIDATION, EXECUTION, NETWORK, FILESYSTEM, MEMORY, TIMEOUT, CONFIGURATION, EXTERNAL_src/api, UNKNOWN

### 2. 自动恢复机制
- 智能恢复策略匹配
- 指数退避重试算法
- 错误隔离和防护

### 3. 完整监控体系
- 实时错误统计
- 详细的错误日志
- JSON格式错误报告导出

### 4. 并发安全保障
- 线程安全的错误处理
- 原子性操作保证
- 资源竞争预防

## 使用方法

### 基本错误处理

```python
from src/core.error.handler import ErrorHandler, ErrorSeverity, ErrorCategory

# 创建错误处理器
handler = ErrorHandler()

# 处理各种错误
try:
    # 网络操作
    raise ConnectionError("src/api连接失败")
except Exception as e:
    error_info = handler.handle_error(
        e,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.NETWORK,
        context={"endpoint": "/api/data"}
    )
    print(f"错误ID: {error_info.error_id}")

# 查看错误统计
stats = handler.get_error_statistics()
print(f"总错误数: {stats['total_errors']}")
print(f"按类别分布: {stats['categories']}")
```

### 安全执行模式

```python
from src/core.error.handler import safe_execute

def risky_operation(x, y):
    """可能出错的操作"""
    return x / y

# 安全执行带默认值
result = safe_execute(
    risky_operation, 
    10, 0, 
    fallback_value=0,  # 除零时返回0
    max_retries=3      # 最多重试3次
)
print(f"结果: {result}")  # 输出: 结果: 0
```

### 装饰器使用

```python
from src/core.error.handler import safe_operation, critical_operation

@safe_operation(max_retries=3, fallback_value="默认结果")
def unreliable_api_call():
    """不稳定的src/api调用"""
    import random
    if random.random() < 0.5:
        raise ConnectionError("网络不稳定")
    return "成功"

@critical_operation
def important_calculation(data):
    """关键计算，错误不能被忽略"""
    if not data:
        raise ValueError("数据不能为空")
    return sum(data)

# 使用装饰器函数
result1 = unreliable_api_call()  # 自动重试和恢复
try:
    result2 = important_calculation([])  # 错误会被重新抛出
except ValueError as e:
    print(f"关键操作失败: {e}")
```

### 自定义恢复策略

```python
from src/core.error.handler import ErrorHandler, RecoveryStrategy, ErrorCategory, ErrorSeverity

def custom_recovery_function(error_info):
    """自定义恢复逻辑"""
    print(f"正在处理错误: {error_info.error_id}")
    # 实现具体的恢复逻辑
    return True  # 返回恢复是否成功

# 注册自定义策略
handler = ErrorHandler()
custom_strategy = RecoveryStrategy(
    name="custom_db_recovery",
    description="数据库连接恢复策略",
    applicable_categories=[ErrorCategory.EXTERNAL_src/api],
    applicable_severities=[ErrorSeverity.MEDIUM, ErrorSeverity.HIGH],
    max_atdata/cache/temporaryts=3,
    retry_delay=5.0,
    recovery_function=custom_recovery_function
)

handler.register_recovery_strategy("db_recovery", custom_strategy)
```

## 错误报告

### 导出错误报告

```python
# 导出详细的错误报告
success = handler.export_error_report("error_report.json")
if success:
    print("错误报告已生成")

# 清理历史错误
handler.clear_error_history(older_than_hours=24)  # 清除24小时前的错误
```

### 错误报告结构

```json
{
  "generated_at": "2026-02-07T23:11:14.448217",
  "statistics": {
    "total_errors": 15,
    "categories": {
      "network": 5,
      "execution": 8,
      "filesystem": 2
    },
    "severities": {
      "medium": 12,
      "high": 3
    },
    "recovery": {
      "successful": 8,
      "failed": 2,
      "atdata/cache/temporaryts": 15
    }
  },
  "recent_errors": [
    {
      "id": "err_1770477074447116_4785",
      "timestamp": "2026-02-07T23:11:14.447116",
      "severity": "medium",
      "category": "unknown",
      "type": "ValueError",
      "message": "值错误 0",
      "recovery_atdata/cache/temporaryts": 1,
      "recovery_successful": true
    }
  ]
}
```

## 最佳实践

### 1. 错误分类准则

```python
# 正确的严重程度选择
ErrorSeverity.LOW      # 用户输入小错误，可自动修正
ErrorSeverity.MEDIUM   # 影响部分功能，但系统可继续运行
ErrorSeverity.HIGH     # 影响主要功能，需要人工干预
ErrorSeverity.CRITICAL # 系统级错误，可能导致崩溃
```

### 2. 上下文信息提供

```python
# 提供丰富的上下文信息
context = {
    "function": "analyze_dataset",
    "dataset_name": "sales_data_2024",
    "row_count": 10000,
    "operation": "data_cleaning",
    "user_id": "user123"
}
```

### 3. 重试策略设置

```python
# 根据操作类型设置合适的重试次数
safe_execute(api_call, max_retries=5)        # 网络操作，多次重试
safe_execute(file_operation, max_retries=2)  # 文件操作，少量重试
safe_execute(calculation, max_retries=0)     # 计算操作，不重试
```

## 系统集成

### 在现有代码中集成

```python
# 替换原有的try-except块
# 原代码
try:
    result = some_operation()
except Exception as e:
    print(f"Error: {e}")
    return None

# 新代码
from src/core.error.handler import safe_execute

result = safe_execute(some_operation, fallback_value=None)
```

### 监控和告警

```python
def check_system_health():
    """定期检查系统健康状态"""
    handler = get_error_handler()
    stats = handler.get_error_statistics()
    
    # 设置告警阈值
    if stats.get('total_errors', 0) > 100:
        send_alert("错误数量过多")
    
    # 检查关键错误比例
    critical_errors = stats.get('severities', {}).get('critical', 0)
    if critical_errors > 10:
        send_alert("检测到关键错误")

# 定期执行健康检查
import schedule
schedule.every(30).minutes.do(check_system_health)
```

## 故障排除

### 常见问题

1. **导入错误**
```bash
# 确保正确的Python路径
export PYTHONPATH=/path/to/DeepAnalyze:$PYTHONPATH
```

2. **日志级别设置**
```python
import logging
logging.basicConfig(level=logging.WARNING)  # 减少日志输出
```

3. **性能优化**
```python
# 限制错误历史大小
handler.max_error_history = 500  # 默认1000
```

## src/api参考

### ErrorHandler类

#### `handle_error(error, severity, category, context, recoverable)`
处理错误并尝试自动恢复

#### `get_error_statistics()`
获取错误统计信息

#### `export_error_report(filepath)`
导出错误报告到JSON文件

#### `clear_error_history(older_than_hours)`
清理错误历史

#### `register_recovery_strategy(name, strategy)`
注册自定义恢复策略

### 便捷函数

- `safe_execute()`: 安全执行函数
- `handle_exception()`: 快速处理异常
- `get_error_handler()`: 获取全局错误处理器

### 装饰器

- `@safe_operation`: 安全操作装饰器
- `@critical_operation`: 关键操作装饰器

---
*文档版本: 1.0*
*最后更新: 2026-02-07*