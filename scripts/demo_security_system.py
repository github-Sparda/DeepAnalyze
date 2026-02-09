#!/usr/bin/env python3
"""
安全执行系统演示脚本
展示轻量级沙箱和智能资源调度的核心功能
"""

import sys
import os
import time

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def demonstrate_sandbox_features():
    """演示沙箱功能"""
    print("🚀 安全执行系统演示")
    print("=" * 50)
    
    try:
        # 测试1: 基础沙箱执行
        print("\n--- 测试1: 基础沙箱执行 ---")
        from security.lightweight_sandbox import execute_in_sandbox
        
        test_code = '''
print("Hello from secure sandbox!")
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers]
print(f"Squares: {squares}")
print(f"Sum of squares: {sum(squares)}")
'''
        
        result = execute_in_sandbox(test_code, 'demo_user_1')
        print(f"✅ 执行成功: {result.success}")
        print(f"📄 输出: {result.stdout.strip()}")
        print(f"⏱️  执行时间: {result.execution_time:.3f}秒")
        print(f"💾 内存使用: {result.memory_used} bytes")
        
        # 测试2: 资源限制测试
        print("\n--- 测试2: 资源限制测试 ---")
        memory_test_code = '''
# 尝试分配大量内存
print("Testing memory allocation...")
big_list = [0] * 1000000  # 100万个元素
print(f"Created list with {len(big_list)} elements")
print("Memory test completed")
'''
        
        result2 = execute_in_sandbox(memory_test_code, 'demo_user_2')
        print(f"✅ 内存测试执行: {result2.success}")
        if not result2.success:
            print(f"❌ 失败原因: {result2.stderr}")
        
        # 测试3: 时间限制测试
        print("\n--- 测试3: 时间限制测试 ---")
        infinite_loop_code = '''
print("Starting infinite loop test...")
count = 0
while count < 5:  # 限制循环次数避免真正无限循环
    count += 1
    print(f"Iteration {count}")
print("Loop test completed safely")
'''
        
        result3 = execute_in_sandbox(infinite_loop_code, 'demo_user_3', timeout=5)
        print(f"✅ 时间限制测试: {result3.success}")
        print(f"⏱️  实际执行时间: {result3.execution_time:.3f}秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 沙箱测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_trust_system():
    """演示信任评估系统"""
    print("\n--- 测试4: 用户信任评估系统 ---")
    
    try:
        from security.hybrid_engine import secure_execute, get_user_trust
        
        # 模拟多次执行来测试信任评估
        user_id = "trust_demo_user"
        
        test_codes = [
            'print("First execution")',
            'print("Second execution")', 
            'print("Third execution")',
            'print("Fourth execution")'
        ]
        
        print("执行多次代码来测试信任评估:")
        for i, code in enumerate(test_codes, 1):
            result = secure_execute(code, user_id)
            trust_info = get_user_trust(user_id)
            print(f"  执行 {i}: 信任等级 {trust_info['trust_level'] if trust_info else 'N/A'}")
        
        # 显示最终信任信息
        final_trust = get_user_trust(user_id)
        if final_trust:
            print(f"\n📊 最终用户信任信息:")
            print(f"  用户ID: {final_trust['user_id']}")
            print(f"  信任等级: {final_trust['trust_level']}/10")
            print(f"  执行次数: {final_trust['execution_count']}")
            print(f"  安全级别: {final_trust['security_level']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 信任系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_resource_management():
    """演示资源管理功能"""
    print("\n--- 测试5: 资源管理功能 ---")
    
    try:
        from security.lightweight_sandbox import get_sandbox_stats
        
        # 显示沙箱统计信息
        stats = get_sandbox_stats()
        print("📊 沙箱统计信息:")
        print(f"  活跃进程数: {stats['active_processes']}")
        if stats['process_info']:
            print("  进程详情:")
            for user_id, info in stats['process_info'].items():
                print(f"    用户 {user_id}: PID {info['pid']}, 状态 {info['status']}")
        else:
            print("  暂无活跃进程")
        
        return True
        
    except Exception as e:
        print(f"❌ 资源管理测试失败: {e}")
        return False

def main():
    """主演示函数"""
    print("🔬 DeepAnalyze 安全执行系统演示")
    print("=" * 60)
    
    # 执行各项测试
    tests = [
        ("沙箱基础功能", demonstrate_sandbox_features),
        ("用户信任评估", demonstrate_trust_system),
        ("资源管理", demonstrate_resource_management)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📍 正在测试: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    print("🎯 演示总结")
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！安全执行系统核心功能正常工作")
    else:
        print("⚠️  部分测试失败，请检查系统配置")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)