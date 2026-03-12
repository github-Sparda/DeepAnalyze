"""扩展测试文件工具模块.

验证 file_utils 中未覆盖的功能.
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.common.file_utils import (
    copy_file,
    hash_file,
    load_text,
    save_text,
    load_json,
    save_json,
)


def test_copy_file():
    """测试文件复制功能."""
    print("测试 copy_file...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建源文件
        src_file = Path(tmpdir) / "source.txt"
        src_file.write_text("Hello, World!", encoding="utf-8")
        
        # 复制到目标
        dst_file = Path(tmpdir) / "subdir" / "destination.txt"
        result = copy_file(src_file, dst_file)
        
        assert result.exists(), "目标文件应该被创建"
        assert result == dst_file, "应该返回正确的路径"
        assert result.read_text(encoding="utf-8") == "Hello, World!", "内容应该一致"
    
    print("  ✓ copy_file 测试通过")


def test_hash_file_algorithms():
    """测试不同哈希算法."""
    print("测试 hash_file 不同算法...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_content = "Test content for hashing"
        test_file.write_text(test_content, encoding="utf-8")
        
        # 测试 SHA256
        sha256_hash = hash_file(test_file, algorithm="sha256")
        assert len(sha256_hash) == 64, "SHA256 应该是 64 个字符"
        
        # 测试 MD5
        md5_hash = hash_file(test_file, algorithm="md5")
        assert len(md5_hash) == 32, "MD5 应该是 32 个字符"
        
        # 测试 SHA1
        sha1_hash = hash_file(test_file, algorithm="sha1")
        assert len(sha1_hash) == 40, "SHA1 应该是 40 个字符"
        
        # 测试一致性
        sha256_hash2 = hash_file(test_file, algorithm="sha256")
        assert sha256_hash == sha256_hash2, "相同内容应该产生相同哈希"
    
    print("  ✓ hash_file 不同算法测试通过")


def test_load_text_edge_cases():
    """测试文本加载边界情况."""
    print("测试 load_text 边界情况...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试空文件
        empty_file = Path(tmpdir) / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        result = load_text(empty_file)
        assert result == "", "空文件应该返回空字符串"
        
        # 测试多行文本
        multi_line = Path(tmpdir) / "multi.txt"
        multi_line.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")
        result = load_text(multi_line)
        assert result == "Line 1\nLine 2\nLine 3", "多行文本应该正确加载"
        
        # 测试 Unicode 内容
        unicode_file = Path(tmpdir) / "unicode.txt"
        unicode_file.write_text("你好世界 🌍 émojis", encoding="utf-8")
        result = load_text(unicode_file)
        assert result == "你好世界 🌍 émojis", "Unicode 内容应该正确加载"
        
        # 测试不存在的文件带自定义默认值
        result = load_text(Path(tmpdir) / "not_exist.txt", default="default_value")
        assert result == "default_value", "应该返回自定义默认值"
    
    print("  ✓ load_text 边界情况测试通过")


def test_save_text_edge_cases():
    """测试文本保存边界情况."""
    print("测试 save_text 边界情况...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试空内容
        empty_file = Path(tmpdir) / "empty.txt"
        result = save_text(empty_file, "")
        assert result.exists(), "文件应该被创建"
        assert result.read_text(encoding="utf-8") == "", "内容应该是空的"
        
        # 测试多行内容
        multi_line = Path(tmpdir) / "multi.txt"
        content = "Line 1\nLine 2\nLine 3"
        result = save_text(multi_line, content)
        assert result.read_text(encoding="utf-8") == content, "多行内容应该正确保存"
        
        # 测试 Unicode 内容
        unicode_file = Path(tmpdir) / "unicode.txt"
        content = "你好世界 🌍 émojis"
        result = save_text(unicode_file, content)
        assert result.read_text(encoding="utf-8") == content, "Unicode 内容应该正确保存"
    
    print("  ✓ save_text 边界情况测试通过")


def test_json_indent():
    """测试 JSON 保存的缩进选项."""
    print("测试 JSON 缩进选项...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = {"key": "value", "nested": {"a": 1}}
        
        # 测试默认缩进
        file1 = Path(tmpdir) / "default.json"
        save_json(file1, test_data)
        content1 = file1.read_text(encoding="utf-8")
        assert "  " in content1, "应该有缩进"
        
        # 测试无缩进
        file2 = Path(tmpdir) / "no_indent.json"
        save_json(file2, test_data, indent=None)
        content2 = file2.read_text(encoding="utf-8")
        assert "\n" not in content2.strip(), "应该没有换行"
    
    print("  ✓ JSON 缩进选项测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始扩展测试文件工具模块")
    print("=" * 60)
    
    tests = [
        test_copy_file,
        test_hash_file_algorithms,
        test_load_text_edge_cases,
        test_save_text_edge_cases,
        test_json_indent,
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
