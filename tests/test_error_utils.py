"""测试错误处理工具模块.

验证 error_utils 模块的功能.
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common.error_utils import (
    safe_execute,
    safe_convert_to_float,
    safe_convert_to_int,
    extract_hypothesis_id,
    find_nearest_centroid,
    detect_time_column,
    normalize_output_dir,
)
import numpy as np


def test_safe_execute():
    """测试安全执行函数."""
    print("测试 safe_execute...")
    
    # 测试正常执行
    result = safe_execute(lambda x: x * 2, 5, default=0)
    assert result == 10
    
    # 测试异常返回默认值
    result = safe_execute(lambda x: 1/x, 0, default=-1)
    assert result == -1
    
    # 测试自定义错误消息
    result = safe_execute(lambda: int("not_a_number"), default=0, error_message="Conversion failed")
    assert result == 0
    
    print("  ✓ safe_execute 测试通过")


def test_safe_convert_to_float():
    """测试安全转换为浮点数."""
    print("测试 safe_convert_to_float...")
    
    # 测试正常转换
    assert safe_convert_to_float("3.14") == 3.14
    assert safe_convert_to_float(42) == 42.0
    assert safe_convert_to_float(3.14) == 3.14
    
    # 测试布尔值返回None
    assert safe_convert_to_float(True) is None
    assert safe_convert_to_float(False) is None
    
    # 测试无效值返回None
    assert safe_convert_to_float("not_a_number") is None
    assert safe_convert_to_float(None) is None
    
    print("  ✓ safe_convert_to_float 测试通过")


def test_safe_convert_to_int():
    """测试安全转换为整数."""
    print("测试 safe_convert_to_int...")
    
    # 测试正常转换
    assert safe_convert_to_int("42") == 42
    assert safe_convert_to_int(3.14) == 3
    
    # 测试布尔值返回None
    assert safe_convert_to_int(True) is None
    assert safe_convert_to_int(False) is None
    
    # 测试无效值返回None
    assert safe_convert_to_int("not_a_number") is None
    assert safe_convert_to_int(None) is None
    
    print("  ✓ safe_convert_to_int 测试通过")


def test_extract_hypothesis_id():
    """测试提取假设ID."""
    print("测试 extract_hypothesis_id...")
    
    # 测试正常提取
    assert extract_hypothesis_id("H1 hypothesis") == "H1"
    assert extract_hypothesis_id("Test H12 description") == "H12"
    assert extract_hypothesis_id("H123") == "H123"
    
    # 测试默认索引
    assert extract_hypothesis_id("no hypothesis id", default_idx=0) == "H1"
    assert extract_hypothesis_id("no hypothesis id", default_idx=5) == "H6"
    
    print("  ✓ extract_hypothesis_id 测试通过")


def test_find_nearest_centroid():
    """测试查找最近质心."""
    print("测试 find_nearest_centroid...")
    
    centroids = {
        "A": [0.0, 0.0],
        "B": [10.0, 10.0],
        "C": [5.0, 5.0],
    }
    
    # 测试找到最近的质心
    sample = np.array([1.0, 1.0])
    assert find_nearest_centroid(sample, centroids) == "A"
    
    sample = np.array([9.0, 9.0])
    assert find_nearest_centroid(sample, centroids) == "B"
    
    sample = np.array([4.0, 4.0])
    assert find_nearest_centroid(sample, centroids) == "C"
    
    print("  ✓ find_nearest_centroid 测试通过")


def test_detect_time_column():
    """测试检测时间列."""
    print("测试 detect_time_column...")
    
    import pandas as pd
    
    # 测试包含time列
    df = pd.DataFrame({"time": [1, 2, 3], "value": [4, 5, 6]})
    assert detect_time_column(df) == "time"
    
    # 测试包含date列
    df = pd.DataFrame({"date": [1, 2, 3], "value": [4, 5, 6]})
    assert detect_time_column(df) == "date"
    
    # 测试包含timestamp列
    df = pd.DataFrame({"timestamp": [1, 2, 3], "value": [4, 5, 6]})
    assert detect_time_column(df) == "timestamp"
    
    # 测试没有时间列
    df = pd.DataFrame({"value": [4, 5, 6], "count": [1, 2, 3]})
    assert detect_time_column(df) is None
    
    print("  ✓ detect_time_column 测试通过")


def test_normalize_output_dir():
    """测试规范化输出目录."""
    print("测试 normalize_output_dir...")
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试创建子目录
        parent_dir = Path(tmpdir) / "parent"
        parent_dir.mkdir()
        path = normalize_output_dir(parent_dir, "result")
        assert path.exists()
        # 如果目录已存在且有名称，会返回原目录
        
        # 测试空路径（使用默认名称）
        empty_dir = Path(tmpdir) / "empty"
        empty_dir.mkdir()
        path2 = normalize_output_dir(empty_dir / ".", "plots")
        assert path2.exists()
        
        # 测试直接传入路径
        path3 = normalize_output_dir(Path(tmpdir) / "output")
        assert path3.exists()
        assert path3.name == "output"
    
    print("  ✓ normalize_output_dir 测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试错误处理工具模块")
    print("=" * 60)
    
    tests = [
        test_safe_execute,
        test_safe_convert_to_float,
        test_safe_convert_to_int,
        test_extract_hypothesis_id,
        test_find_nearest_centroid,
        test_detect_time_column,
        test_normalize_output_dir,
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
