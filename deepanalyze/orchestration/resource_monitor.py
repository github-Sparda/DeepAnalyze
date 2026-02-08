"""
系统资源监控模块
实时监控CPU、内存、磁盘等系统资源使用情况
"""

import psutil
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import json

@dataclass
class ResourceMetrics:
    """资源指标数据类"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available: int  # bytes
    disk_usage_percent: float
    disk_io_read_bytes: int
    disk_io_write_bytes: int
    network_bytes_sent: int
    network_bytes_recv: int

class SystemMonitor:
    """系统资源监控器"""
    
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # 初始化基准值
        self._baseline_metrics = self._collect_metrics()
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                with self.lock:
                    self.metrics_history.append(metrics)
                time.sleep(interval)
            except Exception as e:
                print(f"监控循环错误: {e}")
                time.sleep(interval)
    
    def _collect_metrics(self) -> ResourceMetrics:
        """收集系统资源指标"""
        timestamp = time.time()
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available = memory.available
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # 磁盘IO
        disk_io = psutil.disk_io_counters()
        disk_io_read_bytes = disk_io.read_bytes if disk_io else 0
        disk_io_write_bytes = disk_io.write_bytes if disk_io else 0
        
        # 网络IO
        net_io = psutil.net_io_counters()
        network_bytes_sent = net_io.bytes_sent if net_io else 0
        network_bytes_recv = net_io.bytes_recv if net_io else 0
        
        return ResourceMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available=memory_available,
            disk_usage_percent=disk_usage_percent,
            disk_io_read_bytes=disk_io_read_bytes,
            disk_io_write_bytes=disk_io_write_bytes,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv
        )
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """获取当前资源指标"""
        with self.lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_average_metrics(self, window_size: int = 10) -> Optional[ResourceMetrics]:
        """获取平均资源指标"""
        with self.lock:
            if len(self.metrics_history) < window_size:
                return None
            
            recent_metrics = list(self.metrics_history)[-window_size:]
            
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / window_size
            avg_memory_percent = sum(m.memory_percent for m in recent_metrics) / window_size
            avg_memory_available = sum(m.memory_available for m in recent_metrics) / window_size
            avg_disk_usage = sum(m.disk_usage_percent for m in recent_metrics) / window_size
            
            return ResourceMetrics(
                timestamp=time.time(),
                cpu_percent=avg_cpu,
                memory_percent=avg_memory_percent,
                memory_available=int(avg_memory_available),
                disk_usage_percent=avg_disk_usage,
                disk_io_read_bytes=recent_metrics[-1].disk_io_read_bytes,
                disk_io_write_bytes=recent_metrics[-1].disk_io_write_bytes,
                network_bytes_sent=recent_metrics[-1].network_bytes_sent,
                network_bytes_recv=recent_metrics[-1].network_bytes_recv
            )
    
    def get_resource_pressure(self) -> Dict[str, float]:
        """获取资源压力指数 (0-1, 越接近1表示压力越大)"""
        current = self.get_current_metrics()
        if not current:
            return {'cpu': 0.0, 'memory': 0.0, 'disk': 0.0}
        
        # CPU压力：直接使用使用率
        cpu_pressure = current.cpu_percent / 100.0
        
        # 内存压力：考虑可用内存
        memory_pressure = current.memory_percent / 100.0
        
        # 磁盘压力：使用率 + IO压力
        disk_pressure = min(current.disk_usage_percent / 100.0, 0.9)  # 最大0.9
        
        return {
            'cpu': min(cpu_pressure, 1.0),
            'memory': min(memory_pressure, 1.0),
            'disk': min(disk_pressure, 1.0)
        }
    
    def get_system_health(self) -> Dict[str, str]:
        """获取系统健康状态"""
        pressure = self.get_resource_pressure()
        
        health_status = {}
        thresholds = {'good': 0.6, 'warning': 0.8, 'critical': 0.9}
        
        for resource, value in pressure.items():
            if value < thresholds['good']:
                health_status[resource] = 'good'
            elif value < thresholds['warning']:
                health_status[resource] = 'warning'
            elif value < thresholds['critical']:
                health_status[resource] = 'critical'
            else:
                health_status[resource] = 'severe'
        
        return health_status
    
    def get_history_data(self, limit: int = 50) -> List[ResourceMetrics]:
        """获取历史数据"""
        with self.lock:
            return list(self.metrics_history)[-limit:]
    
    def export_metrics(self, filepath: str):
        """导出指标数据到文件"""
        history = self.get_history_data()
        data = [
            {
                'timestamp': m.timestamp,
                'cpu_percent': m.cpu_percent,
                'memory_percent': m.memory_percent,
                'memory_available': m.memory_available,
                'disk_usage_percent': m.disk_usage_percent
            }
            for m in history
        ]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self):
        self.current_process = psutil.Process()
    
    def get_process_info(self) -> Dict[str, any]:
        """获取当前进程信息"""
        try:
            with self.current_process.oneshot():
                return {
                    'pid': self.current_process.pid,
                    'name': self.current_process.name(),
                    'status': self.current_process.status(),
                    'cpu_percent': self.current_process.cpu_percent(),
                    'memory_percent': self.current_process.memory_percent(),
                    'memory_info': dict(self.current_process.memory_info()._asdict()),
                    'num_threads': self.current_process.num_threads(),
                    'create_time': self.current_process.create_time()
                }
        except Exception as e:
            return {'error': str(e)}
    
    def get_child_processes(self) -> List[Dict[str, any]]:
        """获取子进程信息"""
        try:
            children = self.current_process.children(recursive=True)
            child_info = []
            for child in children:
                with child.oneshot():
                    child_info.append({
                        'pid': child.pid,
                        'name': child.name(),
                        'status': child.status(),
                        'cpu_percent': child.cpu_percent(),
                        'memory_percent': child.memory_percent()
                    })
            return child_info
        except Exception as e:
            return [{'error': str(e)}]

# 全局监控实例
_global_system_monitor = None
_global_process_monitor = None

def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器"""
    global _global_system_monitor
    if _global_system_monitor is None:
        _global_system_monitor = SystemMonitor()
    return _global_system_monitor

def get_process_monitor() -> ProcessMonitor:
    """获取全局进程监控器"""
    global _global_process_monitor
    if _global_process_monitor is None:
        _global_process_monitor = ProcessMonitor()
    return _global_process_monitor

# 便捷函数
def start_monitoring(interval: float = 1.0):
    """启动系统监控"""
    monitor = get_system_monitor()
    monitor.start_monitoring(interval)

def stop_monitoring():
    """停止系统监控"""
    monitor = get_system_monitor()
    monitor.stop_monitoring()

def get_current_resources() -> Optional[ResourceMetrics]:
    """获取当前资源使用情况"""
    monitor = get_system_monitor()
    return monitor.get_current_metrics()

def get_resource_pressure() -> Dict[str, float]:
    """获取资源压力指数"""
    monitor = get_system_monitor()
    return monitor.get_resource_pressure()

def get_system_health() -> Dict[str, str]:
    """获取系统健康状态"""
    monitor = get_system_monitor()
    return monitor.get_system_health()