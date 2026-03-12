"""配置提供者.

提供统一的配置访问接口.
"""

from __future__ import annotations

import os
from typing import Any, TypeVar, Generic

T = TypeVar("T")


class ConfigProvider:
    """配置提供者.

    提供类型安全的配置访问方法.

    Example:
        >>> config = ConfigProvider()
        >>> api_base = config.get_str("API_BASE", "http://localhost:48000/v1")
        >>> timeout = config.get_int("CODE_EXECUTION_TIMEOUT", 120)
    """

    def __init__(self, prefix: str = "DEEPANALYZE_"):
        """初始化配置提供者.

        Args:
            prefix: 环境变量前缀
        """
        self._prefix = prefix
        self._cache: dict[str, Any] = {}

    def _get_key(self, key: str) -> str:
        """获取完整的环境变量名."""
        if key.startswith(self._prefix):
            return key
        return f"{self._prefix}{key}"

    def get(self, key: str, default: T | None = None) -> str | T | None:
        """获取字符串配置值.

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值或默认值
        """
        env_key = self._get_key(key)
        return os.getenv(env_key, default)

    def get_str(self, key: str, default: str = "") -> str:
        """获取字符串配置值."""
        value = self.get(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置值."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置值."""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置值."""
        value = self.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def get_list(self, key: str, default: list[str] | None = None, separator: str = ",") -> list[str]:
        """获取列表配置值.

        Args:
            key: 配置键名
            default: 默认值
            separator: 分隔符

        Returns:
            字符串列表
        """
        value = self.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]

    def get_dict(self, key: str, default: dict[str, str] | None = None, item_separator: str = ",", kv_separator: str = "=") -> dict[str, str]:
        """获取字典配置值.

        Args:
            key: 配置键名
            default: 默认值
            item_separator: 项目分隔符
            kv_separator: 键值分隔符

        Returns:
            字符串字典
        """
        value = self.get(key)
        if value is None:
            return default or {}

        result = {}
        for item in value.split(item_separator):
            item = item.strip()
            if kv_separator in item:
                k, v = item.split(kv_separator, 1)
                result[k.strip()] = v.strip()
        return result

    # 预定义的配置属性

    @property
    def api_base(self) -> str:
        """API 基础 URL."""
        return self.get_str("VLLM_BASE_URL", "http://localhost:48000/v1")

    @property
    def api_key(self) -> str:
        """API 密钥."""
        return self.get_str("VLLM_API_KEY", "")

    @property
    def model_name(self) -> str:
        """模型名称."""
        return self.get_str("MODEL_NAME", "default")

    @property
    def workspace_dir(self) -> str:
        """工作空间目录."""
        return self.get_str("WORKSPACE_DIR", "data/sessions/active")

    @property
    def code_execution_timeout(self) -> int:
        """代码执行超时时间（秒）."""
        return self.get_int("CODE_EXECUTION_TIMEOUT", 120)

    @property
    def max_recursion_depth(self) -> int:
        """最大递归深度."""
        depth = self.get_int("MAX_DEPTH", 1)
        return max(0, min(depth, 3))

    @property
    def analysis_use_llm(self) -> bool:
        """分析是否使用 LLM."""
        return self.get_bool("ANALYSIS_USE_LLM", False)

    @property
    def report_use_llm(self) -> bool:
        """报告是否使用 LLM."""
        return self.get_bool("REPORT_USE_LLM", False)

    @property
    def graph_monitoring(self) -> bool:
        """是否启用图监控."""
        return self.get_bool("GRAPH_MONITORING", False)

    @property
    def trace_enabled(self) -> bool:
        """是否启用追踪."""
        return self.get_bool("TRACE_ENABLED", True)