"""
动态并行度调度器
根据系统资源状况动态调整并发任务数量
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import math

from .resource_monitor import get_system_monitor, ResourceMetrics

class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    priority: TaskPriority
    resource_requirements: Dict[str, float]  # cpu, memory, disk需求
    estimated_duration: float  # 预估执行时间(秒)
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = "pending"  # pending, running, completed, failed

class DynamicScheduler:
    """动态并行度调度器"""
    
    def __init__(self, 
                 max_workers: int = 8,
                 min_workers: int = 1,
                 resource_thresholds: Optional[Dict[str, float]] = None,
                 adaptation_interval: float = 2.0):
        """
        初始化调度器
        
        Args:
            max_workers: 最大并发工作者数
            min_workers: 最小并发工作者数
            resource_thresholds: 资源阈值 {'cpu': 0.8, 'memory': 0.7, 'disk': 0.85}
            adaptation_interval: 自适应调整间隔(秒)
        """
        self.max_workers = max_workers
        self.min_workers = min_workers
        self.resource_thresholds = resource_thresholds or {
            'cpu': 0.75,
            'memory': 0.7,
            'disk': 0.8
        }
        self.adaptation_interval = adaptation_interval
        
        # 运行时状态
        self.current_workers = min_workers
        self.target_workers = min_workers
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.task_queue: List[TaskInfo] = []
        self.completed_tasks: List[TaskInfo] = []
        
        # 监控和适应
        self.system_monitor = get_system_monitor()
        self.adapting = False
        self.scheduler_thread = None
        self.running = False
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'worker_adjustments': 0,
            'last_adjustment_time': time.time()
        }
        
        self.lock = threading.RLock()
    
    def start(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        self.system_monitor.start_monitoring(1.0)
        
        # 启动自适应线程
        self.scheduler_thread = threading.Thread(
            target=self._adaptation_loop,
            daemon=True
        )
        self.scheduler_thread.start()
        
        print(f"动态调度器已启动，初始工作者数: {self.current_workers}")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        self.system_monitor.stop_monitoring()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5.0)
        
        # 等待所有任务完成
        self._wait_for_tasks_completion()
        print("动态调度器已停止")
    
    def submit_task(self, 
                   task_func: Callable,
                   task_id: str,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   resource_requirements: Optional[Dict[str, float]] = None,
                   estimated_duration: float = 10.0) -> str:
        """
        提交任务
        
        Args:
            task_func: 任务函数
            task_id: 任务ID
            priority: 任务优先级
            resource_requirements: 资源需求
            estimated_duration: 预估执行时间
            
        Returns:
            任务ID
        """
        if not self.running:
            raise RuntimeError("调度器未运行")
        
        # 默认资源需求
        if resource_requirements is None:
            resource_requirements = {'cpu': 0.1, 'memory': 0.1, 'disk': 0.05}
        
        task_info = TaskInfo(
            task_id=task_id,
            priority=priority,
            resource_requirements=resource_requirements,
            estimated_duration=estimated_duration,
            created_at=time.time()
        )
        
        with self.lock:
            self.task_queue.append(task_info)
            self.stats['total_tasks'] += 1
            self._sort_task_queue()
        
        # 尝试立即调度
        self._attemporaryt_schedule()
        
        return task_id
    
    def _sort_task_queue(self):
        """对任务队列排序（优先级优先）"""
        self.task_queue.sort(key=lambda x: (
            -x.priority.value,  # 优先级高的在前
            x.created_at       # 相同优先级按创建时间排序
        ))
    
    def _attemporaryt_schedule(self):
        """尝试调度任务"""
        with self.lock:
            # 计算可调度的任务数
            available_slots = self.current_workers - len(self.active_tasks)
            
            if available_slots <= 0:
                return
            
            # 按优先级调度任务
            scheduled_count = 0
            i = 0
            while i < len(self.task_queue) and scheduled_count < available_slots:
                task = self.task_queue[i]
                
                # 检查资源是否足够
                if self._check_resource_availability(task):
                    # 移除任务并开始执行
                    self.task_queue.pop(i)
                    self._start_task(task)
                    scheduled_count += 1
                else:
                    i += 1
    
    def _check_resource_availability(self, task: TaskInfo) -> bool:
        """检查资源是否足够执行任务"""
        current_resources = self.system_monitor.get_resource_pressure()
        
        # 检查各项资源
        for resource, threshold in self.resource_thresholds.items():
            if resource in task.resource_requirements:
                required = task.resource_requirements[resource]
                current_usage = current_resources.get(resource, 0)
                # 预留一些资源余量
                if current_usage + required > threshold * 0.9:
                    return False
        
        return True
    
    def _start_task(self, task: TaskInfo):
        """开始执行任务"""
        task.status = "running"
        task.started_at = time.time()
        
        with self.lock:
            self.active_tasks[task.task_id] = task
        
        # 在新线程中执行任务
        thread = threading.Thread(
            target=self._execute_task,
            args=(task,),
            daemon=True
        )
        thread.start()
    
    def _execute_task(self, task: TaskInfo):
        """执行任务"""
        try:
            # 这里应该是实际的任务执行逻辑
            # 为了演示，我们模拟任务执行
            time.sleep(min(task.estimated_duration, 5.0))  # 限制最大执行时间
            
            # 模拟随机成功/失败
            import random
            success = random.random() > 0.1  # 90%成功率
            
            with self.lock:
                task.completed_at = time.time()
                task.status = "completed" if success else "failed"
                
                if success:
                    self.stats['completed_tasks'] += 1
                else:
                    self.stats['failed_tasks'] += 1
                
                # 移动到完成列表
                completed_task = self.active_tasks.pop(task.task_id, None)
                if completed_task:
                    self.completed_tasks.append(completed_task)
                
                # 尝试调度新任务
                self._attemporaryt_schedule()
                
        except Exception as e:
            with self.lock:
                task.completed_at = time.time()
                task.status = "failed"
                task.error = str(e)
                self.stats['failed_tasks'] += 1
                self.active_tasks.pop(task.task_id, None)
                self._attemporaryt_schedule()
    
    def _adaptation_loop(self):
        """自适应调整循环"""
        while self.running:
            try:
                if not self.adapting:
                    self._adapt_worker_count()
                time.sleep(self.adaptation_interval)
            except Exception as e:
                print(f"自适应循环错误: {e}")
                time.sleep(self.adaptation_interval)
    
    def _adapt_worker_count(self):
        """自适应调整工作者数量"""
        self.adapting = True
        try:
            # 获取系统资源压力
            pressure = self.system_monitor.get_resource_pressure()
            health = self.system_monitor.get_system_health()
            
            # 计算目标工作者数
            target = self._calculate_target_workers(pressure, health)
            
            # 平滑调整
            if target != self.target_workers:
                self.target_workers = target
                self.stats['worker_adjustments'] += 1
                self.stats['last_adjustment_time'] = time.time()
                
                # 逐步调整当前工作者数
                if self.target_workers > self.current_workers:
                    self.current_workers = min(
                        self.current_workers + 1, 
                        self.target_workers
                    )
                elif self.target_workers < self.current_workers:
                    self.current_workers = max(
                        self.current_workers - 1, 
                        self.target_workers
                    )
                
                print(f"工作者数调整: {self.current_workers} (目标: {self.target_workers})")
                print(f"资源压力: CPU={pressure['cpu']:.2f}, "
                      f"内存={pressure['memory']:.2f}, "
                      f"磁盘={pressure['disk']:.2f}")
            
        finally:
            self.adapting = False
    
    def _calculate_target_workers(self, pressure: Dict[str, float], 
                                health: Dict[str, str]) -> int:
        """计算目标工作者数量"""
        # 基于资源压力计算
        cpu_factor = 1.0 - pressure['cpu']
        memory_factor = 1.0 - pressure['memory']
        disk_factor = 1.0 - pressure['disk']
        
        # 综合因子
        combined_factor = (cpu_factor + memory_factor + disk_factor) / 3
        
        # 计算目标工作者数
        target = max(
            self.min_workers,
            min(
                self.max_workers,
                int(self.max_workers * combined_factor)
            )
        )
        
        # 考虑系统健康状态的额外调整
        severe_resources = sum(1 for status in health.values() if status in ['critical', 'severe'])
        if severe_resources > 0:
            target = max(self.min_workers, target - severe_resources)
        
        return target
    
    def _wait_for_tasks_completion(self):
        """等待所有任务完成"""
        while self.active_tasks:
            time.sleep(0.1)
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        with self.lock:
            return {
                'current_workers': self.current_workers,
                'target_workers': self.target_workers,
                'active_tasks': len(self.active_tasks),
                'pending_tasks': len(self.task_queue),
                'completed_tasks': len(self.completed_tasks),
                'stats': self.stats.copy(),
                'resource_pressure': self.system_monitor.get_resource_pressure()
            }
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取活跃任务信息"""
        with self.lock:
            return [
                {
                    'task_id': task.task_id,
                    'priority': task.priority.name,
                    'status': task.status,
                    'duration': (time.time() - task.started_at) if task.started_at else 0
                }
                for task in self.active_tasks.values()
            ]

# 全局调度器实例
_global_scheduler = None

def get_scheduler() -> DynamicScheduler:
    """获取全局调度器"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = DynamicScheduler()
    return _global_scheduler

# 便捷函数
def start_scheduler():
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.start()

def stop_scheduler():
    """停止全局调度器"""
    scheduler = get_scheduler()
    scheduler.stop()

def submit_task(task_func, task_id: str, **kwargs) -> str:
    """提交任务到全局调度器"""
    scheduler = get_scheduler()
    return scheduler.submit_task(task_func, task_id, **kwargs)

def get_scheduler_status() -> Dict[str, Any]:
    """获取调度器状态"""
    scheduler = get_scheduler()
    return scheduler.get_status()