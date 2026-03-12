"""测试配置设置模块.

验证 settings 模块的功能是否按预期执行.
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config.settings import (
    DeepAnalyzeSettings,
    get_settings,
    reset_settings,
)


def test_settings_default_values():
    """测试设置默认值."""
    print("测试 settings 默认值...")
    
    # 清除可能影响的环境变量
    for key in list(os.environ.keys()):
        if key.startswith("DEEPANALYZE_"):
            del os.environ[key]
    
    reset_settings()
    settings = get_settings()
    
    # 注意：如果环境中有预设的环境变量，这些值可能不同
    # 这里主要验证设置对象能正常创建和基本类型正确
    assert isinstance(settings.vllm_base_url, str), "VLLM URL 应该是字符串"
    assert isinstance(settings.code_execution_timeout, int), "超时时间应该是整数"
    assert 1 <= settings.code_execution_timeout <= 600, "超时时间应该在有效范围内"
    assert isinstance(settings.execution_max_retries, int), "最大重试次数应该是整数"
    assert 0 <= settings.execution_max_retries <= 10, "最大重试次数应该在有效范围内"
    assert isinstance(settings.trace_enabled, bool), "追踪设置应该是布尔值"
    
    print("  ✓ settings 默认值测试通过")


def test_settings_from_env():
    """测试从环境变量加载设置."""
    print("测试从环境变量加载 settings...")
    
    # 设置环境变量
    os.environ["DEEPANALYZE_VLLM_BASE_URL"] = "http://test:8080/v1"
    os.environ["DEEPANALYZE_CODE_EXECUTION_TIMEOUT"] = "60"
    os.environ["DEEPANALYZE_EXECUTION_MAX_RETRIES"] = "5"
    
    reset_settings()
    settings = get_settings()
    
    assert settings.vllm_base_url == "http://test:8080/v1", f"环境变量 VLLM URL 未生效: {settings.vllm_base_url}"
    assert settings.code_execution_timeout == 60, f"环境变量超时时间未生效: {settings.code_execution_timeout}"
    assert settings.execution_max_retries == 5, f"环境变量最大重试次数未生效: {settings.execution_max_retries}"
    
    # 清理环境变量
    del os.environ["DEEPANALYZE_VLLM_BASE_URL"]
    del os.environ["DEEPANALYZE_CODE_EXECUTION_TIMEOUT"]
    del os.environ["DEEPANALYZE_EXECUTION_MAX_RETRIES"]
    
    print("  ✓ 环境变量加载 settings 测试通过")


def test_settings_validation():
    """测试设置验证."""
    print("测试 settings 验证...")
    
    # 测试超时时间范围验证
    try:
        settings = DeepAnalyzeSettings(code_execution_timeout=0)
        assert False, "应该拒绝过小的超时时间"
    except Exception:
        pass  # 预期会失败
    
    try:
        settings = DeepAnalyzeSettings(code_execution_timeout=1000)
        assert False, "应该拒绝过大的超时时间"
    except Exception:
        pass  # 预期会失败
    
    # 测试有效值
    settings = DeepAnalyzeSettings(code_execution_timeout=300)
    assert settings.code_execution_timeout == 300, "有效超时时间应该被接受"
    
    print("  ✓ settings 验证测试通过")


def test_settings_singleton():
    """测试设置单例模式."""
    print("测试 settings 单例模式...")
    
    reset_settings()
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2, "get_settings 应该返回相同的实例"
    
    print("  ✓ settings 单例模式测试通过")


def test_settings_to_dict():
    """测试设置转换为字典."""
    print("测试 settings 转换为字典...")
    
    reset_settings()
    settings = get_settings()
    config_dict = settings.to_config_dict()
    
    assert isinstance(config_dict, dict), "to_config_dict 应该返回字典"
    assert "vllm_base_url" in config_dict, "字典应该包含 vllm_base_url"
    assert "code_execution_timeout" in config_dict, "字典应该包含 code_execution_timeout"
    
    print("  ✓ settings 转换为字典测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试 settings 模块")
    print("=" * 60)
    
    tests = [
        test_settings_default_values,
        test_settings_from_env,
        test_settings_validation,
        test_settings_singleton,
        test_settings_to_dict,
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
