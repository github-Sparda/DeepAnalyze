#!/usr/bin/env python3
"""
协作和分享功能测试
Collaboration and Sharing Features Test
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from deepanalyze.collaboration.manager import (
    CollaborationManager, 
    PermissionLevel, 
    ShareType,
    Collaborator,
    ShareLink,
    Comment,
    ActivityLog
)

def test_collaboration_manager_initialization():
    """测试协作管理器初始化"""
    print("🧪 测试协作管理器初始化...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        
        assert manager.workspace_base == Path(temp_dir)
        assert isinstance(manager.share_links, dict)
        assert isinstance(manager.collaborators, dict)
        assert isinstance(manager.comments, dict)
        assert isinstance(manager.activity_logs, list)
        
        print("✅ 协作管理器初始化测试通过")

def test_add_collaborator():
    """测试添加协作者功能"""
    print("\n🧪 测试添加协作者...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        session_id = "test_session_123"
        
        # 添加协作者
        result = manager.add_collaborator(
            session_id=session_id,
            user_id="user_001",
            username="张三",
            email="zhangsan@example.com",
            permission_level=PermissionLevel.EDITOR
        )
        
        assert result == True
        
        # 验证协作者已添加
        collaborators = manager.get_collaborators(session_id)
        assert len(collaborators) == 1
        
        collab = collaborators[0]
        assert isinstance(collab, Collaborator)
        assert collab.user_id == "user_001"
        assert collab.username == "张三"
        assert collab.email == "zhangsan@example.com"
        assert collab.permission_level == PermissionLevel.EDITOR
        
        print("✅ 添加协作者测试通过")

def test_remove_collaborator():
    """测试移除协作者功能"""
    print("\n🧪 测试移除协作者...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        session_id = "test_session_123"
        
        # 先添加协作者
        manager.add_collaborator(session_id, "user_001", "张三")
        manager.add_collaborator(session_id, "user_002", "李四")
        
        # 验证添加成功
        collaborators = manager.get_collaborators(session_id)
        assert len(collaborators) == 2
        
        # 移除一个协作者
        result = manager.remove_collaborator(session_id, "user_001")
        assert result == True
        
        # 验证移除成功
        remaining_collaborators = manager.get_collaborators(session_id)
        assert len(remaining_collaborators) == 1
        assert remaining_collaborators[0].user_id == "user_002"
        
        print("✅ 移除协作者测试通过")

def test_create_share_link():
    """测试创建分享链接功能"""
    print("\n🧪 测试创建分享链接...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        session_id = "test_session_123"
        
        # 创建分享链接
        share_link = manager.create_share_link(
            session_id=session_id,
            created_by="user_admin",
            permission_level=PermissionLevel.VIEWER,
            expires_in_hours=24,
            max_views=10
        )
        
        assert share_link is not None
        assert isinstance(share_link, ShareLink)
        assert share_link.created_by == "user_admin"
        assert share_link.permission_level == PermissionLevel.VIEWER
        assert share_link.max_views == 10
        assert share_link.view_count == 0
        assert share_link.is_active == True
        
        print("✅ 创建分享链接测试通过")

def test_validate_share_link():
    """测试验证分享链接功能"""
    print("\n🧪 测试验证分享链接...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        session_id = "test_session_123"
        
        # 创建分享链接
        share_link = manager.create_share_link(
            session_id=session_id,
            created_by="user_admin"
        )
        
        # 验证有效的链接
        validated_link = manager.validate_share_link(
            share_link.link_id,
            share_link.share_token
        )
        
        assert validated_link is not None
        assert validated_link.link_id == share_link.link_id
        assert validated_link.view_count == 1  # 查看次数应该增加
        
        # 验证无效的链接（错误的令牌）
        invalid_link = manager.validate_share_link(
            share_link.link_id,
            "wrong_token"
        )
        assert invalid_link is None
        
        print("✅ 验证分享链接测试通过")

def test_comments_functionality():
    """测试评论功能"""
    print("\n🧪 测试评论功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        resource_id = "report_001"
        
        # 添加评论
        comment = manager.add_comment(
            resource_id=resource_id,
            content="这是一个很好的分析报告！",
            author_id="user_001",
            author_name="张三"
        )
        
        assert comment is not None
        assert isinstance(comment, Comment)
        assert comment.content == "这是一个很好的分析报告！"
        assert comment.author_id == "user_001"
        assert comment.author_name == "张三"
        assert comment.is_edited == False
        assert comment.is_deleted == False
        
        # 获取评论
        comments = manager.get_comments(resource_id)
        assert len(comments) == 1
        assert comments[0].comment_id == comment.comment_id
        
        # 编辑评论
        edit_result = manager.edit_comment(
            comment_id=comment.comment_id,
            new_content="这是一个非常出色的分析报告！",
            editor_id="user_001"
        )
        assert edit_result == True
        
        # 验证编辑后的评论
        updated_comments = manager.get_comments(resource_id)
        assert len(updated_comments) == 1
        assert updated_comments[0].content == "这是一个非常出色的分析报告！"
        assert updated_comments[0].is_edited == True
        
        # 删除评论
        delete_result = manager.delete_comment(
            comment_id=comment.comment_id,
            deleter_id="user_001"
        )
        assert delete_result == True
        
        # 验证删除后的评论（应该被过滤掉）
        final_comments = manager.get_comments(resource_id)
        assert len(final_comments) == 0
        
        print("✅ 评论功能测试通过")

def test_activity_logging():
    """测试活动日志功能"""
    print("\n🧪 测试活动日志功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = CollaborationManager(temp_dir)
        session_id = "test_session_123"
        
        # 执行一些操作来生成日志
        manager.add_collaborator(session_id, "user_001", "张三")
        manager.create_share_link(session_id, "user_admin")
        
        # 获取活动日志
        logs = manager.get_activity_logs(limit=10)
        
        assert len(logs) >= 2
        assert isinstance(logs[0], ActivityLog)
        
        # 验证日志内容
        actions = [log.action for log in logs]
        assert "add_collaborator" in actions
        assert "create_share_link" in actions
        
        # 按用户过滤日志
        user_logs = manager.get_activity_logs(user_id="user_001")
        assert len(user_logs) >= 1
        
        print("✅ 活动日志功能测试通过")

def test_permission_levels():
    """测试权限等级枚举"""
    print("\n🧪 测试权限等级...")
    
    # 测试所有权限等级
    permissions = [
        PermissionLevel.OWNER,
        PermissionLevel.ADMIN, 
        PermissionLevel.EDITOR,
        PermissionLevel.VIEWER,
        PermissionLevel.COMMENTER
    ]
    
    expected_values = ["owner", "admin", "editor", "viewer", "commenter"]
    
    for i, permission in enumerate(permissions):
        assert permission.value == expected_values[i]
    
    print("✅ 权限等级测试通过")

def test_data_persistence():
    """测试数据持久化功能"""
    print("\n🧪 测试数据持久化...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)
        manager = CollaborationManager(str(workspace_path))
        session_id = "test_session_123"
        
        # 添加数据
        manager.add_collaborator(session_id, "user_001", "张三", "zhangsan@example.com")
        manager.create_share_link(session_id, "user_admin")
        manager.add_comment("report_001", "测试评论", "user_001", "张三")
        
        # 验证数据文件已创建
        collab_dir = workspace_path / session_id / "collaboration"
        shared_dir = workspace_path / "shared"
        comments_dir = workspace_path / "comments"
        
        assert collab_dir.exists()
        assert shared_dir.exists()
        assert comments_dir.exists()
        
        # 验证文件存在
        collab_file = collab_dir / "collaborators.json"
        links_file = shared_dir / "share_links.json"
        comments_file = comments_dir / "comments.json"
        
        assert collab_file.exists()
        assert links_file.exists()
        assert comments_file.exists()
        
        print("✅ 数据持久化测试通过")

def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("🚀 开始协作和分享功能测试")
    print("=" * 50)
    
    test_functions = [
        test_collaboration_manager_initialization,
        test_add_collaborator,
        test_remove_collaborator,
        test_create_share_link,
        test_validate_share_link,
        test_comments_functionality,
        test_activity_logging,
        test_permission_levels,
        test_data_persistence
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 失败: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果汇总:")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📈 成功率: {passed/(passed+failed)*100:.1f}%")
    print("=" * 50)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)