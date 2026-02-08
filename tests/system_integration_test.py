#!/usr/bin/env python3
"""
系统集成测试和性能优化验证
System Integration Test and Performance Optimization
"""

import sys
import os
import time
import json
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入各个模块
from deepanalyze.state.manager import StateManager
from deepanalyze.error.handler import ErrorHandler, ErrorSeverity, ErrorCategory, safe_execute
from deepanalyze.assistant.engine import AIAssistantEngine
from deepanalyze.analytics.advanced_analyzer import AdvancedDataAnalyzer, analyze_dataset
from deepanalyze.reporting.manager import ReportManager
from deepanalyze.collaboration.manager import CollaborationManager, PermissionLevel

class SystemIntegrationTest:
    """系统集成测试类"""
    
    def __init__(self):
        self.temp_dir = None
        self.managers = {}
        self.test_results = {}
        self.performance_metrics = {}
    
    def setup(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")
        self.temp_dir = tempfile.mkdtemp(prefix="deepanalyze_test_")
        
        # 初始化各个管理器
        self.managers = {
            'state': StateManager(self.temp_dir),
            'error': ErrorHandler(),
            'assistant': AIAssistantEngine(),
            'analyzer': AdvancedDataAnalyzer(),
            'report': ReportManager(self.temp_dir),
            'collaboration': CollaborationManager(self.temp_dir)
        }
        
        print(f"📁 测试工作目录: {self.temp_dir}")
        print("✅ 测试环境设置完成")
    
    def teardown(self):
        """清理测试环境"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print("🧹 测试环境已清理")
    
    def test_complete_analysis_workflow(self):
        """测试完整的分析工作流"""
        print("\n🧪 测试完整分析工作流...")
        start_time = time.time()
        
        try:
            session_id = "integration_test_session"
            
            # 1. 创建会话状态
            print("  1️⃣ 创建会话状态...")
            state_created = self.managers['state'].create_session(session_id)
            assert state_created, "会话创建失败"
            
            # 2. 添加协作者
            print("  2️⃣ 添加协作者...")
            collab_added = self.managers['collaboration'].add_collaborator(
                session_id, "user_001", "测试用户", "test@example.com", PermissionLevel.EDITOR
            )
            assert collab_added, "添加协作者失败"
            
            # 3. 模拟数据分析
            print("  3️⃣ 执行数据分析...")
            # 使用正确的API接口
            sample_data_path = Path(self.temp_dir) / "sample_data.csv"
            sample_data_content = "name,age,salary\n张三,25,8000\n李四,30,12000\n王五,35,15000"
            sample_data_path.write_text(sample_data_content, encoding='utf-8')
            
            analysis_result = analyze_dataset(
                file_path=str(sample_data_path),
                session_id=session_id
            )
            assert analysis_result is not None, "数据分析失败"
            assert "error" not in analysis_result, f"数据分析出错: {analysis_result.get('error', '')}"
            
            # 4. 生成AI助手响应
            print("  4️⃣ 生成AI助手响应...")
            assistant_response = self.managers['assistant'].process_message(
                session_id, "请分析这些员工数据的主要特征"
            )
            assert assistant_response is not None, "AI助手响应失败"
            
            # 5. 创建分析报告
            print("  5️⃣ 创建分析报告...")
            report = self.managers['report'].create_report(
                session_id=session_id,
                report_type="comprehensive",
                title="员工数据分析报告",
                content=json.dumps(analysis_result, ensure_ascii=False)
            )
            assert report is not None, "报告创建失败"
            
            # 6. 添加评论
            print("  6️⃣ 添加评论...")
            comment = self.managers['collaboration'].add_comment(
                resource_id=report.report_id,
                content="这份报告很有价值！",
                author_id="user_001",
                author_name="测试用户"
            )
            assert comment is not None, "添加评论失败"
            
            # 7. 验证状态更新
            print("  7️⃣ 验证状态更新...")
            session_state = self.managers['state'].get_session_state(session_id)
            assert session_state is not None, "获取会话状态失败"
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results['complete_workflow'] = {
                'status': 'PASS',
                'execution_time': execution_time,
                'steps_completed': 7
            }
            
            print(f"✅ 完整工作流测试通过 (耗时: {execution_time:.3f}秒)")
            return True
            
        except Exception as e:
            self.test_results['complete_workflow'] = {
                'status': 'FAIL',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
            print(f"❌ 完整工作流测试失败: {str(e)}")
            return False
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        print("\n🧪 测试并发操作...")
        start_time = time.time()
        
        try:
            import threading
            import concurrent.futures
            
            session_ids = [f"concurrent_test_{i}" for i in range(5)]
            results = []
            
            def worker(session_id):
                try:
                    # 创建会话
                    self.managers['state'].create_session(session_id)
                    
                    # 添加数据
                    sample_data = {"test": f"data_{session_id}"}
                    success = self.managers['state'].update_state(session_id, {"test_data": sample_data})
                    
                    # 获取数据验证
                    retrieved_state = self.managers['state'].get_state(session_id)
                    retrieved_data = retrieved_state.get("test_data") if retrieved_state else None
                    return success and retrieved_data == sample_data
                except Exception:
                    return False
            
            # 使用线程池执行并发测试
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_results = [executor.submit(worker, sid) for sid in session_ids]
                results = [future.result() for future in future_results]
            
            success_count = sum(results)
            total_count = len(results)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results['concurrent_operations'] = {
                'status': 'PASS' if success_count == total_count else 'FAIL',
                'success_rate': f"{success_count}/{total_count}",
                'execution_time': execution_time
            }
            
            print(f"✅ 并发操作测试完成: {success_count}/{total_count} 成功 (耗时: {execution_time:.3f}秒)")
            return success_count == total_count
            
        except Exception as e:
            self.test_results['concurrent_operations'] = {
                'status': 'FAIL',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
            print(f"❌ 并发操作测试失败: {str(e)}")
            return False
    
    def test_error_recovery(self):
        """测试错误恢复机制"""
        print("\n🧪 测试错误恢复机制...")
        start_time = time.time()
        
        try:
            # 测试错误处理
            test_error = ValueError("测试错误")
            error_info = self.managers['error'].handle_error(
                test_error,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXECUTION
            )
            
            assert error_info is not None, "错误处理失败"
            assert error_info.severity == ErrorSeverity.HIGH, "错误严重程度不正确"
            
            # 测试安全执行器
            def risky_operation():
                raise RuntimeError("模拟运行时错误")
            
            safe_result = safe_execute(risky_operation, fallback_value="默认值")
            assert safe_result == "默认值", "安全执行器应该返回默认值"
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results['error_recovery'] = {
                'status': 'PASS',
                'execution_time': execution_time
            }
            
            print(f"✅ 错误恢复测试通过 (耗时: {execution_time:.3f}秒)")
            return True
            
        except Exception as e:
            self.test_results['error_recovery'] = {
                'status': 'FAIL',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
            print(f"❌ 错误恢复测试失败: {str(e)}")
            return False
    
    def test_performance_benchmark(self):
        """性能基准测试"""
        print("\n🧪 执行性能基准测试...")
        
        performance_tests = {
            'session_creation': self._benchmark_session_creation,
            'data_storage': self._benchmark_data_storage,
            'intent_classification': self._benchmark_intent_classification,
            'report_generation': self._benchmark_report_generation
        }
        
        for test_name, test_func in performance_tests.items():
            print(f"  📊 测试 {test_name}...")
            try:
                result = test_func()
                self.performance_metrics[test_name] = result
                print(f"    ⏱️  平均耗时: {result['avg_time']:.4f}秒")
                print(f"    📈 吞吐量: {result['throughput']:.1f} ops/sec")
            except Exception as e:
                print(f"    ❌ 测试失败: {str(e)}")
                self.performance_metrics[test_name] = {'error': str(e)}
    
    def _benchmark_session_creation(self, iterations=100):
        """会话创建性能测试"""
        times = []
        for i in range(iterations):
            start_time = time.time()
            session_id = f"perf_test_{i}"
            self.managers['state'].create_session(session_id)
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        throughput = 1 / avg_time if avg_time > 0 else 0
        
        return {
            'avg_time': avg_time,
            'min_time': min(times),
            'max_time': max(times),
            'throughput': throughput,
            'iterations': iterations
        }
    
    def _benchmark_data_storage(self, iterations=100):
        """数据存储性能测试"""
        times = []
        test_data = {"numbers": list(range(1000)), "text": "x" * 1000}
        
        for i in range(iterations):
            start_time = time.time()
            session_id = f"data_test_{i}"
            self.managers['state'].create_session(session_id)
            self.managers['state'].update_state(session_id, {"benchmark_data": test_data})
            self.managers['state'].get_state(session_id)
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        throughput = 1 / avg_time if avg_time > 0 else 0
        
        return {
            'avg_time': avg_time,
            'min_time': min(times),
            'max_time': max(times),
            'throughput': throughput,
            'iterations': iterations
        }
    
    def _benchmark_intent_classification(self, iterations=50):
        """意图分类性能测试"""
        times = []
        test_messages = [
            "分析这份销售数据",
            "帮我看看数据有什么问题",
            "生成一份完整的报告",
            "这个趋势是怎么回事",
            "需要进一步深入分析"
        ]
        
        for i in range(iterations):
            start_time = time.time()
            message = test_messages[i % len(test_messages)]
            # 使用正确的API接口
            session_id = f"intent_test_{i}"
            self.managers['state'].create_session(session_id)
            self.managers['assistant'].process_message(session_id, message)
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        throughput = 1 / avg_time if avg_time > 0 else 0
        
        return {
            'avg_time': avg_time,
            'min_time': min(times),
            'max_time': max(times),
            'throughput': throughput,
            'iterations': iterations
        }
    
    def _benchmark_report_generation(self, iterations=20):
        """报告生成性能测试"""
        times = []
        sample_content = json.dumps({
            "title": "性能测试报告",
            "sections": [
                {"name": "摘要", "content": "这是测试摘要"},
                {"name": "数据分析", "content": "这里是详细分析"},
                {"name": "结论", "content": "测试结论"}
            ] * 10  # 重复10次增加内容长度
        }, ensure_ascii=False)
        
        for i in range(iterations):
            start_time = time.time()
            session_id = f"report_test_{i}"
            self.managers['state'].create_session(session_id)
            self.managers['report'].create_report(
                session_id=session_id,
                report_type="comprehensive",
                title=f"性能测试报告 {i}",
                content=sample_content
            )
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        throughput = 1 / avg_time if avg_time > 0 else 0
        
        return {
            'avg_time': avg_time,
            'min_time': min(times),
            'max_time': max(times),
            'throughput': throughput,
            'iterations': iterations
        }
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📋 系统集成测试报告")
        print("=" * 60)
        
        # 测试结果汇总
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result.get('status') == 'PASS')
        total_tests = len(self.test_results)
        
        print(f"\n🎯 测试结果汇总:")
        print(f"   ✅ 通过: {passed_tests}")
        print(f"   ❌ 失败: {total_tests - passed_tests}")
        print(f"   📊 成功率: {passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "📊 成功率: 0%")
        
        print(f"\n🔬 详细测试结果:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            time_info = f" ({result['execution_time']:.3f}s)" if 'execution_time' in result else ""
            print(f"   {status_icon} {test_name}: {result['status']}{time_info}")
        
        print(f"\n⚡ 性能基准测试:")
        for test_name, metrics in self.performance_metrics.items():
            if 'error' in metrics:
                print(f"   ❌ {test_name}: 测试失败 - {metrics['error']}")
            else:
                print(f"   📊 {test_name}:")
                print(f"      平均耗时: {metrics['avg_time']*1000:.2f}ms")
                print(f"      吞吐量: {metrics['throughput']:.1f} ops/sec")
                print(f"      最小/最大: {metrics['min_time']*1000:.2f}ms / {metrics['max_time']*1000:.2f}ms")
        
        # 系统健康度评估
        health_score = self.calculate_health_score()
        print(f"\n🏥 系统健康度评估: {health_score}/100")
        
        if health_score >= 90:
            print("   🟢 系统状态优秀")
        elif health_score >= 75:
            print("   🟡 系统状态良好")
        elif health_score >= 60:
            print("   🟠 系统状态一般")
        else:
            print("   🔴 系统状态需要优化")
        
        print("=" * 60)
        
        return {
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'health_score': health_score,
            'passed_tests': passed_tests,
            'total_tests': total_tests
        }
    
    def calculate_health_score(self):
        """计算系统健康度分数"""
        score = 100
        
        # 基于测试通过率
        if self.test_results:
            pass_rate = sum(1 for r in self.test_results.values() if r.get('status') == 'PASS') / len(self.test_results)
            score *= pass_rate
        
        # 基于性能指标
        if self.performance_metrics:
            perf_scores = []
            for metrics in self.performance_metrics.values():
                if 'avg_time' in metrics and 'error' not in metrics:
                    # 性能得分：平均响应时间越短得分越高
                    avg_time_ms = metrics['avg_time'] * 1000
                    if avg_time_ms < 10:
                        perf_scores.append(100)
                    elif avg_time_ms < 50:
                        perf_scores.append(80)
                    elif avg_time_ms < 100:
                        perf_scores.append(60)
                    else:
                        perf_scores.append(40)
            
            if perf_scores:
                score = score * 0.7 + (sum(perf_scores) / len(perf_scores)) * 0.3
        
        return round(score)

def main():
    """主测试函数"""
    print("🚀 开始系统集成测试和性能优化验证")
    
    tester = SystemIntegrationTest()
    
    try:
        # 设置测试环境
        tester.setup()
        
        # 执行各项测试
        test_functions = [
            tester.test_complete_analysis_workflow,
            tester.test_concurrent_operations,
            tester.test_error_recovery
        ]
        
        for test_func in test_functions:
            test_func()
        
        # 执行性能基准测试
        tester.test_performance_benchmark()
        
        # 生成测试报告
        report = tester.generate_test_report()
        
        # 保存测试报告
        report_file = Path(tester.temp_dir) / "integration_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 测试报告已保存到: {report_file}")
        
        # 返回测试结果
        return report['health_score'] >= 75  # 健康度75分以上认为通过
        
    except Exception as e:
        print(f"💥 测试执行过程中发生错误: {str(e)}")
        return False
    finally:
        # 清理测试环境
        tester.teardown()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)