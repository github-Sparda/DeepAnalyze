"""
State Management Usage Examples and Tests
状态管理使用示例和测试
"""

from src.core.state.manager import (
    StateManager,
    create_new_session,
    get_session_state,
    save_session_state,
    update_session_state,
    get_state_manager
)


def demo_basic_usage():
    """演示基本使用方法"""
    print("=== 状态管理基本使用演示 ===")
    
    # 创建状态管理器
    manager = StateManager()
    
    # 创建新会话
    session_id = manager.create_session(
        session_name="数据分析会话",
        tags=["analysis", "demo"]
    )
    print(f"创建会话: {session_id}")
    
    # 获取初始状态
    state = manager.get_state(session_id)
    print(f"初始状态字段数: {len(state) if state else 0}")
    
    # 更新状态
    updates = {
        "input_files": ["data.csv", "config.json"],
        "analysis_results": "初步分析完成",
        "hypotheses": ["数据存在季节性趋势", "不同类别间存在显著差异"]
    }
    
    success = manager.update_state(session_id, updates)
    print(f"状态更新: {'成功' if success else '失败'}")
    
    # 验证更新
    updated_state = manager.get_state(session_id)
    if updated_state:
        print(f"输入文件: {updated_state.get('input_files', [])}")
        print(f"分析结果: {updated_state.get('analysis_results', '')}")
        print(f"假设数量: {len(updated_state.get('hypotheses', []))}")
    
    return session_id


def demo_session_lifecycle():
    """演示会话生命周期"""
    print("\n=== 会话生命周期演示 ===")
    
    manager = StateManager()
    
    # 创建多个会话
    session1 = manager.create_session(session_name="会话1", tags=["test"])
    session2 = manager.create_session(session_name="会话2", tags=["production"])
    
    print(f"创建会话1: {session1}")
    print(f"创建会话2: {session2}")
    
    # 列出会话
    all_sessions = manager.list_sessions()
    print(f"总会话数: {len(all_sessions)}")
    
    test_sessions = manager.list_sessions(tags=["test"])
    print(f"测试会话数: {len(test_sessions)}")
    
    # 删除会话
    deleted = manager.delete_session(session1)
    print(f"删除会话1: {'成功' if deleted else '失败'}")
    
    # 验证删除
    remaining_sessions = manager.list_sessions()
    print(f"剩余会话数: {len(remaining_sessions)}")


def demo_concurrent_access():
    """演示并发访问"""
    print("\n=== 并发访问演示 ===")
    
    import threading
    import time
    
    manager = StateManager()
    session_id = manager.create_session(session_name="并发测试")
    
    def worker(worker_id: int):
        for i in range(5):
            # 更新不同的字段
            updates = {
                f"worker_{worker_id}_counter": i,
                f"worker_{worker_id}_timestamp": time.time()
            }
            manager.update_state(session_id, updates)
            time.sleep(0.1)
    
    # 创建多个线程
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    # 检查最终状态
    final_state = manager.get_state(session_id)
    if final_state:
        counters = [key for key in final_state.keys() if key.startswith('worker_')]
        print(f"并发更新的字段数: {len(counters)}")


def demo_persistence():
    """演示持久化功能"""
    print("\n=== 持久化功能演示 ===")
    
    # 第一次创建和使用
    manager1 = StateManager()
    session_id = manager1.create_session(session_name="持久化测试")
    
    # 设置一些状态
    initial_updates = {
        "test_data": "这是持久化测试数据",
        "test_number": 42,
        "test_list": [1, 2, 3, 4, 5]
    }
    manager1.update_state(session_id, initial_updates)
    
    # 创建新的管理器实例（模拟重启）
    manager2 = StateManager()
    
    # 从磁盘恢复状态
    restored_state = manager2.get_state(session_id)
    if restored_state:
        print(f"恢复的数据: {restored_state.get('test_data')}")
        print(f"恢复的数字: {restored_state.get('test_number')}")
        print(f"恢复的列表: {restored_state.get('test_list')}")
    
    # 清理
    manager2.delete_session(session_id)
    print("测试会话已清理")


def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理演示 ===")
    
    manager = StateManager()
    
    # 尝试获取不存在的会话
    non_existent_state = manager.get_state("non_existent_session")
    print(f"获取不存在会话: {non_existent_state is None}")
    
    # 尝试更新不存在的会话
    update_success = manager.update_state("non_existent_session", {"test": "value"})
    print(f"更新不存在会话: {update_success is False}")
    
    # 尝试删除不存在的会话
    delete_success = manager.delete_session("non_existent_session")
    print(f"删除不存在会话: {delete_success is False}")


if __name__ == "__main__":
    print("DeepAnalyze 状态管理系统演示")
    print("=" * 50)
    
    try:
        session_id = demo_basic_usage()
        demo_session_lifecycle()
        demo_concurrent_access()
        demo_persistence()
        demo_error_handling()
        
        print(f"\n演示完成！创建的测试会话ID: {session_id}")
        print("注意：演示会话将在程序结束后需要手动清理")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
