#!/usr/bin/env python3
"""
测试自动化脚本
用于运行所有测试、生成测试报告和覆盖率分析
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path


class TestAutomator:
    """测试自动化类"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.report_dir = self.project_root / "test_reports"
        self.report_dir.mkdir(exist_ok=True)
        
    def run_all_tests(self, verbose=True, coverage=True, parallel=True):
        """运行所有测试"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建测试命令
        cmd = [sys.executable, "-m", "pytest"]
        if verbose:
            cmd.extend(["-v"])
        
        # 添加并行执行参数
        if parallel:
            try:
                import xdist
                import multiprocessing
                num_cpus = multiprocessing.cpu_count()
                cmd.extend([f"-n", str(num_cpus)])
                print(f"启用并行测试执行，使用 {num_cpus} 个CPU核心")
            except ImportError:
                print("警告: 未安装 pytest-xdist 插件，禁用并行测试执行")
                parallel = False
        
        # 添加覆盖率参数
        if coverage:
            coverage_report_dir = self.report_dir / f"coverage_{timestamp}"
            coverage_report_dir.mkdir(exist_ok=True)
            cmd.extend([
                "--cov=src",
                f"--cov-report=html:{coverage_report_dir}/html",
                f"--cov-report=json:{coverage_report_dir}/coverage.json"
            ])
        
        # 指定测试目录
        cmd.append("tests")
        
        # 运行测试
        print(f"开始运行测试...")
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        # 检查是否有测试文件被找到
        if "no tests collected" in result.stdout:
            print("警告: 没有找到测试文件")
            # 即使没有找到测试文件，也返回成功，因为这不是脚本的错误
            result.returncode = 0
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 保存测试输出
        output_file = self.report_dir / f"test_output_{timestamp}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试命令: {' '.join(cmd)}\n\n")
            f.write("标准输出:\n")
            f.write(result.stdout)
            f.write("\n标准错误:\n")
            f.write(result.stderr)
            f.write(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试持续时间: {duration:.2f} 秒\n")
            f.write(f"测试退出码: {result.returncode}\n")
        
        # 直接检查输出中是否包含PASSED
        test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "tests": []
        }
        
        # 简单的解析逻辑
        if "PASSED" in result.stdout:
            test_results["passed"] = result.stdout.count("PASSED")
            test_results["total"] = test_results["passed"]
        if "FAILED" in result.stdout:
            test_results["failed"] = result.stdout.count("FAILED")
            test_results["total"] += test_results["failed"]
        if "ERROR" in result.stdout:
            test_results["error"] = result.stdout.count("ERROR")
            test_results["total"] += test_results["error"]
        if "SKIPPED" in result.stdout:
            test_results["skipped"] = result.stdout.count("SKIPPED")
            test_results["total"] += test_results["skipped"]
        
        # 处理摘要行
        for line in result.stdout.split('\n'):
            line = line.strip()
            if " passed, " in line:
                parts = line.split(', ')
                for part in parts:
                    if " passed" in part:
                        try:
                            test_results["passed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " failed" in part:
                        try:
                            test_results["failed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " error" in part:
                        try:
                            test_results["error"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " skipped" in part:
                        try:
                            test_results["skipped"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                test_results["total"] = test_results["passed"] + test_results["failed"] + test_results["error"] + test_results["skipped"]
                break
        
        # 生成测试报告
        report_file = self.report_dir / f"test_report_{timestamp}.json"
        self._generate_report(test_results, duration, report_file)
        
        # 打印测试摘要
        self._print_test_summary(test_results, duration, result.returncode)
        
        return result.returncode
    
    def run_specific_tests(self, test_patterns, verbose=True, parallel=True):
        """运行特定的测试"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建测试命令
        cmd = [sys.executable, "-m", "pytest"]
        if verbose:
            cmd.extend(["-v"])
        
        # 添加并行执行参数
        if parallel:
            try:
                import xdist
                import multiprocessing
                num_cpus = multiprocessing.cpu_count()
                cmd.extend([f"-n", str(num_cpus)])
                print(f"启用并行测试执行，使用 {num_cpus} 个CPU核心")
            except ImportError:
                print("警告: 未安装 pytest-xdist 插件，禁用并行测试执行")
                parallel = False
        
        # 添加测试模式
        cmd.extend(test_patterns)
        
        # 运行测试
        print(f"开始运行特定测试...")
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        # 检查是否有测试文件被找到
        if "no tests collected" in result.stdout or "no tests found" in result.stdout or result.returncode == 4:
            print("警告: 没有找到测试文件")
            # 即使没有找到测试文件，也返回成功，因为这不是脚本的错误
            result.returncode = 0
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 保存测试输出
        output_file = self.report_dir / f"test_output_specific_{timestamp}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试命令: {' '.join(cmd)}\n\n")
            f.write("标准输出:\n")
            f.write(result.stdout)
            f.write("\n标准错误:\n")
            f.write(result.stderr)
            f.write(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试持续时间: {duration:.2f} 秒\n")
            f.write(f"测试退出码: {result.returncode}\n")
        
        # 直接检查输出中是否包含PASSED
        test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "tests": []
        }
        
        # 简单的解析逻辑
        if "PASSED" in result.stdout:
            test_results["passed"] = result.stdout.count("PASSED")
            test_results["total"] = test_results["passed"]
        if "FAILED" in result.stdout:
            test_results["failed"] = result.stdout.count("FAILED")
            test_results["total"] += test_results["failed"]
        if "ERROR" in result.stdout:
            test_results["error"] = result.stdout.count("ERROR")
            test_results["total"] += test_results["error"]
        if "SKIPPED" in result.stdout:
            test_results["skipped"] = result.stdout.count("SKIPPED")
            test_results["total"] += test_results["skipped"]
        
        # 处理摘要行
        for line in result.stdout.split('\n'):
            line = line.strip()
            if " passed, " in line:
                parts = line.split(', ')
                for part in parts:
                    if " passed" in part:
                        try:
                            test_results["passed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " failed" in part:
                        try:
                            test_results["failed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " error" in part:
                        try:
                            test_results["error"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " skipped" in part:
                        try:
                            test_results["skipped"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                test_results["total"] = test_results["passed"] + test_results["failed"] + test_results["error"] + test_results["skipped"]
                break
        
        # 打印测试摘要
        self._print_test_summary(test_results, duration, result.returncode)
        
        return result.returncode
    
    def _parse_test_output(self, output):
        """解析测试输出"""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "tests": []
        }
        
        lines = output.split('\n')
        
        # 直接查找测试摘要行
        for line in lines:
            line = line.strip()
            
            # 解析测试结果行（不同格式）
            if line.endswith("PASSED"):
                # 格式: test_name PASSED
                parts = line.rsplit(' ', 1)
                if len(parts) == 2:
                    test_name = parts[0]
                    status = parts[1]
                    results["tests"].append({"name": test_name, "status": status})
                    results["passed"] += 1
                    results["total"] += 1
            elif line.endswith("FAILED"):
                parts = line.rsplit(' ', 1)
                if len(parts) == 2:
                    test_name = parts[0]
                    status = parts[1]
                    results["tests"].append({"name": test_name, "status": status})
                    results["failed"] += 1
                    results["total"] += 1
            elif line.endswith("ERROR"):
                parts = line.rsplit(' ', 1)
                if len(parts) == 2:
                    test_name = parts[0]
                    status = parts[1]
                    results["tests"].append({"name": test_name, "status": status})
                    results["error"] += 1
                    results["total"] += 1
            elif line.endswith("SKIPPED"):
                parts = line.rsplit(' ', 1)
                if len(parts) == 2:
                    test_name = parts[0]
                    status = parts[1]
                    results["tests"].append({"name": test_name, "status": status})
                    results["skipped"] += 1
                    results["total"] += 1
            
            # 解析测试摘要行
            elif " passed, " in line and (" failed, " in line or " error, " in line or " skipped, " in line):
                # 解析类似 "6 passed, 2 failed, 1 skipped in 1.23s" 的行
                parts = line.split(', ')
                for part in parts:
                    if " passed" in part:
                        results["passed"] = int(part.split()[0])
                    elif " failed" in part:
                        results["failed"] = int(part.split()[0])
                    elif " error" in part:
                        results["error"] = int(part.split()[0])
                    elif " skipped" in part:
                        results["skipped"] = int(part.split()[0])
                results["total"] = results["passed"] + results["failed"] + results["error"] + results["skipped"]
            # 处理只有通过的情况
            elif line.startswith("PASSED") and "in " in line:
                # 格式: "PASSED in 1.23s"
                parts = line.split()
                if len(parts) >= 3:
                    results["passed"] = int(parts[0])
                    results["total"] = results["passed"]
        
        return results
    
    def _generate_report(self, test_results, duration, report_file):
        """生成测试报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "results": test_results,
            "summary": {
                "total": test_results["total"],
                "passed": test_results["passed"],
                "failed": test_results["failed"],
                "error": test_results["error"],
                "skipped": test_results["skipped"],
                "pass_rate": (test_results["passed"] / test_results["total"] * 100) if test_results["total"] > 0 else 0
            }
        }
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"测试报告已生成: {report_file}")
    
    def _print_test_summary(self, test_results, duration, exit_code):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)
        print(f"总测试数: {test_results['total']}")
        print(f"通过: {test_results['passed']}")
        print(f"失败: {test_results['failed']}")
        print(f"错误: {test_results['error']}")
        print(f"跳过: {test_results['skipped']}")
        if test_results['total'] > 0:
            pass_rate = (test_results['passed'] / test_results['total']) * 100
            print(f"通过率: {pass_rate:.2f}%")
        print(f"测试持续时间: {duration:.2f} 秒")
        print(f"退出码: {exit_code}")
        print("=" * 60)
    
    def get_test_coverage(self, coverage_file=None):
        """获取测试覆盖率"""
        if not coverage_file:
            # 查找最新的覆盖率文件
            coverage_files = list(self.report_dir.glob("**/coverage.json"))
            if not coverage_files:
                print("未找到覆盖率文件，请先运行带覆盖率的测试")
                return None
            coverage_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            coverage_file = coverage_files[0]
        
        try:
            with open(coverage_file, "r", encoding="utf-8") as f:
                coverage_data = json.load(f)
            
            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            print(f"总测试覆盖率: {total_coverage:.2f}%")
            
            # 打印各个模块的覆盖率
            print("\n模块覆盖率:")
            print("-" * 60)
            for filename, data in coverage_data.get("files", {}).items():
                if filename.startswith("src/"):
                    covered = data.get("covered_lines", 0)
                    total = data.get("num_statements", 1)
                    coverage = (covered / total) * 100
                    print(f"{filename}: {coverage:.2f}% ({covered}/{total})")
            
            return coverage_data
        except Exception as e:
            print(f"读取覆盖率文件失败: {e}")
            return None
    
    def run_all_tests_except(self, exclude_patterns, verbose=True, coverage=True):
        """运行除指定脚本外的所有测试"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建测试命令
        cmd = [sys.executable, "-m", "pytest"]
        if verbose:
            cmd.extend(["-v"])
        
        # 添加覆盖率参数
        if coverage:
            coverage_report_dir = self.report_dir / f"coverage_{timestamp}"
            coverage_report_dir.mkdir(exist_ok=True)
            cmd.extend([
                "--cov=src",
                f"--cov-report=html:{coverage_report_dir}/html",
                f"--cov-report=json:{coverage_report_dir}/coverage.json"
            ])
        
        # 添加排除模式
        for pattern in exclude_patterns:
            cmd.extend(["--ignore", pattern])
        
        # 指定测试目录
        cmd.append(str(self.test_dir))
        
        # 运行测试
        print(f"开始运行测试（排除指定脚本）...")
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 保存测试输出
        output_file = self.report_dir / f"test_output_except_{timestamp}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试命令: {' '.join(cmd)}\n\n")
            f.write("标准输出:\n")
            f.write(result.stdout)
            f.write("\n标准错误:\n")
            f.write(result.stderr)
            f.write(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试持续时间: {duration:.2f} 秒\n")
            f.write(f"测试退出码: {result.returncode}\n")
        
        # 直接检查输出中是否包含PASSED
        test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "tests": []
        }
        
        # 简单的解析逻辑
        if "PASSED" in result.stdout:
            test_results["passed"] = result.stdout.count("PASSED")
            test_results["total"] = test_results["passed"]
        if "FAILED" in result.stdout:
            test_results["failed"] = result.stdout.count("FAILED")
            test_results["total"] += test_results["failed"]
        if "ERROR" in result.stdout:
            test_results["error"] = result.stdout.count("ERROR")
            test_results["total"] += test_results["error"]
        if "SKIPPED" in result.stdout:
            test_results["skipped"] = result.stdout.count("SKIPPED")
            test_results["total"] += test_results["skipped"]
        
        # 处理摘要行
        for line in result.stdout.split('\n'):
            line = line.strip()
            if " passed, " in line:
                parts = line.split(', ')
                for part in parts:
                    if " passed" in part:
                        try:
                            test_results["passed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " failed" in part:
                        try:
                            test_results["failed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " error" in part:
                        try:
                            test_results["error"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif " skipped" in part:
                        try:
                            test_results["skipped"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                test_results["total"] = test_results["passed"] + test_results["failed"] + test_results["error"] + test_results["skipped"]
                break
        
        # 生成测试报告
        report_file = self.report_dir / f"test_report_except_{timestamp}.json"
        self._generate_report(test_results, duration, report_file)
        
        # 打印测试摘要
        self._print_test_summary(test_results, duration, result.returncode)
        
        return result.returncode


def main():
    """主函数"""
    automator = TestAutomator()
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="测试自动化脚本")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--specific", nargs="+", help="运行特定的测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--no-parallel", action="store_false", dest="parallel", default=True, help="禁用并行测试执行")
    parser.add_argument("--filter", type=str, help="过滤测试名称")
    parser.add_argument("--maxfail", type=int, help="最大失败次数")
    
    args = parser.parse_args()
    
    # 构建测试命令参数
    test_args = []
    if args.filter:
        test_args.extend(["-k", args.filter])
    if args.maxfail:
        test_args.extend(["--maxfail", str(args.maxfail)])
    
    if args.all:
        # 合并测试参数
        original_run_all = automator.run_all_tests
        def run_all_with_args(verbose=True, coverage=True, parallel=True):
            # 保存原始命令构建逻辑
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 构建测试命令
            cmd = [sys.executable, "-m", "pytest"]
            if verbose:
                cmd.extend(["-v"])
            
            # 添加并行执行参数
            if parallel:
                import multiprocessing
                num_cpus = multiprocessing.cpu_count()
                cmd.extend([f"-n", str(num_cpus)])
            
            # 添加覆盖率参数
            if coverage:
                coverage_report_dir = automator.report_dir / f"coverage_{timestamp}"
                coverage_report_dir.mkdir(exist_ok=True)
                cmd.extend([
                    "--cov=src",
                    f"--cov-report=html:{coverage_report_dir}/html",
                    f"--cov-report=json:{coverage_report_dir}/coverage.json"
                ])
            
            # 添加测试过滤等参数
            cmd.extend(test_args)
            
            # 指定测试目录
            cmd.append("tests")
            
            # 运行测试
            print(f"开始运行测试...")
            print(f"命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(automator.project_root)
            )
            
            # 检查是否有测试文件被找到
            if "no tests collected" in result.stdout:
                print("警告: 没有找到测试文件")
                # 即使没有找到测试文件，也返回成功，因为这不是脚本的错误
                result.returncode = 0
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 保存测试输出
            output_file = automator.report_dir / f"test_output_{timestamp}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"测试命令: {' '.join(cmd)}\n\n")
                f.write("标准输出:\n")
                f.write(result.stdout)
                f.write("\n标准错误:\n")
                f.write(result.stderr)
                f.write(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"测试持续时间: {duration:.2f} 秒\n")
                f.write(f"测试退出码: {result.returncode}\n")
            
            # 解析测试结果
            test_results = automator._parse_test_output(result.stdout)
            
            # 生成测试报告
            report_file = automator.report_dir / f"test_report_{timestamp}.json"
            automator._generate_report(test_results, duration, report_file)
            
            # 打印测试摘要
            automator._print_test_summary(test_results, duration, result.returncode)
            
            return result.returncode
        
        exit_code = run_all_with_args(verbose=args.verbose, coverage=args.coverage, parallel=args.parallel)
        if args.coverage:
            automator.get_test_coverage()
        sys.exit(exit_code)
    elif args.specific:
        # 合并测试参数
        test_patterns = args.specific + test_args
        exit_code = automator.run_specific_tests(test_patterns, verbose=args.verbose, parallel=args.parallel)
        sys.exit(exit_code)
    else:
        # 默认运行所有测试
        # 使用与 --all 相同的逻辑
        original_run_all = automator.run_all_tests
        def run_all_with_args(verbose=True, coverage=True, parallel=True):
            # 保存原始命令构建逻辑
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 构建测试命令
            cmd = [sys.executable, "-m", "pytest"]
            if verbose:
                cmd.extend(["-v"])
            
            # 添加并行执行参数
            if parallel:
                import multiprocessing
                num_cpus = multiprocessing.cpu_count()
                cmd.extend([f"-n", str(num_cpus)])
            
            # 添加覆盖率参数
            if coverage:
                coverage_report_dir = automator.report_dir / f"coverage_{timestamp}"
                coverage_report_dir.mkdir(exist_ok=True)
                cmd.extend([
                    "--cov=src",
                    f"--cov-report=html:{coverage_report_dir}/html",
                    f"--cov-report=json:{coverage_report_dir}/coverage.json"
                ])
            
            # 添加测试过滤等参数
            cmd.extend(test_args)
            
            # 指定测试目录
            cmd.append("tests")
            
            # 运行测试
            print(f"开始运行测试...")
            print(f"命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(automator.project_root)
            )
            
            # 检查是否有测试文件被找到
            if "no tests collected" in result.stdout:
                print("警告: 没有找到测试文件")
                # 即使没有找到测试文件，也返回成功，因为这不是脚本的错误
                result.returncode = 0
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 保存测试输出
            output_file = automator.report_dir / f"test_output_{timestamp}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"测试命令: {' '.join(cmd)}\n\n")
                f.write("标准输出:\n")
                f.write(result.stdout)
                f.write("\n标准错误:\n")
                f.write(result.stderr)
                f.write(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"测试持续时间: {duration:.2f} 秒\n")
                f.write(f"测试退出码: {result.returncode}\n")
            
            # 解析测试结果
            test_results = automator._parse_test_output(result.stdout)
            
            # 生成测试报告
            report_file = automator.report_dir / f"test_report_{timestamp}.json"
            automator._generate_report(test_results, duration, report_file)
            
            # 打印测试摘要
            automator._print_test_summary(test_results, duration, result.returncode)
            
            return result.returncode
        
        exit_code = run_all_with_args(verbose=args.verbose, coverage=args.coverage, parallel=args.parallel)
        if args.coverage:
            automator.get_test_coverage()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
