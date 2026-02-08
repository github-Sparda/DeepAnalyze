# 架构重构说明

## 统一API客户端设计

### 目标
创建一个统一的API客户端来简化所有外部服务调用，提高代码可维护性和一致性。

### 主要改进

1. **统一接口**
   - 封装所有OpenAI兼容的API调用
   - 提供一致的错误处理和重试机制
   - 标准化的参数处理

2. **核心功能**
   - `chat_completion()`: 统一的聊天补全接口
   - `upload_file()`: 文件上传功能
   - `download_file()`: 文件下载功能
   - `list_files()`: 文件列表查询
   - `prepare_messages()`: 标准化消息格式准备

3. **增强特性**
   - 自动重试机制（使用tenacity库）
   - 类型提示和文档字符串
   - 全局客户端实例管理
   - 错误信息标准化

### 使用示例

```python
from API.unified_client import get_api_client

# 获取客户端实例
client = get_api_client()

# 简单聊天
messages = [{"role": "user", "content": "分析这份数据"}]
response = client.chat_completion(messages)

# 文件操作
file_info = client.upload_file("data.csv")
files = client.list_files()

# 准备标准化消息
messages = client.prepare_messages(
    instruction="请分析数据趋势",
    file_ids=[file_info["id"]]
)
```

### 优势
1. **简化调用**: 所有API调用使用统一接口
2. **错误处理**: 内置重试和错误恢复机制
3. **类型安全**: 完整的类型提示支持
4. **易于维护**: 集中管理所有API交互逻辑
5. **向前兼容**: 不影响现有功能，逐步迁移

### 迁移计划
1. 保留现有API接口不变
2. 逐步将内部调用迁移到统一客户端
3. 最终替换分散的API调用代码