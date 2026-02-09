"""
容器池化管理系统
管理预创建的Docker容器池，提高资源利用效率
"""

import docker
import threading
import time
import queue
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@dataclass
class ContainerConfig:
    """容器配置"""
    image: str = "python:3.12-slim"
    memory_limit: str = "512m"
    cpu_quota: int = 50000  # 50% CPU
    network_disabled: bool = True
    readonly_rootfs: bool = True
    tmpfs_mounts: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tmpfs_mounts is None:
            self.tmpfs_mounts = {
                "/tmp": "rw,noexec,nosuid,size=100m",
                "/data_sessions_active": "rw,noexec,nosuid,size=200m"
            }

@dataclass
class PoolStats:
    """池统计信息"""
    total_capacity: int
    available_count: int
    busy_count: int
    active_sessions: int
    average_wait_time: float

class ContainerSession:
    """容器会话"""
    
    def __init__(self, container, session_id: str, user_id: str):
        self.container = container
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = time.time()
        self.last_access = time.time()
        self.executions = 0
        
    def update_access(self):
        """更新最后访问时间"""
        self.last_access = time.time()
        self.executions += 1
    
    def reset_state(self):
        """重置会话状态"""
        try:
            # 清理工作目录
            self.container.exec_run("rm -rf /data_sessions_active/*")
            # 重置访问计数
            self.executions = 0
            logger.info(f"会话 {self.session_id} 状态已重置")
        except Exception as e:
            logger.error(f"重置会话状态失败: {e}")

class ContainerPool:
    """容器池管理器"""
    
    def __init__(self, 
                 pool_size: int = 10,
                 config: Optional[ContainerConfig] = None,
                 session_timeout: int = 3600):
        """
        初始化容器池
        
        Args:
            pool_size: 池大小
            config: 容器配置
            session_timeout: 会话超时时间(秒)
        """
        self.pool_size = pool_size
        self.config = config or ContainerConfig()
        self.session_timeout = session_timeout
        
        # Docker客户端
        try:
            self.client = docker.from_env()
            self.client.ping()  # 测试连接
        except Exception as e:
            logger.error(f"Docker客户端初始化失败: {e}")
            raise RuntimeError("无法连接到Docker守护进程")
        
        # 池管理
        self.available_containers = queue.Queue(maxsize=pool_size)
        self.busy_containers: Dict[str, ContainerSession] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        
        # 统计和监控
        self.wait_times = []
        self.lock = threading.RLock()
        self.monitor_thread = None
        self.running = False
        
        # 初始化池
        self._initialize_pool()
        self._start_monitoring()
    
    def _initialize_pool(self):
        """初始化容器池"""
        logger.info(f"正在初始化容器池，大小: {self.pool_size}")
        
        for i in range(self.pool_size):
            try:
                container = self._create_container()
                self.available_containers.put(container)
                logger.debug(f"容器 {i+1}/{self.pool_size} 创建成功")
            except Exception as e:
                logger.error(f"创建容器 {i+1} 失败: {e}")
        
        logger.info(f"容器池初始化完成，可用容器: {self.available_containers.qsize()}")
    
    def _create_container(self):
        """创建单个容器"""
        container_name = f"src/core-worker-{uuid.uuid4().hex[:8]}"
        
        # 容器运行配置
        host_config = self.client.api.create_host_config(
            mem_limit=self.config.memory_limit,
            cpu_quota=self.config.cpu_quota,
            network_mode="none" if self.config.network_disabled else "bridge",
            readonly_rootfs=self.config.readonly_rootfs,
            tmpfs=self.config.tmpfs_mounts,
            security_opt=["no-new-privileges"]
        )
        
        # 创建容器
        container = self.client.containers.create(
            image=self.config.image,
            name=container_name,
            command="sleep infinity",  # 保持容器运行
            detach=True,
            host_config=host_config,
            working_dir="/data_sessions_active"
        )
        
        # 启动容器
        container.start()
        
        # 安装必要的Python包
        self._install_dependencies(container)
        
        return container
    
    def _install_dependencies(self, container):
        """在容器中安装依赖"""
        requirements = [
            "pandas",
            "numpy", 
            "matplotlib",
            "scikit-learn"
        ]
        
        if requirements:
            cmd = f"pip install --no-data/cache-dir {' '.join(requirements)}"
            try:
                result = container.exec_run(cmd, stream=False, timeout=300)
                if result.exit_code != 0:
                    logger.warning(f"依赖安装可能失败: {result.output}")
            except Exception as e:
                logger.warning(f"安装依赖时出错: {e}")
    
    def get_container(self, user_id: str, timeout: float = 30.0) -> ContainerSession:
        """
        获取容器会话
        
        Args:
            user_id: 用户ID
            timeout: 等待超时时间
            
        Returns:
            ContainerSession: 容器会话
        """
        start_time = time.time()
        
        # 检查是否已有会话
        with self.lock:
            if user_id in self.user_sessions:
                session_id = self.user_sessions[user_id]
                if session_id in self.busy_containers:
                    session = self.busy_containers[session_id]
                    session.update_access()
                    return session
        
        # 等待可用容器
        try:
            container = self.available_containers.get(timeout=timeout)
            wait_time = time.time() - start_time
            self.wait_times.append(wait_time)
            
            # 创建新会话
            session_id = f"session-{uuid.uuid4().hex[:12]}"
            session = ContainerSession(container, session_id, user_id)
            
            with self.lock:
                self.busy_containers[session_id] = session
                self.user_sessions[user_id] = session_id
            
            logger.info(f"为用户 {user_id} 分配会话 {session_id}")
            return session
            
        except queue.Empty:
            raise TimeoutError(f"等待容器超时 ({timeout}秒)")
    
    def release_container(self, user_id: str):
        """
        释放容器会话
        
        Args:
            user_id: 用户ID
        """
        with self.lock:
            if user_id in self.user_sessions:
                session_id = self.user_sessions[user_id]
                if session_id in self.busy_containers:
                    session = self.busy_containers[session_id]
                    
                    # 重置会话状态
                    session.reset_state()
                    
                    # 放回可用池
                    try:
                        self.available_containers.put(session.container, timeout=1.0)
                        del self.busy_containers[session_id]
                        del self.user_sessions[user_id]
                        logger.info(f"会话 {session_id} 已释放")
                    except queue.Full:
                        # 池已满，销毁容器
                        self._destroy_container(session.container)
                        del self.busy_containers[session_id]
                        del self.user_sessions[user_id]
    
    def execute_in_session(self, user_id: str, code: str, 
                          timeout: int = 60) -> Dict[str, Any]:
        """
        在会话中执行代码
        
        Args:
            user_id: 用户ID
            code: 要执行的代码
            timeout: 执行超时时间
            
        Returns:
            执行结果字典
        """
        session = self.get_container(user_id)
        try:
            # 将代码写入文件
            code_filename = f"script_{int(time.time())}.py"
            exec_cmd = f"echo '{code}' > /data_sessions_active/{code_filename} && python /data_sessions_active/{code_filename}"
            
            # 执行代码
            result = session.container.exec_run(
                cmd=["sh", "-c", exec_cmd],
                stream=False,
                timeout=timeout,
                workdir="/data_sessions_active"
            )
            
            session.update_access()
            
            return {
                'success': result.exit_code == 0,
                'stdout': result.output.decode('utf-8', errors='ignore') if result.output else "",
                'stderr': "",
                'exit_code': result.exit_code,
                'session_id': session.session_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'stdout': "",
                'stderr': str(e),
                'exit_code': -1,
                'session_id': session.session_id
            }
        finally:
            # 根据执行频率决定是否释放
            if session.executions > 10:  # 执行超过10次后释放
                self.release_container(user_id)
    
    def _destroy_container(self, container):
        """销毁容器"""
        try:
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info(f"容器 {container.name} 已销毁")
        except Exception as e:
            logger.error(f"销毁容器失败: {e}")
    
    def _start_monitoring(self):
        """启动监控线程"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._cleanup_expired_sessions()
                self._maintain_pool_size()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(60)
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []
        
        with self.lock:
            for session_id, session in self.busy_containers.items():
                if current_time - session.last_access > self.session_timeout:
                    expired_sessions.append((session_id, session.user_id))
        
        for session_id, user_id in expired_sessions:
            logger.info(f"清理过期会话: {session_id}")
            self.release_container(user_id)
    
    def _maintain_pool_size(self):
        """维护池大小"""
        with self.lock:
            available_count = self.available_containers.qsize()
            busy_count = len(self.busy_containers)
            total_active = available_count + busy_count
            
            # 如果活跃容器太少，补充容器
            if total_active < self.pool_size * 0.8:  # 低于80%时补充
                needed = self.pool_size - total_active
                for _ in range(min(needed, 2)):  # 每次最多补充2个
                    try:
                        container = self._create_container()
                        self.available_containers.put(container, timeout=1.0)
                    except Exception as e:
                        logger.error(f"补充容器失败: {e}")
                        break
    
    def get_stats(self) -> PoolStats:
        """获取池统计信息"""
        with self.lock:
            available_count = self.available_containers.qsize()
            busy_count = len(self.busy_containers)
            
            if self.wait_times:
                avg_wait_time = sum(self.wait_times[-100:]) / min(len(self.wait_times), 100)
            else:
                avg_wait_time = 0.0
            
            return PoolStats(
                total_capacity=self.pool_size,
                available_count=available_count,
                busy_count=busy_count,
                active_sessions=len(self.user_sessions),
                average_wait_time=avg_wait_time
            )
    
    def shutdown(self):
        """关闭容器池"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        # 清理所有容器
        with self.lock:
            # 清理忙碌的容器
            for session in self.busy_containers.values():
                self._destroy_container(session.container)
            
            # 清理可用的容器
            while not self.available_containers.empty():
                try:
                    container = self.available_containers.get_nowait()
                    self._destroy_container(container)
                except queue.Empty:
                    break

# 全局容器池实例
_global_container_pool = None

def get_container_pool() -> ContainerPool:
    """获取全局容器池实例"""
    global _global_container_pool
    if _global_container_pool is None:
        _global_container_pool = ContainerPool()
    return _global_container_pool

# 便捷函数
def execute_with_container(user_id: str, code: str, timeout: int = 60) -> Dict[str, Any]:
    """使用容器执行代码的便捷函数"""
    pool = get_container_pool()
    return pool.execute_in_session(user_id, code, timeout)

def get_pool_stats() -> Dict[str, Any]:
    """获取容器池统计"""
    pool = get_container_pool()
    stats = pool.get_stats()
    return {
        'total_capacity': stats.total_capacity,
        'available_count': stats.available_count,
        'busy_count': stats.busy_count,
        'active_sessions': stats.active_sessions,
        'average_wait_time': stats.average_wait_time
    }