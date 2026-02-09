"""
Error Handling System Usage Examples and Tests
错误处理系统使用示例和测试
"""

import time
import logging
from pathlib import Path

from error.handler import (
    ErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    safe_execute,
    handle_exception,
    safe_operation,
    critical_operation
)


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def demo_basic_error_handling():
    """演示基本错误处理"""
    print("=== 基本错误处理演示 ===")
    
    # 创建错误处理器
    handler = ErrorHandler()
    
    # 模拟不同类型错误
    try:
        # 网络错误
        raise ConnectionError("无法连接到src_api服务器")
    except Exception as e:
        error_info = handler.handle_error(
            e,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context={"api_endpoint": "chat_completions"}
        )
        print(f"处理网络错误: {error_info.error_id}")
    
    try:
        # 文件系统错误
        raise FileNotFoundError("找不到指定的文件")
    except Exception as e:
        error_info = handler.handle_error(
            e,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.FILESYSTEM,
            context={"filename": "data.csv"}
        )
        print(f"处理文件错误: {error_info.error_id}")
    
    # 查看错误统计
    stats = handler.get_error_statistics()
    print(f"错误总数: {stats.get('total_errors', 0)}")
    print(f"按类别统计: {stats.get('categories', {})}")


def demo_safe_execution():
    """演示安全执行"""
    print("\n=== 安全执行演示 ===")
    
    def risky_function(x, y):
        """可能出错的函数"""
        if y == 0:
            raise ZeroDivisionError("除零错误")
        return x / y
    
    def unstable_function():
        """不稳定函数"""
        import random
        if random.random() < 0.7:  # 70%概率出错
            raise ConnectionError("网络连接不稳定")
        return "操作成功"
    
    # 安全执行除法
    result1 = safe_execute(risky_function, 10, 2, fallback_value=0)
    print(f"安全除法结果: {result1}")
    
    result2 = safe_execute(risky_function, 10, 0, fallback_value=-1)
    print(f"除零保护结果: {result2}")
    
    # 带重试的安全执行
    result3 = safe_execute(unstable_function, max_retries=5, fallback_value="失败")
    print(f"网络操作结果: {result3}")


@safe_operation(max_retries=3, fallback_value="默认值")
def decorated_risky_function(name):
    """使用装饰器的安全函数"""
    import random
    if random.random() < 0.5:
        raise ValueError(f"处理{name}时发生错误")
    return f"成功处理{name}"


@critical_operation
def critical_function(data):
    """关键操作函数"""
    if not data:
        raise ValueError("关键数据不能为空")
    return f"处理了{len(data)}条数据"


def demo_decorators():
    """演示装饰器使用"""
    print("\n=== 装饰器使用演示 ===")
    
    # 安全装饰器
    result1 = decorated_risky_function("用户数据")
    print(f"装饰器函数结果: {result1}")
    
    # 关键操作装饰器
    try:
        result2 = critical_function([1, 2, 3])
        print(f"关键操作结果: {result2}")
    except Exception as e:
        print(f"关键操作失败: {e}")
    
    try:
        critical_function([])  # 这会抛出异常
    except Exception as e:
        print(f"关键操作验证失败: {e}")


def demo_recovery_strategies():
    """演示恢复策略"""
    print("\n=== 恢复策略演示 ===")
    
    handler = ErrorHandler()
    
    # 模拟网络超时错误
    try:
        raise TimeoutError("src_api请求超时")
    except Exception as e:
        error_info = handle_exception(
            e,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK
        )
        print(f"网络错误处理: {error_info.error_id}")
        print(f"恢复尝试次数: {error_info.recovery_attemporaryts}")
        print(f"恢复成功: {error_info.recovery_successful}")


def demo_error_reporting():
    """演示错误报告"""
    print("\n=== 错误报告演示 ===")
    
    handler = ErrorHandler()
    
    # 生成一些错误
    for i in range(5):
        try:
            if i % 2 == 0:
                raise ValueError(f"值错误 {i}")
            else:
                raise RuntimeError(f"运行时错误 {i}")
        except Exception as e:
            handler.handle_error(e, context={"iteration": i})
    
    # 导出错误报告
    report_file = Path("error_report.json")
    success = handler.export_error_report(str(report_file))
    
    if success and report_file.exists():
        print(f"错误报告已导出到: {report_file}")
        # 显示报告内容摘要
        import json
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        print(f"报告生成时间: {report_data['generated_at']}")
        print(f"总错误数: {report_data['statistics']['total_errors']}")
        report_file.unlink()  # 清理测试文件


def demo_concurrent_error_handling():
    """演示并发错误处理"""
    print("\n=== 并发错误处理演示 ===")
    
    import threading
    import concurrent.futures
    
    handler = ErrorHandler()
    
    def worker(worker_id):
        """工作线程"""
        for i in range(3):
            try:
                # 模拟随机错误
                import random
                if random.random() < 0.3:
                    raise Exception(f"Worker {worker_id} error at iteration {i}")
                time.sleep(0.1)
            except Exception as e:
                handler.handle_error(
                    e,
                    context={"worker_id": worker_id, "iteration": i}
                )
    
    # 使用线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(worker, i) for i in range(3)]
        concurrent.futures.wait(futures)
    
    stats = handler.get_error_statistics()
    print(f"并发处理后错误总数: {stats.get('total_errors', 0)}")


if __name__ == "__main__":
    print("DeepAnalyze 错误处理系统演示")
    print("=" * 50)
    
    setup_logging()
    
    try:
        demo_basic_error_handling()
        demo_safe_execution()
        demo_decorators()
        demo_recovery_strategies()
        demo_error_reporting()
        demo_concurrent_error_handling()
        
        print("\n演示完成！")
        print("错误处理系统提供了:")
        print("- 多级别错误分类和严重程度评估")
        print("- 自动恢复策略和重试机制")
        print("- 完整的错误日志和统计")
        print("- 安全执行装饰器")
        print("- 并发安全的错误处理")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()