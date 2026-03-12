"""测试依赖注入功能.

验证 DI 容器和配置提供者是否按预期执行.
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.di import Container, ConfigProvider, get_container, init_container


def test_container_basic():
    """测试容器基本功能."""
    print("测试容器基本功能...")

    container = Container()

    # 注册单例服务
    container.register_singleton(ConfigProvider, ConfigProvider)

    # 解析服务
    config1 = container.resolve(ConfigProvider)
    config2 = container.resolve(ConfigProvider)

    # 验证单例
    assert config1 is config2, "单例服务应该返回同一实例"

    print("  ✓ 容器基本功能测试通过")


def test_container_transient():
    """测试瞬态服务."""
    print("测试瞬态服务...")

    container = Container()

    # 注册瞬态服务
    class TestService:
        pass

    container.register_transient(TestService, TestService)

    # 解析服务
    service1 = container.resolve(TestService)
    service2 = container.resolve(TestService)

    # 验证瞬态
    assert service1 is not service2, "瞬态服务应该返回不同实例"

    print("  ✓ 瞬态服务测试通过")


def test_container_factory():
    """测试工厂函数."""
    print("测试工厂函数...")

    container = Container()

    # 使用工厂函数注册
    def create_config(container):
        return ConfigProvider(prefix="TEST_")

    container.register_singleton(ConfigProvider, ConfigProvider, factory=create_config)

    # 解析服务
    config = container.resolve(ConfigProvider)
    assert isinstance(config, ConfigProvider), "应该返回 ConfigProvider 实例"

    print("  ✓ 工厂函数测试通过")


def test_config_provider():
    """测试配置提供者."""
    print("测试配置提供者...")

    # 设置测试环境变量
    os.environ["TEST_API_BASE"] = "http://test.example.com"
    os.environ["TEST_TIMEOUT"] = "60"
    os.environ["TEST_ENABLED"] = "true"
    os.environ["TEST_LIST"] = "a,b,c"

    config = ConfigProvider(prefix="TEST_")

    # 测试字符串
    assert config.get_str("API_BASE") == "http://test.example.com"

    # 测试整数
    assert config.get_int("TIMEOUT") == 60

    # 测试布尔
    assert config.get_bool("ENABLED") is True

    # 测试列表
    assert config.get_list("LIST") == ["a", "b", "c"]

    # 测试默认值
    assert config.get_str("NOT_EXIST", "default") == "default"
    assert config.get_int("NOT_EXIST", 100) == 100
    assert config.get_bool("NOT_EXIST", False) is False

    # 清理环境变量
    del os.environ["TEST_API_BASE"]
    del os.environ["TEST_TIMEOUT"]
    del os.environ["TEST_ENABLED"]
    del os.environ["TEST_LIST"]

    print("  ✓ 配置提供者测试通过")


def test_global_container():
    """测试全局容器."""
    print("测试全局容器...")

    # 获取全局容器
    container1 = get_container()
    container2 = get_container()

    # 验证是同一实例
    assert container1 is container2, "全局容器应该是单例"

    # 初始化容器
    init_container()

    # 验证服务已注册
    assert container1.is_registered(ConfigProvider), "ConfigProvider 应该已注册"

    # 解析配置
    config = container1.resolve(ConfigProvider)
    assert isinstance(config, ConfigProvider), "应该返回 ConfigProvider 实例"

    print("  ✓ 全局容器测试通过")


def test_config_properties():
    """测试配置属性."""
    print("测试配置属性...")

    config = ConfigProvider()

    # 测试属性访问
    assert isinstance(config.api_base, str), "api_base 应该是字符串"
    assert isinstance(config.api_key, str), "api_key 应该是字符串"
    assert isinstance(config.model_name, str), "model_name 应该是字符串"
    assert isinstance(config.workspace_dir, str), "workspace_dir 应该是字符串"
    assert isinstance(config.code_execution_timeout, int), "code_execution_timeout 应该是整数"
    assert isinstance(config.max_recursion_depth, int), "max_recursion_depth 应该是整数"
    assert isinstance(config.analysis_use_llm, bool), "analysis_use_llm 应该是布尔值"
    assert isinstance(config.report_use_llm, bool), "report_use_llm 应该是布尔值"
    assert isinstance(config.graph_monitoring, bool), "graph_monitoring 应该是布尔值"
    assert isinstance(config.trace_enabled, bool), "trace_enabled 应该是布尔值"

    # 测试递归深度范围限制
    os.environ["DEEPANALYZE_MAX_DEPTH"] = "10"
    config2 = ConfigProvider()
    assert config2.max_recursion_depth == 3, "递归深度应该被限制在 3"
    del os.environ["DEEPANALYZE_MAX_DEPTH"]

    os.environ["DEEPANALYZE_MAX_DEPTH"] = "-1"
    config3 = ConfigProvider()
    assert config3.max_recursion_depth == 0, "递归深度应该被限制在 0"
    del os.environ["DEEPANALYZE_MAX_DEPTH"]

    print("  ✓ 配置属性测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试依赖注入功能")
    print("=" * 60)

    tests = [
        test_container_basic,
        test_container_transient,
        test_container_factory,
        test_config_provider,
        test_global_container,
        test_config_properties,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)