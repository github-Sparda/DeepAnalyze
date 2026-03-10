# DeepAnalyze 配置项说明

## 📁 配置文件位置
- **主配置**: `/home/huangzw/Project/DeepAnalyze/.env`
- **src/api配置**: `/home/huangzw/Project/DeepAnalyze/src/api/config.py`

## ⚙️ 核心配置项

### LLM相关配置
```bash
# 必需配置
DEEPANALYZE_VLLM_API_KEY=your-api-key          # API密钥
DEEPANALYZE_VLLM_BASE_URL=https://api.data/examples.com/v1  # API地址
DEEPANALYZE_MODEL_NAME=model-name              # 模型名称

# 可选配置
DEFAULT_MODEL=gpt-4                            # 默认模型
```

### AI流程控制配置
```bash
# 编排系统开关
DEEPANALYZE_USE_ORCHESTRATOR=0                 # 0=禁用完整AI流程, 1=启用
DEEPANALYZE_MAX_DEPTH=1                        # 最大递归深度 (0-3)
DEEPANALYZE_FORCE_ROUNDS=1                     # 强制至少执行 N 轮（不超过 MAX_DEPTH）

# 执行控制
DEEPANALYZE_CODEGEN_CONCURRENCY=2              # 代码生成并发数
DEEPANALYZE_EXECUTION_CONCURRENCY=1            # 执行并发数
DEEPANALYZE_EXECUTION_MAX_RETRIES=2            # 最大重试次数
DEEPANALYZE_PATHC_CONFLICT_THRESHOLD=0.3       # 双路径冲突触发 Path-C 裁决阈值
```

### 报告和可视化配置
```bash
# 报告设置
DEEPANALYZE_REPORT_FORMAT=html                 # 报告格式
DEEPANALYZE_REPORT_LANGUAGE=zh                 # 报告语言
DEEPANALYZE_REPORT_EXPORT_MODE=html_convert    # 导出模式

# 可视化设置
DEEPANALYZE_VISUAL_STYLE=academic              # 图表风格
DEEPANALYZE_VISUAL_INTERACTIVE=0               # 交互式图表开关
```

### 系统功能开关
```bash
# 监控和追踪
DEEPANALYZE_GRAPH_MONITORING=0                 # 图形监控
DEEPANALYZE_TRACE_ENABLED=1                    # 追踪功能
DEEPANALYZE_DATA_QUALITY_ENABLED=1             # 数据质量检查

# 元数据和安全性
DEEPANALYZE_REPRO_METADATA_ENABLED=1           # 可重现性元数据
DEEPANALYZE_ALLOW_ABSOLUTE_IO=0                # 绝对路径IO权限
```

## 🔄 配置修改方法

### 1. 修改.env文件（推荐）
```bash
# 编辑配置文件
nano /home/huangzw/Project/DeepAnalyze/.env

# 修改后重启服务使配置生效
./scripts/restart_services.sh
```

### 2. 临时环境变量
```bash
# 临时修改（当前会话有效）
export DEEPANALYZE_USE_ORCHESTRATOR=1
python your_script.py
```

### 3. 程序内动态修改
```python
import os
os.environ['DEEPANALYZE_USE_ORCHESTRATOR'] = '1'
# 重新导入配置模块
import importlib
import src/api.config
importlib.reload(src/api.config)
```

## 🎯 常见配置场景

### 场景1：启用完整AI分析流程
```bash
DEEPANALYZE_USE_ORCHESTRATOR=1
DEEPANALYZE_MAX_DEPTH=3
```

### 场景2：仅使用传统统计分析
```bash
DEEPANALYZE_USE_ORCHESTRATOR=0
DEEPANALYZE_MAX_DEPTH=1
```

### 场景3：调试和开发模式
```bash
DEEPANALYZE_DEBUG_STREAM=1
DEEPANALYZE_TRACE_ENABLED=1
DEEPANALYZE_GRAPH_MONITORING=1
```

### 场景4：高性能生产环境
```bash
DEEPANALYZE_CODEGEN_CONCURRENCY=4
DEEPANALYZE_EXECUTION_CONCURRENCY=2
DEEPANALYZE_EXECUTION_MAX_RETRIES=1
```

## 🔧 配置验证

修改配置后可以通过以下方式验证：

```bash
# 检查环境变量
python -c "import os; print(os.getenv('DEEPANALYZE_USE_ORCHESTRATOR'))"

# 检查配置加载
python -c "from src/api.config import USE_ORCHESTRATOR; print(USE_ORCHESTRATOR)"

# 测试LLM连接
python -c "
from src/api.config import DEEPANALYZE_VLLM_API_KEY, VLLM_BASE_URL
import requests
response = requests.get(f'{VLLM_BASE_URL}/models', 
                       headers={'Authorization': f'Bearer {DEEPANALYZE_VLLM_API_KEY}'})
print('连接状态:', '成功' if response.status_code == 200 else '失败')
"
```

## 🧾 新增运行产物说明（与配置联动）

开启编排分析后，可重点查看：

- `meta/completion_validation.json`：完成态校验（失败时报告会降级）
- `meta/plan_validation/file_summary_fallback.json`：DataIngest 降级追踪（可选）
- `meta/plan_validation/report_llm_fallback.json`：ReportAssembly 降级追踪（可选）

## Runtime Config Files (新增)

可选配置文件：

- `config/analysis_runtime.json`
- `<session_dir>/config/analysis_runtime.json`
- `config/hypothesis_profile_registry.json`
- `<session_dir>/config/hypothesis_profile_registry.json`

用途：

- `analysis_runtime.json`
  - `group_column_candidates`
  - `group_selection.reference_labels`
  - `group_selection.preferred_case_labels`
  - `group_selection.max_top_groups`
  - `required_result_artifacts`
- `hypothesis_profile_registry.json`
  - 自定义假设类型的标题、默认假设文本、证据 claim、方法族、默认图表绑定
- `result/path_adjudication.json`：冲突裁决结果（受 `DEEPANALYZE_PATHC_CONFLICT_THRESHOLD` 影响）
- `result/ml_repro_bundle_index.json`：预测类假设复现包索引（缺失会触发 gate 降级）
