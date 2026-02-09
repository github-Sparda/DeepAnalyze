"""
Unified State Management System for DeepAnalyze
统一的状态管理系统，支持会话级别的状态持久化和恢复
"""

from __future__ import annotations

import json
import os
import pickle
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
import uuid
import sys

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from orchestration.state import OrchestrationState
# 暂时使用默认值替代配置导入
WORKSPACE_BASE_DIR = Path.home() / "deepanalyze_workspace"


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    created_at: datetime
    last_accessed: datetime
    user_id: Optional[str] = None
    session_name: Optional[str] = None
    tags: Optional[list[str]] = None


class StateManager:
    """统一状态管理器"""
    
    def __init__(self, base_dir: str = WORKSPACE_BASE_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._data_cache: Dict[str, OrchestrationState] = {}
        self._metadata: Dict[str, SessionMetadata] = {}
        self._load_metadata()
    
    def _get_session_path(self, session_id: str) -> Path:
        """获取会话存储路径"""
        return self.base_dir / session_id
    
    def _get_state_file(self, session_id: str) -> Path:
        """获取状态文件路径"""
        session_path = self._get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path / "state.pkl"
    
    def _get_metadata_file(self, session_id: str) -> Path:
        """获取元数据文件路径"""
        session_path = self._get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path / "metadata.json"
    
    def create_session(
        self, 
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_name: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> str:
        """
        创建新会话
        
        Args:
            session_id: 会话ID，如果为None则自动生成
            user_id: 用户ID
            session_name: 会话名称
            tags: 标签列表
            
        Returns:
            会话ID
        """
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        with self._lock:
            # 创建会话目录
            session_path = self._get_session_path(session_id)
            session_path.mkdir(parents=True, exist_ok=True)
            
            # 初始化空状态
            initial_state: OrchestrationState = {
                "session_id": session_id,
                "run_id": "",
                "trace_id": "",
                "data_sessions_active_dir": str(session_path),
                "data_sessions_active_dirs": {},
                "input_files": [],
                "file_summary": "",
                "plan": "",
                "plan_json": {},
                "hypotheses": [],
                "followup_hypotheses": [],
                "code_steps": [],
                "exec_results": [],
                "docs_analysis_results": "",
                "docs_analysis_history": [],
                "data_quality": {},
                "data_quality_path": "",
                "visualization_plan": [],
                "execution_entries": [],
                "execution_retry_requested": False,
                "execution_retry_count": 0,
                "execution_retry_exhausted": False,
                "execution_errors": [],
                "report_outline": "",
                "report": "",
                "report_versions": [],
                "plan_id": "",
                "depth": 0,
                "max_depth": 1,
                "depth_prompt": "",
                "depth_decision": "",
                "should_recurse": False,
                "continuation_required": False,
                "artifacts": [],
                "visualizations": [],
                "run_summary": {},
                "errors": [],
                "telemetry": [],
                "document_manifest": {},
                "config": {}
            }
            
            # 保存初始状态
            self._save_state(session_id, initial_state)
            
            # 创建元数据
            metadata = SessionMetadata(
                session_id=session_id,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                user_id=user_id,
                session_name=session_name,
                tags=tags or []
            )
            self._metadata[session_id] = metadata
            self._save_metadata(session_id)
            
            return session_id
    
    def get_state(self, session_id: str) -> Optional[OrchestrationState]:
        """
        获取会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            状态对象，如果不存在返回None
        """
        with self._lock:
            # 先从缓存获取
            if session_id in self._data_cache:
                self._update_last_accessed(session_id)
                return self._data_cache[session_id].copy()
            
            # 从磁盘加载
            state_file = self._get_state_file(session_id)
            if state_file.exists():
                try:
                    with open(state_file, 'rb') as f:
                        state = pickle.load(f)
                    self._data_cache[session_id] = state
                    self._update_last_accessed(session_id)
                    return state.copy()
                except Exception as e:
                    print(f"Failed to load state for session {session_id}: {e}")
                    return None
            
            return None
    
    def save_state(self, session_id: str, state: OrchestrationState) -> bool:
        """
        保存会话状态
        
        Args:
            session_id: 会话ID
            state: 状态对象
            
        Returns:
            是否保存成功
        """
        with self._lock:
            try:
                self._save_state(session_id, state)
                self._data_cache[session_id] = state.copy()
                self._update_last_accessed(session_id)
                return True
            except Exception as e:
                print(f"Failed to save state for session {session_id}: {e}")
                return False
    
    def _save_state(self, session_id: str, state: OrchestrationState) -> None:
        """内部保存状态方法"""
        state_file = self._get_state_file(session_id)
        with open(state_file, 'wb') as f:
            pickle.dump(state, f)
    
    def update_state(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新会话状态的部分字段
        
        Args:
            session_id: 会话ID
            updates: 要更新的字段字典
            
        Returns:
            是否更新成功
        """
        with self._lock:
            current_state = self.get_state(session_id)
            if current_state is None:
                return False
            
            # 更新字段
            current_state.update(updates)
            
            # 保存更新后的状态
            return self.save_state(session_id, current_state)
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话及其所有数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            try:
                # 删除缓存
                self._data_cache.pop(session_id, None)
                self._metadata.pop(session_id, None)
                
                # 删除磁盘文件
                session_path = self._get_session_path(session_id)
                if session_path.exists():
                    import shutil
                    shutil.rmtree(session_path)
                
                return True
            except Exception as e:
                print(f"Failed to delete session {session_id}: {e}")
                return False
    
    def list_sessions(
        self, 
        user_id: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> list[SessionMetadata]:
        """
        列出会话
        
        Args:
            user_id: 用户ID过滤
            tags: 标签过滤
            
        Returns:
            会话元数据列表
        """
        with self._lock:
            sessions = list(self._metadata.values())
            
            # 按用户ID过滤
            if user_id:
                sessions = [s for s in sessions if s.user_id == user_id]
            
            # 按标签过滤
            if tags:
                sessions = [s for s in sessions if s.tags and any(tag in s.tags for tag in tags)]
            
            # 按最后访问时间排序
            sessions.sort(key=lambda x: x.last_accessed, reverse=True)
            
            return sessions
    
    def get_session_info(self, session_id: str) -> Optional[SessionMetadata]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话元数据
        """
        with self._lock:
            return self._metadata.get(session_id)
    
    def _update_last_accessed(self, session_id: str) -> None:
        """更新最后访问时间"""
        if session_id in self._metadata:
            self._metadata[session_id].last_accessed = datetime.now()
            self._save_metadata(session_id)
    
    def _save_metadata(self, session_id: str) -> None:
        """保存会话元数据"""
        if session_id in self._metadata:
            metadata_file = self._get_metadata_file(session_id)
            metadata_dict = asdict(self._metadata[session_id])
            # 转换datetime对象为字符串
            metadata_dict['created_at'] = metadata_dict['created_at'].isoformat()
            metadata_dict['last_accessed'] = metadata_dict['last_accessed'].isoformat()
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
    
    def _load_metadata(self) -> None:
        """加载所有会话元数据"""
        try:
            for session_dir in self.base_dir.iterdir():
                if session_dir.is_dir() and session_dir.name.startswith('session_'):
                    metadata_file = session_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata_dict = json.load(f)
                            
                            # 转换字符串为datetime对象
                            metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
                            metadata_dict['last_accessed'] = datetime.fromisoformat(metadata_dict['last_accessed'])
                            
                            metadata = SessionMetadata(**metadata_dict)
                            self._metadata[metadata.session_id] = metadata
                        except Exception as e:
                            print(f"Failed to load metadata for {session_dir.name}: {e}")
        except Exception as e:
            print(f"Failed to load session metadata: {e}")


# 全局状态管理器实例
state_manager = StateManager()


def get_state_manager() -> StateManager:
    """获取全局状态管理器实例"""
    return state_manager


def create_new_session(
    user_id: Optional[str] = None,
    session_name: Optional[str] = None,
    tags: Optional[list[str]] = None
) -> str:
    """
    便捷函数：创建新会话
    
    Returns:
        会话ID
    """
    manager = get_state_manager()
    return manager.create_session(user_id=user_id, session_name=session_name, tags=tags)


def get_session_state(session_id: str) -> Optional[OrchestrationState]:
    """
    便捷函数：获取会话状态
    
    Returns:
        状态对象
    """
    manager = get_state_manager()
    return manager.get_state(session_id)


def save_session_state(session_id: str, state: OrchestrationState) -> bool:
    """
    便捷函数：保存会话状态
    
    Returns:
        是否保存成功
    """
    manager = get_state_manager()
    return manager.save_state(session_id, state)


def update_session_state(session_id: str, updates: Dict[str, Any]) -> bool:
    """
    便捷函数：更新会话状态
    
    Returns:
        是否更新成功
    """
    manager = get_state_manager()
    return manager.update_state(session_id, updates)