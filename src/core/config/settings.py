"""Pydantic BaseSettings 配置管理.

使用 Pydantic BaseSettings 统一管理所有配置.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeepAnalyzeSettings(BaseSettings):
    """DeepAnalyze 全局配置.
    
    所有配置项都可以通过环境变量设置，前缀为 DEEPANALYZE_
    """
    
    model_config = SettingsConfigDict(
        env_prefix="DEEPANALYZE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # API 配置
    vllm_base_url: str = Field(
        default="http://localhost:48000/v1",
        description="VLLM API 基础 URL"
    )
    vllm_api_key: str = Field(
        default="",
        description="VLLM API 密钥"
    )
    model_name: str = Field(
        default="default",
        description="模型名称"
    )
    
    # 工作空间配置
    workspace_dir: str = Field(
        default="data/sessions/active",
        description="工作空间目录"
    )
    
    # 执行配置
    code_execution_timeout: int = Field(
        default=120,
        ge=1,
        le=600,
        description="代码执行超时时间（秒）"
    )
    max_recursion_depth: int = Field(
        default=1,
        ge=0,
        le=3,
        description="最大递归深度"
    )
    
    # 功能开关
    analysis_use_llm: bool = Field(
        default=False,
        description="分析是否使用 LLM"
    )
    report_use_llm: bool = Field(
        default=False,
        description="报告是否使用 LLM"
    )
    graph_monitoring: bool = Field(
        default=False,
        description="是否启用图监控"
    )
    trace_enabled: bool = Field(
        default=True,
        description="是否启用追踪"
    )
    
    # 报告配置
    custom_line_summary_days: int = Field(
        default=7,
        description="自定义行摘要天数"
    )
    custom_line_promo_min_runs: int = Field(
        default=3,
        description="自定义行晋升最小运行次数"
    )
    custom_line_promo_min_success: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="自定义行晋升最小成功率"
    )
    
    # 执行配置
    execution_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="执行最大重试次数"
    )
    
    # 路径 C 配置
    path_c_conflict_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="路径 C 冲突阈值"
    )
    
    @property
    def api_base(self) -> str:
        """兼容旧代码的 api_base 属性."""
        return self.vllm_base_url


@lru_cache()
def get_settings() -> DeepAnalyzeSettings:
    """获取全局配置实例（单例）.
    
    Returns:
        DeepAnalyzeSettings 实例
    """
    return DeepAnalyzeSettings()


def reset_settings() -> None:
    """重置配置实例（用于测试）.
    
    清除缓存，使下次调用 get_settings() 创建新实例.
    """
    get_settings.cache_clear()


def to_config_dict(self) -> dict:
    """将设置转换为字典.
    
    Returns:
        配置字典
    """
    return self.model_dump()


# 将方法添加到类
DeepAnalyzeSettings.to_config_dict = to_config_dict

# 导出兼容旧代码的变量
settings = get_settings()
