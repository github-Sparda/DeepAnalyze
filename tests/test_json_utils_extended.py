"""扩展测试 JSON 工具模块.

验证 json_utils 中未覆盖的功能.
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common.json_utils import (
    merge_json_objects,
    validate_json_schema,
    extract_json_candidates,
    safe_json_load,
)


def test_merge_json_objects():
    """测试深度合并 JSON 对象."""
    print("测试 merge_json_objects...")
    
    # 测试基本合并
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = merge_json_objects(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}
    
    # 测试嵌套合并
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    override = {"a": {"y": 20, "z": 30}}
    result = merge_json_objects(base, override)
    assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}
    
    # 测试空字典
    result = merge_json_objects({}, {"a": 1})
    assert result == {"a": 1}
    
    result = merge_json_objects({"a": 1}, {})
    assert result == {"a": 1}
    
    print("  ✓ merge_json_objects 测试通过")


def test_validate_json_schema():
    """测试 JSON Schema 验证."""
    print("测试 validate_json_schema...")
    
    # 测试对象类型验证
    schema = {"type": "object"}
    valid, errors = validate_json_schema({}, schema)
    assert valid is True
    assert len(errors) == 0
    
    valid, errors = validate_json_schema([], schema)
    assert valid is False
    assert len(errors) == 1
    
    # 测试字符串类型验证
    schema = {"type": "string"}
    valid, errors = validate_json_schema("hello", schema)
    assert valid is True
    
    valid, errors = validate_json_schema(123, schema)
    assert valid is False
    
    # 测试数字类型验证
    schema = {"type": "number"}
    valid, errors = validate_json_schema(42, schema)
    assert valid is True
    
    valid, errors = validate_json_schema(3.14, schema)
    assert valid is True
    
    # 测试整数类型验证
    schema = {"type": "integer"}
    valid, errors = validate_json_schema(42, schema)
    assert valid is True
    
    valid, errors = validate_json_schema(3.14, schema)
    assert valid is False
    
    # 测试布尔类型验证
    schema = {"type": "boolean"}
    valid, errors = validate_json_schema(True, schema)
    assert valid is True
    
    # 测试数组类型验证
    schema = {"type": "array"}
    valid, errors = validate_json_schema([1, 2, 3], schema)
    assert valid is True
    
    # 测试 null 类型验证
    schema = {"type": "null"}
    valid, errors = validate_json_schema(None, schema)
    assert valid is True
    
    # 测试必需字段验证
    schema = {
        "type": "object",
        "required": ["name", "age"]
    }
    valid, errors = validate_json_schema({"name": "test"}, schema)
    assert valid is False
    assert any("age" in err for err in errors)
    
    valid, errors = validate_json_schema({"name": "test", "age": 25}, schema)
    assert valid is True
    
    # 测试嵌套属性验证
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    }
    valid, errors = validate_json_schema({"user": {"name": "test"}}, schema)
    assert valid is True
    
    valid, errors = validate_json_schema({"user": {"name": 123}}, schema)
    assert valid is False
    
    print("  ✓ validate_json_schema 测试通过")


def test_extract_json_candidates_edge_cases():
    """测试 JSON 候选提取的边界情况."""
    print("测试 extract_json_candidates 边界情况...")
    
    # 测试空字符串
    candidates = extract_json_candidates("")
    assert len(candidates) == 0
    
    # 测试无 JSON 内容
    candidates = extract_json_candidates("纯文本内容")
    assert len(candidates) == 0
    
    # 测试多个 JSON 对象
    text = '{"a": 1} 一些文本 {"b": 2}'
    candidates = extract_json_candidates(text)
    assert len(candidates) >= 2
    
    # 测试嵌套 JSON
    text = '{"outer": {"inner": "value"}}'
    candidates = extract_json_candidates(text)
    assert len(candidates) >= 1
    
    print("  ✓ extract_json_candidates 边界情况测试通过")


def test_safe_json_load_edge_cases():
    """测试安全 JSON 加载的边界情况."""
    print("测试 safe_json_load 边界情况...")
    
    # 测试带尾部逗号的 JSON
    text = '{"a": 1, "b": 2,}'
    result = safe_json_load(text)
    assert result == {"a": 1, "b": 2}
    
    # 测试单引号 JSON
    text = "{'a': 1, 'b': 2}"
    result = safe_json_load(text)
    assert result == {"a": 1, "b": 2}
    
    # 测试混合引号
    text = '{"a": 1, \'b\': 2}'
    result = safe_json_load(text)
    assert "a" in result or "b" in result
    
    # 测试空白字符
    text = '   {"a": 1}   '
    result = safe_json_load(text)
    assert result == {"a": 1}
    
    # 测试复杂嵌套
    text = '{"a": {"b": {"c": [1, 2, 3]}}}'
    result = safe_json_load(text)
    assert result["a"]["b"]["c"] == [1, 2, 3]
    
    print("  ✓ safe_json_load 边界情况测试通过")


def test_safe_json_any_edge_cases():
    """测试 safe_json_any 的边界情况."""
    print("测试 safe_json_any 边界情况...")
    
    from src.core.common.json_utils import safe_json_any
    
    # 测试嵌套列表
    result = safe_json_any([[1, 2], [3, 4]])
    assert result == [[1, 2], [3, 4]]
    
    # 测试嵌套字典
    result = safe_json_any({"a": {"b": {"c": 1}}})
    assert result == {"a": {"b": {"c": 1}}}
    
    # 测试混合结构
    result = safe_json_any({"list": [1, 2], "tuple": (3, 4), "dict": {"a": 1}})
    assert result["list"] == [1, 2]
    assert result["tuple"] == [3, 4]
    assert result["dict"] == {"a": 1}
    
    # 测试不可序列化对象
    class Unserializable:
        def __str__(self):
            return "unserializable"
    
    result = safe_json_any(Unserializable())
    # 应该返回默认值或某种表示
    assert result is not None
    
    print("  ✓ safe_json_any 边界情况测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始扩展测试 JSON 工具模块")
    print("=" * 60)
    
    tests = [
        test_merge_json_objects,
        test_validate_json_schema,
        test_extract_json_candidates_edge_cases,
        test_safe_json_load_edge_cases,
        test_safe_json_any_edge_cases,
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
