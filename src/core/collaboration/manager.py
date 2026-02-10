"""
Collaboration and Sharing System for DeepAnalyze
协作和分享系统
"""

from __future__ import annotations

import json
import secrets
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from ..error.handler import ErrorHandler, ErrorSeverity, ErrorCategory
from ..state.manager import get_session_state, update_session_state


class PermissionLevel(Enum):
    """权限等级"""
    OWNER = "owner"           # 所有者（完全控制）
    ADMIN = "admin"           # 管理员（管理权限）
    EDITOR = "editor"         # 编辑者（读写权限）
    VIEWER = "viewer"         # 查看者（只读权限）
    COMMENTER = "commenter"   # 评论者（读写评论）


class ShareType(Enum):
    """分享类型"""
    PUBLIC = "public"         # 公开分享
    PRIVATE = "private"       # 私密分享
    LINK = "link"            # 链接分享
    INVITE = "invite"        # 邀请分享


@dataclass
class Collaborator:
    """协作者信息"""
    user_id: str
    username: str
    email: Optional[str] = None
    permission_level: PermissionLevel = PermissionLevel.VIEWER
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class ShareLink:
    """分享链接"""
    link_id: str
    share_token: str
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    permission_level: PermissionLevel = PermissionLevel.VIEWER
    max_views: Optional[int] = None
    view_count: int = 0
    is_active: bool = True


@dataclass
class Comment:
    """评论"""
    comment_id: str
    content: str
    author_id: str
    author_name: str
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[str] = None  # 支持回复功能
    is_edited: bool = False
    is_deleted: bool = False


@dataclass
class ActivityLog:
    """活动日志"""
    log_id: str
    user_id: str
    username: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class CollaborationManager:
    """协作管理器"""
    
    def __init__(self, data_sessions_active_base: str = "data_sessions_active"):
        self.data_sessions_active_base = Path(data_sessions_active_base)
        self.error_handler = ErrorHandler()
        self.share_links: Dict[str, ShareLink] = {}
        self.collaborators: Dict[str, List[Collaborator]] = {}
        self.comments: Dict[str, List[Comment]] = {}
        self.activity_outputs_logs: List[ActivityLog] = []
    
    def add_collaborator(
        self,
        session_id: str,
        user_id: str,
        username: str,
        email: Optional[str] = None,
        permission_level: PermissionLevel = PermissionLevel.VIEWER
    ) -> bool:
        """添加协作者"""
        try:
            # 检查是否已是协作者
            if session_id not in self.collaborators:
                self.collaborators[session_id] = []
            
            existing_collaborators = [c.user_id for c in self.collaborators[session_id]]
            if user_id in existing_collaborators:
                # 更新权限
                for collab in self.collaborators[session_id]:
                    if collab.user_id == user_id:
                        collab.permission_level = permission_level
                        collab.last_active = datetime.now()
                        break
            else:
                # 添加新协作者
                collaborator = Collaborator(
                    user_id=user_id,
                    username=username,
                    email=email,
                    permission_level=permission_level
                )
                self.collaborators[session_id].append(collaborator)
            
            # 记录活动日志
            self._log_activity(
                user_id=user_id,
                username=username,
                action="add_collaborator",
                resource_type="session",
                resource_id=session_id,
                details={"permission_level": permission_level.value}
            )
            
            # 保存到文件
            self._save_collaboration_data(session_id)
            
            return True
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "user_id": user_id}
            )
            return False
    
    def remove_collaborator(self, session_id: str, user_id: str) -> bool:
        """移除协作者"""
        try:
            if session_id in self.collaborators:
                self.collaborators[session_id] = [
                    c for c in self.collaborators[session_id] 
                    if c.user_id != user_id
                ]
                
                # 记录活动日志
                self._log_activity(
                    user_id=user_id,
                    username="Unknown",
                    action="remove_collaborator",
                    resource_type="session",
                    resource_id=session_id
                )
                
                # 保存到文件
                self._save_collaboration_data(session_id)
            
            return True
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "user_id": user_id}
            )
            return False
    
    def get_collaborators(self, session_id: str) -> List[Collaborator]:
        """获取协作者列表"""
        return self.collaborators.get(session_id, [])
    
    def create_share_link(
        self,
        session_id: str,
        created_by: str,
        permission_level: PermissionLevel = PermissionLevel.VIEWER,
        expires_in_hours: Optional[int] = None,
        max_views: Optional[int] = None
    ) -> Optional[ShareLink]:
        """创建分享链接"""
        try:
            # 生成唯一的链接ID和令牌
            link_id = f"link_{int(time.time())}_{secrets.token_hex(4)}"
            share_token = secrets.token_urlsafe(32)
            
            # 计算过期时间
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.now().replace(microsecond=0) + \
                           timedelta(hours=expires_in_hours)
            
            # 创建分享链接
            share_link = ShareLink(
                link_id=link_id,
                share_token=share_token,
                created_by=created_by,
                created_at=datetime.now().replace(microsecond=0),
                expires_at=expires_at,
                permission_level=permission_level,
                max_views=max_views,
                view_count=0,
                is_active=True
            )
            
            self.share_links[link_id] = share_link
            
            # 记录活动日志
            self._log_activity(
                user_id=created_by,
                username="Unknown",
                action="create_share_link",
                resource_type="session",
                resource_id=session_id,
                details={
                    "permission_level": permission_level.value,
                    "expires_in_hours": expires_in_hours,
                    "max_views": max_views
                }
            )
            
            # 保存分享链接数据
            self._save_share_links()
            
            return share_link
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"session_id": session_id, "created_by": created_by}
            )
            return None
    
    def validate_share_link(self, link_id: str, share_token: str) -> Optional[ShareLink]:
        """验证分享链接"""
        try:
            if link_id not in self.share_links:
                return None
            
            share_link = self.share_links[link_id]
            
            # 检查令牌是否匹配
            if share_link.share_token != share_token:
                return None
            
            # 检查是否激活
            if not share_link.is_active:
                return None
            
            # 检查是否过期
            if share_link.expires_at and datetime.now() > share_link.expires_at:
                share_link.is_active = False
                self._save_share_links()
                return None
            
            # 检查查看次数限制
            if share_link.max_views and share_link.view_count >= share_link.max_views:
                share_link.is_active = False
                self._save_share_links()
                return None
            
            # 增加查看次数
            share_link.view_count += 1
            self._save_share_links()
            
            return share_link
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"link_id": link_id}
            )
            return None
    
    def add_comment(
        self,
        resource_id: str,
        content: str,
        author_id: str,
        author_name: str,
        parent_id: Optional[str] = None
    ) -> Optional[Comment]:
        """添加评论"""
        try:
            comment_id = f"comment_{int(time.time())}_{secrets.token_hex(4)}"
            
            comment = Comment(
                comment_id=comment_id,
                content=content,
                author_id=author_id,
                author_name=author_name,
                created_at=datetime.now().replace(microsecond=0),
                updated_at=datetime.now().replace(microsecond=0),
                parent_id=parent_id,
                is_edited=False,
                is_deleted=False
            )
            
            if resource_id not in self.comments:
                self.comments[resource_id] = []
            
            self.comments[resource_id].append(comment)
            
            # 记录活动日志
            self._log_activity(
                user_id=author_id,
                username=author_name,
                action="add_comment",
                resource_type="resource",
                resource_id=resource_id,
                details={"parent_id": parent_id, "content_length": len(content)}
            )
            
            # 保存评论数据
            self._save_comments()
            
            return comment
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={
                    "resource_id": resource_id,
                    "author_id": author_id,
                    "content_length": len(content)
                }
            )
            return None
    
    def get_comments(self, resource_id: str) -> List[Comment]:
        """获取资源的评论"""
        comments = self.comments.get(resource_id, [])
        # 过滤掉已删除的评论
        return [c for c in comments if not c.is_deleted]
    
    def edit_comment(
        self,
        comment_id: str,
        new_content: str,
        editor_id: str
    ) -> bool:
        """编辑评论"""
        try:
            # 查找并更新评论
            for resource_id, comments in self.comments.items():
                for comment in comments:
                    if comment.comment_id == comment_id:
                        comment.content = new_content
                        comment.updated_at = datetime.now().replace(microsecond=0)
                        comment.is_edited = True
                        
                        # 记录活动日志
                        self._log_activity(
                            user_id=editor_id,
                            username="Unknown",
                            action="edit_comment",
                            resource_type="comment",
                            resource_id=comment_id,
                            details={"new_content_length": len(new_content)}
                        )
                        
                        self._save_comments()
                        return True
            
            return False
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"comment_id": comment_id, "editor_id": editor_id}
            )
            return False
    
    def delete_comment(self, comment_id: str, deleter_id: str) -> bool:
        """删除评论"""
        try:
            for resource_id, comments in self.comments.items():
                for comment in comments:
                    if comment.comment_id == comment_id:
                        comment.is_deleted = True
                        
                        # 记录活动日志
                        self._log_activity(
                            user_id=deleter_id,
                            username="Unknown",
                            action="delete_comment",
                            resource_type="comment",
                            resource_id=comment_id
                        )
                        
                        self._save_comments()
                        return True
            
            return False
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXECUTION,
                context={"comment_id": comment_id, "deleter_id": deleter_id}
            )
            return False
    
    def get_activity_outputs_logs(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50
    ) -> List[ActivityLog]:
        """获取活动日志"""
        filtered_outputs_logs = self.activity_outputs_logs
        
        if user_id:
            filtered_outputs_logs = [log for log in filtered_outputs_logs if log.user_id == user_id]
        
        if resource_type:
            filtered_outputs_logs = [log for log in filtered_outputs_logs if log.resource_type == resource_type]
        
        # 按时间倒序排列并限制数量
        filtered_outputs_logs.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_outputs_logs[:limit]
    
    def _log_activity(
        self,
        user_id: str,
        username: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录活动日志"""
        log_entry = ActivityLog(
            log_id=f"log_{int(time.time())}_{secrets.token_hex(4)}",
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.now().replace(microsecond=0),
            details=details or {}
        )
        
        self.activity_outputs_logs.append(log_entry)
        
        # 限制日志数量
        if len(self.activity_outputs_logs) > 1000:
            self.activity_outputs_logs = self.activity_outputs_logs[-1000:]
    
    def _save_collaboration_data(self, session_id: str):
        """保存协作数据到文件"""
        try:
            collab_dir = self.data_sessions_active_base / session_id / "collaboration"
            collab_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存协作者数据
            if session_id in self.collaborators:
                collaborators_data = [
                    {
                        "user_id": c.user_id,
                        "username": c.username,
                        "email": c.email,
                        "permission_level": c.permission_level.value,
                        "joined_at": c.joined_at.isoformat(),
                        "last_active": c.last_active.isoformat()
                    }
                    for c in self.collaborators[session_id]
                ]
                
                collab_file = collab_dir / "collaborators.json"
                collab_file.write_text(
                    json.dumps(collaborators_data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.FILESYSTEM,
                context={"session_id": session_id}
            )
    
    def _save_share_links(self):
        """保存分享链接数据"""
        try:
            collab_dir = self.data_sessions_active_base / "shared"
            collab_dir.mkdir(parents=True, exist_ok=True)
            
            share_links_data = [
                {
                    "link_id": sl.link_id,
                    "share_token": sl.share_token,
                    "created_by": sl.created_by,
                    "created_at": sl.created_at.isoformat(),
                    "expires_at": sl.expires_at.isoformat() if sl.expires_at else None,
                    "permission_level": sl.permission_level.value,
                    "max_views": sl.max_views,
                    "view_count": sl.view_count,
                    "is_active": sl.is_active
                }
                for sl in self.share_links.values()
            ]
            
            links_file = collab_dir / "share_links.json"
            links_file.write_text(
                json.dumps(share_links_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.FILESYSTEM
            )
    
    def _save_comments(self):
        """保存评论数据"""
        try:
            collab_dir = self.data_sessions_active_base / "comments"
            collab_dir.mkdir(parents=True, exist_ok=True)
            
            # 按资源组织评论数据
            comments_by_resource = {}
            for resource_id, comments in self.comments.items():
                comments_by_resource[resource_id] = [
                    {
                        "comment_id": c.comment_id,
                        "content": c.content,
                        "author_id": c.author_id,
                        "author_name": c.author_name,
                        "created_at": c.created_at.isoformat(),
                        "updated_at": c.updated_at.isoformat(),
                        "parent_id": c.parent_id,
                        "is_edited": c.is_edited,
                        "is_deleted": c.is_deleted
                    }
                    for c in comments
                ]
            
            comments_file = collab_dir / "comments.json"
            comments_file.write_text(
                json.dumps(comments_by_resource, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.FILESYSTEM
            )


# 便捷函数
def get_collaboration_manager(data_sessions_active_base: str = "data_sessions_active") -> CollaborationManager:
    """获取协作管理器实例"""
    return CollaborationManager(data_sessions_active_base)


def add_session_collaborator(
    session_id: str,
    user_id: str,
    username: str,
    email: Optional[str] = None,
    permission_level: PermissionLevel = PermissionLevel.VIEWER
) -> bool:
    """便捷函数：添加会话协作者"""
    manager = get_collaboration_manager()
    return manager.add_collaborator(session_id, user_id, username, email, permission_level)


def create_session_share_link(
    session_id: str,
    created_by: str,
    permission_level: PermissionLevel = PermissionLevel.VIEWER,
    expires_in_hours: Optional[int] = None,
    max_views: Optional[int] = None
) -> Optional[ShareLink]:
    """便捷函数：创建会话分享链接"""
    manager = get_collaboration_manager()
    return manager.create_share_link(session_id, created_by, permission_level, expires_in_hours, max_views)
