"""依赖注入容器模块.

提供统一的依赖管理和服务定位功能.
"""

from .container import Container, get_container, init_container
from .config import ConfigProvider

__all__ = [
    "Container",
    "get_container",
    "init_container",
    "ConfigProvider",
]