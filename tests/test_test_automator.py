from __future__ import annotations

import tempfile
import subprocess
import json
from pathlib import Path

import pytest


class TestTestAutomator:
    """测试测试自动化脚本"""
    
    def test_run_specific_tests(self):
        """测试运行特定测试"""
        # 运行一个简单的测试文件
        result = subprocess.run(
            ["python", "tests/run_tests.py", "--specific", "tests/test_multimodal_data_fusion.py::test_multimodal_evidence_weights", "--verbose"],
            capture_output=True,
            text=True,
            cwd="/home/huangzw/Project/DeepAnalyze"
        )
        
        # 验证测试通过
        assert result.returncode == 0
        assert "通过: 1" in result.stdout
    
    def test_report_generation(self):
        """测试报告生成"""
        # 运行一个简单的测试并生成报告
        result = subprocess.run(
            ["python", "tests/run_tests.py", "--specific", "tests/test_multimodal_data_fusion.py::test_multimodal_evidence_weights"],
            capture_output=True,
            text=True,
            cwd="/home/huangzw/Project/DeepAnalyze"
        )
        
        # 检查报告目录是否存在
        report_dir = Path("/home/huangzw/Project/DeepAnalyze/test_reports")
        assert report_dir.exists()
        
        # 检查是否生成了测试输出文件
        output_files = list(report_dir.glob("test_output_specific_*.txt"))
        assert len(output_files) > 0
    
    def test_help_message(self):
        """测试帮助信息"""
        result = subprocess.run(
            ["python", "tests/run_tests.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/home/huangzw/Project/DeepAnalyze"
        )
        
        assert result.returncode == 0
        assert "测试自动化脚本" in result.stdout
        assert "--all" in result.stdout
        assert "--specific" in result.stdout
        assert "--coverage" in result.stdout
        assert "--verbose" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
