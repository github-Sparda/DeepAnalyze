"""测试公共工具模块的功能.

此测试脚本验证 src/core/common/ 模块中的工具函数是否按预期执行.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common import (
    ensure_dir,
    load_json,
    save_json,
    load_text,
    save_text,
    hash_file,
    extract_json_candidates,
    safe_json_load,
    safe_json_any,
    load_json_if_exists,
)


def test_ensure_dir():
    """测试目录创建功能."""
    print("测试 ensure_dir...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试创建嵌套目录
        nested_path = Path(tmpdir) / "a" / "b" / "c"
        result = ensure_dir(nested_path)
        assert result.exists(), "目录应该被创建"
        assert result.is_dir(), "应该是目录"
        assert result == nested_path, "应该返回正确的路径"

        # 测试已存在的目录
        result2 = ensure_dir(nested_path)
        assert result2.exists(), "已存在的目录也应该成功"
    print("  ✓ ensure_dir 测试通过")


def test_load_save_json():
    """测试JSON加载和保存功能."""
    print("测试 load_json / save_json...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"
        test_data = {"name": "test", "value": 42, "nested": {"key": "value"}}

        # 测试保存
        result_path = save_json(test_file, test_data)
        assert result_path.exists(), "文件应该被创建"
        assert result_path == test_file, "应该返回正确的路径"

        # 测试加载
        loaded = load_json(test_file)
        assert loaded == test_data, "加载的数据应该与保存的一致"

        # 测试加载不存在的文件
        not_exist = load_json(Path(tmpdir) / "not_exist.json")
        assert not_exist == {}, "不存在的文件应该返回空字典"

        # 测试加载不存在的文件带自定义默认值
        custom_default = load_json(Path(tmpdir) / "not_exist.json", default=[])
        assert custom_default == [], "应该返回自定义默认值"
    print("  ✓ load_json / save_json 测试通过")


def test_load_save_text():
    """测试文本加载和保存功能."""
    print("测试 load_text / save_text...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_content = "Hello, World!\n这是测试内容。"

        # 测试保存
        result_path = save_text(test_file, test_content)
        assert result_path.exists(), "文件应该被创建"

        # 测试加载
        loaded = load_text(test_file)
        assert loaded == test_content, "加载的内容应该与保存的一致"

        # 测试加载不存在的文件
        not_exist = load_text(Path(tmpdir) / "not_exist.txt")
        assert not_exist == "", "不存在的文件应该返回空字符串"

        # 测试加载不存在的文件带自定义默认值
        custom_default = load_text(Path(tmpdir) / "not_exist.txt", default="default")
        assert custom_default == "default", "应该返回自定义默认值"
    print("  ✓ load_text / save_text 测试通过")


def test_hash_file():
    """测试文件哈希功能."""
    print("测试 hash_file...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content, encoding="utf-8")

        # 测试SHA256
        hash1 = hash_file(test_file)
        assert len(hash1) == 64, "SHA256哈希应该是64个字符"
        assert hash1 == hash_file(test_file), "相同内容的哈希应该一致"

        # 测试不存在的文件
        not_exist_hash = hash_file(Path(tmpdir) / "not_exist.txt")
        assert not_exist_hash == "", "不存在的文件应该返回空字符串"

        # 测试MD5
        md5_hash = hash_file(test_file, algorithm="md5")
        assert len(md5_hash) == 32, "MD5哈希应该是32个字符"
    print("  ✓ hash_file 测试通过")


def test_extract_json_candidates():
    """测试JSON候选提取功能."""
    print("测试 extract_json_candidates...")

    # 测试代码块中的JSON
    text_with_code = '''
    这里是一些说明
    ```json
    {"key": "value", "number": 123}
    ```
    更多说明
    '''
    candidates = extract_json_candidates(text_with_code)
    assert len(candidates) > 0, "应该提取到JSON候选"
    assert '{"key": "value", "number": 123}' in candidates, "应该提取代码块中的JSON"

    # 测试普通JSON对象
    text_with_json = '前缀 {"name": "test"} 后缀'
    candidates = extract_json_candidates(text_with_json)
    assert '{"name": "test"}' in candidates, "应该提取普通JSON对象"

    # 测试JSON数组
    text_with_array = "数据 [1, 2, 3] 结束"
    candidates = extract_json_candidates(text_with_array)
    assert "[1, 2, 3]" in candidates, "应该提取JSON数组"
    print("  ✓ extract_json_candidates 测试通过")


def test_safe_json_load():
    """测试安全JSON加载功能."""
    print("测试 safe_json_load...")

    # 测试正常JSON
    normal_json = '{"key": "value", "number": 42}'
    result = safe_json_load(normal_json)
    assert result == {"key": "value", "number": 42}, "应该正确解析正常JSON"

    # 测试代码块中的JSON
    code_block_json = '```json\n{"key": "value"}\n```'
    result = safe_json_load(code_block_json)
    assert result == {"key": "value"}, "应该提取并解析代码块中的JSON"

    # 测试无效JSON
    invalid_json = "不是JSON"
    result = safe_json_load(invalid_json)
    assert result == {}, "无效JSON应该返回空字典"

    # 测试无效JSON带自定义默认值
    result = safe_json_load(invalid_json, default=None)
    assert result is None, "应该返回自定义默认值"

    # 测试空字符串
    result = safe_json_load("")
    assert result == {}, "空字符串应该返回空字典"

    # 测试None
    result = safe_json_load(None)
    assert result == {}, "None应该返回空字典"
    print("  ✓ safe_json_load 测试通过")


def test_safe_json_any():
    """测试安全JSON转换功能."""
    print("测试 safe_json_any...")

    # 测试基本类型
    assert safe_json_any("string") == "string", "字符串应该保持不变"
    assert safe_json_any(42) == 42, "整数应该保持不变"
    assert safe_json_any(3.14) == 3.14, "浮点数应该保持不变"
    assert safe_json_any(True) is True, "布尔值应该保持不变"

    # 测试列表
    result = safe_json_any([1, 2, 3])
    assert result == [1, 2, 3], "列表应该正确转换"

    # 测试元组
    result = safe_json_any((1, 2, 3))
    assert result == [1, 2, 3], "元组应该转换为列表"

    # 测试字典
    result = safe_json_any({"key": "value"})
    assert result == {"key": "value"}, "字典应该正确转换"

    # 测试嵌套结构
    nested = {"list": [1, 2], "dict": {"a": 1}}
    result = safe_json_any(nested)
    assert result == nested, "嵌套结构应该正确转换"

    # 测试None
    result = safe_json_any(None)
    assert result == {}, "None应该返回空字典"

    # 测试自定义类
    class TestClass:
        def __init__(self):
            self.name = "test"
            self.value = 42

    obj = TestClass()
    result = safe_json_any(obj)
    assert result == {"name": "test", "value": 42}, "自定义类应该转换为字典"
    print("  ✓ safe_json_any 测试通过")


def test_load_json_if_exists():
    """测试条件JSON加载功能."""
    print("测试 load_json_if_exists...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"
        test_data = {"key": "value"}
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        # 测试存在的文件
        result = load_json_if_exists(test_file)
        assert result == test_data, "应该加载存在的文件"

        # 测试不存在的文件
        result = load_json_if_exists(Path(tmpdir) / "not_exist.json")
        assert result == {}, "不存在的文件应该返回空字典"

        # 测试非字典JSON（数组）
        array_file = Path(tmpdir) / "array.json"
        array_file.write_text("[1, 2, 3]", encoding="utf-8")
        result = load_json_if_exists(array_file)
        assert result == {}, "非字典JSON应该返回空字典"
    print("  ✓ load_json_if_exists 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试 src/core/common/ 模块")
    print("=" * 60)

    tests = [
        test_ensure_dir,
        test_load_save_json,
        test_load_save_text,
        test_hash_file,
        test_extract_json_candidates,
        test_safe_json_load,
        test_safe_json_any,
        test_load_json_if_exists,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} 测试失败: {e}")
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)