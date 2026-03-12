"""测试状态管理器模块.

验证 state/manager 模块的功能.
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.state.manager import (
    StateManager,
    SessionMetadata,
    get_state_manager,
    create_new_session,
    get_session_state,
)


def test_session_metadata():
    """测试会话元数据."""
    print("测试 SessionMetadata...")
    
    from datetime import datetime
    
    metadata = SessionMetadata(
        session_id="test_session",
        created_at=datetime.now(),
        last_accessed=datetime.now(),
        user_id="user123",
        session_name="Test Session",
        tags=["test", "demo"]
    )
    
    assert metadata.session_id == "test_session"
    assert metadata.user_id == "user123"
    assert metadata.session_name == "Test Session"
    assert "test" in metadata.tags
    
    print("  ✓ SessionMetadata 测试通过")


def test_state_manager_create_session():
    """测试创建会话."""
    print("测试 StateManager 创建会话...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(base_dir=tmpdir)
        
        # 测试创建会话（自动生成ID）
        session_id = manager.create_session()
        assert session_id is not None
        assert session_id.startswith("session_")
        
        # 测试创建会话（指定ID）
        custom_id = "custom_session_123"
        session_id2 = manager.create_session(session_id=custom_id)
        assert session_id2 == custom_id
        
        # 测试创建会话（带元数据）
        session_id3 = manager.create_session(
            user_id="user123",
            session_name="Test Session",
            tags=["test", "demo"]
        )
        assert session_id3 is not None
        
        # 验证元数据
        metadata = manager.get_session_info(session_id3)
        assert metadata is not None
        assert metadata.user_id == "user123"
        assert metadata.session_name == "Test Session"
        assert "test" in metadata.tags
    
    print("  ✓ StateManager 创建会话测试通过")


def test_state_manager_get_save_state():
    """测试获取和保存状态."""
    print("测试 StateManager 获取和保存状态...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(base_dir=tmpdir)
        
        # 创建会话
        session_id = manager.create_session()
        
        # 获取状态
        state = manager.get_state(session_id)
        assert state is not None
        assert state["session_id"] == session_id
        
        # 保存新状态
        new_state = state.copy()
        new_state["test_key"] = "test_value"
        result = manager.save_state(session_id, new_state)
        assert result is True
        
        # 重新获取状态
        retrieved_state = manager.get_state(session_id)
        assert retrieved_state["test_key"] == "test_value"
        
        # 测试获取不存在的会话
        assert manager.get_state("nonexistent") is None
    
    print("  ✓ StateManager 获取和保存状态测试通过")


def test_state_manager_update_state():
    """测试更新状态."""
    print("测试 StateManager 更新状态...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(base_dir=tmpdir)
        
        # 创建会话
        session_id = manager.create_session()
        
        # 更新状态
        result = manager.update_state(session_id, {"new_field": "new_value"})
        assert result is True
        
        # 验证更新
        state = manager.get_state(session_id)
        assert state["new_field"] == "new_value"
        
        # 测试更新不存在的会话
        result = manager.update_state("nonexistent", {"field": "value"})
        assert result is False
    
    print("  ✓ StateManager 更新状态测试通过")


def test_state_manager_delete_session():
    """测试删除会话."""
    print("测试 StateManager 删除会话...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(base_dir=tmpdir)
        
        # 创建会话
        session_id = manager.create_session()
        
        # 验证会话存在
        assert manager.get_state(session_id) is not None
        
        # 删除会话
        result = manager.delete_session(session_id)
        assert result is True
        
        # 验证会话已删除
        assert manager.get_state(session_id) is None
        
        # 测试删除不存在的会话
        result = manager.delete_session("nonexistent")
        assert result is True  # 删除不存在的会话也返回True
    
    print("  ✓ StateManager 删除会话测试通过")


def test_state_manager_list_sessions():
    """测试列会话."""
    print("测试 StateManager 列会话...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(base_dir=tmpdir)
        
        # 创建多个会话
        session1 = manager.create_session(user_id="user1", tags=["tag1"])
        session2 = manager.create_session(user_id="user1", tags=["tag2"])
        session3 = manager.create_session(user_id="user2", tags=["tag1", "tag2"])
        
        # 列出所有会话
        sessions = manager.list_sessions()
        assert len(sessions) == 3
        
        # 按用户ID过滤
        sessions = manager.list_sessions(user_id="user1")
        assert len(sessions) == 2
        
        # 按标签过滤
        sessions = manager.list_sessions(tags=["tag1"])
        assert len(sessions) == 2
        
        # 注意：标签过滤是 OR 关系（any），不是 AND 关系（all）
        sessions = manager.list_sessions(tags=["tag1", "tag2"])
        assert len(sessions) == 3  # 所有会话都至少有一个匹配的标签
    
    print("  ✓ StateManager 列会话测试通过")


def test_state_manager_persistence():
    """测试状态持久化."""
    print("测试 StateManager 持久化...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建第一个管理器并创建会话
        manager1 = StateManager(base_dir=tmpdir)
        session_id = manager1.create_session(user_id="user123")
        manager1.update_state(session_id, {"test_data": "persisted"})
        
        # 创建第二个管理器（应该加载已有会话）
        manager2 = StateManager(base_dir=tmpdir)
        
        # 验证会话被加载
        metadata = manager2.get_session_info(session_id)
        assert metadata is not None
        assert metadata.user_id == "user123"
        
        # 验证状态被加载
        state = manager2.get_state(session_id)
        assert state is not None
        assert state["test_data"] == "persisted"
    
    print("  ✓ StateManager 持久化测试通过")


def test_convenience_functions():
    """测试便捷函数."""
    print("测试便捷函数...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 注意：这会使用全局状态管理器，需要小心
        # 在实际测试中可能需要重置全局实例
        
        # 测试获取状态管理器
        manager = get_state_manager()
        assert manager is not None
        
        print("  ✓ 便捷函数测试通过")


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("开始测试状态管理器模块")
    print("=" * 60)
    
    tests = [
        test_session_metadata,
        test_state_manager_create_session,
        test_state_manager_get_save_state,
        test_state_manager_update_state,
        test_state_manager_delete_session,
        test_state_manager_list_sessions,
        test_state_manager_persistence,
        test_convenience_functions,
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
