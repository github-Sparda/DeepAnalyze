"""测试报告导出功能.

验证 PDF、DOCX、Markdown 导出是否按预期执行.
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.reporting.manager import ReportManager


def test_markdown_export():
    """测试 Markdown 导出功能."""
    print("测试 Markdown 导出...")

    manager = ReportManager()
    metadata = {
        "title": "测试报告",
        "author": "DeepAnalyze",
        "created_at": "2026-03-13",
        "report_type": "analytical",
        "tags": ["test", "analysis"],
        "keywords": ["data", "report"],
        "version": "1.0",
    }
    content = """## 测试内容

这是一个测试报告的内容。

### 数据摘要

- 数据点1: 100
- 数据点2: 200
- 数据点3: 300

### 结论

测试成功！
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_report.md"
        result = manager._export_to_markdown(content, metadata, str(output_path))

        # 验证文件是否创建
        assert Path(result).exists(), f"文件应该被创建: {result}"

        # 验证内容
        file_content = Path(result).read_text(encoding="utf-8")
        assert "---" in file_content, "应该包含 YAML Front Matter"
        assert "title: 测试报告" in file_content, "应该包含标题"
        assert "author: DeepAnalyze" in file_content, "应该包含作者"
        assert "测试内容" in file_content, "应该包含正文内容"

    print("  ✓ Markdown 导出测试通过")


def test_docx_export():
    """测试 DOCX 导出功能."""
    print("测试 DOCX 导出...")

    manager = ReportManager()
    metadata = {
        "title": "测试报告",
        "author": "DeepAnalyze",
        "created_at": "2026-03-13",
        "report_type": "analytical",
    }
    content = """## 测试内容

这是一个测试报告的内容。

- 列表项1
- 列表项2

**粗体文本** 和 *斜体文本*
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_report.docx"
        result = manager._export_to_docx(content, metadata, str(output_path))

        # 验证文件是否创建
        assert Path(result).exists(), f"文件应该被创建: {result}"

        # 如果 python-docx 未安装，会生成 .md 文件
        if result.endswith('.md'):
            print("  ⚠ python-docx 未安装，生成的是 Markdown 文件")
            file_content = Path(result).read_text(encoding="utf-8")
            assert "DOCX Export Not Available" in file_content
        else:
            print("  ✓ DOCX 文件生成成功")

    print("  ✓ DOCX 导出测试通过")


def test_pdf_export():
    """测试 PDF 导出功能."""
    print("测试 PDF 导出...")

    manager = ReportManager()
    metadata = {
        "title": "测试报告",
        "author": "DeepAnalyze",
        "created_at": "2026-03-13",
        "report_type": "analytical",
    }
    content = """<h2>测试内容</h2>

<p>这是一个测试报告的内容。</p>

<ul>
<li>列表项1</li>
<li>列表项2</li>
</ul>
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_report.pdf"
        result = manager._export_to_pdf(content, metadata, str(output_path))

        # 验证文件是否创建
        assert Path(result).exists(), f"文件应该被创建: {result}"

        # 如果 weasyprint 未安装，会生成 .md 文件
        if result.endswith('.md'):
            print("  ⚠ weasyprint 未安装，生成的是 Markdown 文件")
            file_content = Path(result).read_text(encoding="utf-8")
            assert "PDF Export Not Available" in file_content
        else:
            print("  ✓ PDF 文件生成成功")

    print("  ✓ PDF 导出测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试报告导出功能")
    print("=" * 60)

    tests = [
        test_markdown_export,
        test_docx_export,
        test_pdf_export,
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