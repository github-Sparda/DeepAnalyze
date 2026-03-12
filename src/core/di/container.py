"""依赖注入容器实现.

提供服务的注册、解析和管理功能.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, TypeVar, Generic, Optional
from functools import lru_cache

T = TypeVar("T")


class ServiceDescriptor(Generic[T]):
    """服务描述符."""

    def __init__(
        self,
        interface: type[T],
        implementation: type[T] | Callable[..., T],
        instance: T | None = None,
        singleton: bool = True,
        factory: Callable[..., T] | None = None,
    ):
        self.interface = interface
        self.implementation = implementation
        self.instance = instance
        self.singleton = singleton
        self.factory = factory
        self._lock = threading.Lock()

    def resolve(self, container: Container) -> T:
        """解析服务实例."""
        if self.singleton:
            if self.instance is None:
                with self._lock:
                    if self.instance is None:
                        self.instance = self._create_instance(container)
            return self.instance
        return self._create_instance(container)

    def _create_instance(self, container: Container) -> T:
        """创建服务实例."""
        if self.factory:
            return self.factory(container)
        if callable(self.implementation):
            return self.implementation()
        return self.implementation()


class Container:
    """依赖注入容器.

    用于管理服务的注册和解析.

    Example:
        >>> container = Container()
        >>> container.register_singleton(Config, AppConfig)
        >>> config = container.resolve(Config)
    """

    def __init__(self):
        self._services: dict[type, ServiceDescriptor] = {}
        self._lock = threading.RLock()

    def register(
        self,
        interface: type[T],
        implementation: type[T] | Callable[..., T],
        singleton: bool = True,
        factory: Callable[..., T] | None = None,
    ) -> Container:
        """注册服务.

        Args:
            interface: 服务接口类型
            implementation: 服务实现类型或工厂函数
            singleton: 是否为单例模式
            factory: 可选的工厂函数

        Returns:
            容器实例（支持链式调用）
        """
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                singleton=singleton,
                factory=factory,
            )
        return self

    def register_singleton(
        self,
        interface: type[T],
        implementation: type[T] | Callable[..., T],
        factory: Callable[..., T] | None = None,
    ) -> Container:
        """注册单例服务."""
        return self.register(interface, implementation, singleton=True, factory=factory)

    def register_transient(
        self,
        interface: type[T],
        implementation: type[T] | Callable[..., T],
        factory: Callable[..., T] | None = None,
    ) -> Container:
        """注册瞬态服务（每次解析创建新实例）."""
        return self.register(interface, implementation, singleton=False, factory=factory)

    def register_instance(self, interface: type[T], instance: T) -> Container:
        """注册已有实例作为单例服务."""
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=type(instance),
                instance=instance,
                singleton=True,
            )
        return self

    def resolve(self, interface: type[T]) -> T:
        """解析服务实例.

        Args:
            interface: 服务接口类型

        Returns:
            服务实例

        Raises:
            KeyError: 如果服务未注册
        """
        with self._lock:
            if interface not in self._services:
                raise KeyError(f"Service {interface.__name__} not registered")
            descriptor = self._services[interface]
        return descriptor.resolve(self)

    def try_resolve(self, interface: type[T]) -> T | None:
        """尝试解析服务实例.

        Args:
            interface: 服务接口类型

        Returns:
            服务实例，如果未注册则返回 None
        """
        try:
            return self.resolve(interface)
        except KeyError:
            return None

    def is_registered(self, interface: type) -> bool:
        """检查服务是否已注册."""
        with self._lock:
            return interface in self._services

    def build_provider(self) -> ServiceProvider:
        """构建服务提供者（冻结容器）."""
        return ServiceProvider(self._services.copy())


class ServiceProvider:
    """服务提供者（只读容器）."""

    def __init__(self, services: dict[type, ServiceDescriptor]):
        self._services = services

    def get_service(self, interface: type[T]) -> T | None:
        """获取服务实例."""
        descriptor = self._services.get(interface)
        if descriptor is None:
            return None
        return descriptor.resolve(Container())

    def get_required_service(self, interface: type[T]) -> T:
        """获取必需的服务实例."""
        service = self.get_service(interface)
        if service is None:
            raise KeyError(f"Service {interface.__name__} not found")
        return service


# 全局容器实例
_global_container: Container | None = None
_container_lock = threading.Lock()


def get_container() -> Container:
    """获取全局容器实例.

    Returns:
        全局容器实例

    Raises:
        RuntimeError: 如果容器未初始化
    """
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = Container()
    return _global_container


def init_container() -> Container:
    """初始化容器并注册默认服务.

    Returns:
        初始化后的容器实例
    """
    container = get_container()

    # 注册配置提供者
    from .config import ConfigProvider
    container.register_singleton(ConfigProvider, ConfigProvider)

    # 注册缓存服务
    from src.core.cache.smart_cache import SmartCache
    container.register_singleton(SmartCache, SmartCache)

    # 注册LLM客户端
    from src.core.orchestration.llm import LLMClient
    container.register_transient(LLMClient, LLMClient)

    return container