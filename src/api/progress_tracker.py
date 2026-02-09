"""
进度跟踪系统核心模块
提供实时进度监控和状态更新功能
"""

import time
import threading
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

class ProgressStatus(Enum):
    """进度状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProgressEvent:
    """进度事件"""
    event_id: str
    task_id: str
    status: ProgressStatus
    progress: float  # 0.0 - 1.0
    message: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TaskProgress:
    """任务进度信息"""
    task_id: str
    task_name: str
    status: ProgressStatus
    progress: float
    start_time: float
    last_update: float
    estimated_time_remaining: Optional[float] = None
    events: List[ProgressEvent] = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.listeners: List[Callable] = []
        self.lock = threading.RLock()
        
    def create_task(self, task_name: str, task_id: Optional[str] = None) -> str:
        """创建新任务"""
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        with self.lock:
            if task_id in self.tasks:
                raise ValueError(f"任务ID已存在: {task_id}")
            
            task_progress = TaskProgress(
                task_id=task_id,
                task_name=task_name,
                status=ProgressStatus.PENDING,
                progress=0.0,
                start_time=time.time(),
                last_update=time.time()
            )
            
            self.tasks[task_id] = task_progress
            self._emit_event(task_id, ProgressStatus.PENDING, 0.0, f"任务 {task_name} 已创建")
            
            return task_id
    
    def start_task(self, task_id: str) -> bool:
        """开始任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != ProgressStatus.PENDING:
                return False
            
            task.status = ProgressStatus.RUNNING
            task.last_update = time.time()
            self._emit_event(task_id, ProgressStatus.RUNNING, 0.0, f"任务 {task.task_name} 开始执行")
            return True
    
    def update_progress(self, task_id: str, progress: float, message: str = "", 
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新任务进度"""
        if not 0.0 <= progress <= 1.0:
            raise ValueError("进度值必须在0.0-1.0之间")
        
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != ProgressStatus.RUNNING:
                return False
            
            # 更新进度
            old_progress = task.progress
            task.progress = progress
            task.last_update = time.time()
            
            # 估算剩余时间
            if progress > 0 and progress > old_progress:
                elapsed_time = time.time() - task.start_time
                estimated_total_time = elapsed_time / progress
                task.estimated_time_remaining = estimated_total_time - elapsed_time
            
            # 记录事件
            self._emit_event(task_id, ProgressStatus.RUNNING, progress, message, metadata)
            return True
    
    def complete_task(self, task_id: str, message: str = "") -> bool:
        """完成任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = ProgressStatus.COMPLETED
            task.progress = 1.0
            task.last_update = time.time()
            task.estimated_time_remaining = 0.0
            
            self._emit_event(task_id, ProgressStatus.COMPLETED, 1.0, 
                           message or f"任务 {task.task_name} 完成")
            return True
    
    def fail_task(self, task_id: str, error_message: str = "", 
                  error_details: Optional[Dict[str, Any]] = None) -> bool:
        """标记任务失败"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = ProgressStatus.FAILED
            task.last_update = time.time()
            
            metadata = error_details or {}
            metadata['error'] = error_message
            
            self._emit_event(task_id, ProgressStatus.FAILED, task.progress, 
                           error_message, metadata)
            return True
    
    def cancel_task(self, task_id: str, message: str = "") -> bool:
        """取消任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = ProgressStatus.CANCELLED
            task.last_update = time.time()
            
            self._emit_event(task_id, ProgressStatus.CANCELLED, task.progress,
                           message or f"任务 {task.task_name} 已取消")
            return True
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskProgress]:
        """获取所有任务"""
        with self.lock:
            return list(self.tasks.values())
    
    def get_active_tasks(self) -> List[TaskProgress]:
        """获取活跃任务（运行中）"""
        with self.lock:
            return [task for task in self.tasks.values() 
                   if task.status == ProgressStatus.RUNNING]
    
    def add_listener(self, listener: Callable[[ProgressEvent], None]):
        """添加进度监听器"""
        with self.lock:
            self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[ProgressEvent], None]) -> bool:
        """移除进度监听器"""
        with self.lock:
            try:
                self.listeners.remove(listener)
                return True
            except ValueError:
                return False
    
    def _emit_event(self, task_id: str, status: ProgressStatus, progress: float, 
                   message: str, metadata: Optional[Dict[str, Any]] = None):
        """发出进度事件"""
        event = ProgressEvent(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            status=status,
            progress=progress,
            message=message,
            timestamp=time.time(),
            metadata=metadata
        )
        
        # 更新任务事件列表
        if task_id in self.tasks:
            self.tasks[task_id].events.append(event)
            # 保持最近的事件
            if len(self.tasks[task_id].events) > 50:
                self.tasks[task_id].events = self.tasks[task_id].events[-30:]
        
        # 通知所有监听器
        for listener in self.listeners[:]:  # 复制列表以防修改
            try:
                listener(event)
            except Exception as e:
                print(f"监听器执行错误: {e}")

class ProgressAggregator:
    """进度聚合器 - 用于跟踪多个子任务的整体进度"""
    
    def __init__(self, tracker: ProgressTracker, parent_task_id: str):
        self.tracker = tracker
        self.parent_task_id = parent_task_id
        self.sub_tasks: Dict[str, float] = {}  # task_id -> weight
        self.total_weight = 0.0
    
    def add_sub_task(self, task_id: str, weight: float = 1.0):
        """添加子任务"""
        self.sub_tasks[task_id] = weight
        self.total_weight += weight
    
    def update_sub_task_progress(self, task_id: str, progress: float):
        """更新子任务进度并计算整体进度"""
        if task_id not in self.sub_tasks:
            return
        
        # 计算加权进度
        weighted_progress = 0.0
        for sub_task_id, weight in self.sub_tasks.items():
            if sub_task_id == task_id:
                sub_progress = progress
            else:
                sub_task = self.tracker.get_task_progress(sub_task_id)
                sub_progress = sub_task.progress if sub_task else 0.0
            
            weighted_progress += sub_progress * weight
        
        if self.total_weight > 0:
            overall_progress = weighted_progress / self.total_weight
            self.tracker.update_progress(
                self.parent_task_id, 
                overall_progress,
                f"处理子任务 {task_id}"
            )

# 全局进度跟踪器实例
_global_progress_tracker = ProgressTracker()

def get_progress_tracker() -> ProgressTracker:
    """获取全局进度跟踪器"""
    return _global_progress_tracker

# 便捷函数
def create_task(task_name: str, task_id: Optional[str] = None) -> str:
    """创建任务"""
    return _global_progress_tracker.create_task(task_name, task_id)

def start_task(task_id: str) -> bool:
    """开始任务"""
    return _global_progress_tracker.start_task(task_id)

def update_progress(task_id: str, progress: float, message: str = "") -> bool:
    """更新进度"""
    return _global_progress_tracker.update_progress(task_id, progress, message)

def complete_task(task_id: str, message: str = "") -> bool:
    """完成任务"""
    return _global_progress_tracker.complete_task(task_id, message)

def fail_task(task_id: str, error_message: str = "") -> bool:
    """标记任务失败"""
    return _global_progress_tracker.fail_task(task_id, error_message)

def get_task_progress(task_id: str) -> Optional[TaskProgress]:
    """获取任务进度"""
    return _global_progress_tracker.get_task_progress(task_id)