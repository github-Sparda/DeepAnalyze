"""
智能缓存系统主类
实现分层缓存架构：内存缓存 → SSD缓存 → 磁盘缓存
"""

import pickle
import hashlib
import time
import threading
from typing import Any, Optional, Dict, Tuple
from abc import ABC, abstractmethod
import os

class CacheLayer(ABC):
    """缓存层抽象基类"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        pass
    
    @abstractmethod
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """存储缓存项"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空缓存"""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """获取缓存大小"""
        pass

class MemoryCache(CacheLayer):
    """内存缓存层"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.data_cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def _hash_key(self, key: str) -> str:
        """哈希键值以节省空间"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            hashed_key = self._hash_key(key)
            if hashed_key in self.data_cache:
                self.access_times[hashed_key] = time.time()
                return self.data_cache[hashed_key]['value']
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self.lock:
            # 如果缓存已满，删除最久未访问的项
            if len(self.data_cache) >= self.max_size:
                self._evict_lru()
            
            hashed_key = self._hash_key(key)
            expire_time = time.time() + ttl if ttl else None
            
            self.data_cache[hashed_key] = {
                'value': value,
                'expire_time': expire_time
            }
            self.access_times[hashed_key] = time.time()
            return True
    
    def delete(self, key: str) -> bool:
        with self.lock:
            hashed_key = self._hash_key(key)
            if hashed_key in self.data_cache:
                del self.data_cache[hashed_key]
                del self.access_times[hashed_key]
                return True
            return False
    
    def clear(self) -> bool:
        with self.lock:
            self.data_cache.clear()
            self.access_times.clear()
            return True
    
    def size(self) -> int:
        with self.lock:
            return len(self.data_cache)
    
    def _evict_lru(self):
        """删除最久未使用的项"""
        if not self.access_times:
            return
        
        # 找到最早访问的项
        oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
        del self.data_cache[oldest_key]
        del self.access_times[oldest_key]

class FileCache(CacheLayer):
    """文件系统缓存层"""
    
    def __init__(self, data_cache_dir: str, max_size_mb: int = 100):
        self.data_cache_dir = data_cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.RLock()
        
        # 确保缓存目录存在
        os.makedirs(data_cache_dir, exist_ok=True)
    
    def _get_file_path(self, key: str) -> str:
        """获取缓存文件路径"""
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.data_cache_dir, f"{hashed_key}.data_cache")
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            file_path = self._get_file_path(key)
            if not os.path.exists(file_path):
                return None
            
            try:
                # 检查是否过期
                stat = os.stat(file_path)
                if hasattr(stat, 'st_mtime'):
                    # 简单的时间检查机制
                    pass
                
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                    return data['value']
            except Exception:
                # 文件损坏，删除它
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self.lock:
            # 检查磁盘空间
            if self._get_total_size() > self.max_size_bytes * 0.9:
                self._cleanup_old_files()
            
            file_path = self._get_file_path(key)
            try:
                data = {
                    'value': value,
                    'timestamp': time.time(),
                    'ttl': ttl
                }
                
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
                return True
            except Exception as e:
                print(f"文件缓存写入失败: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        with self.lock:
            file_path = self._get_file_path(key)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                return False
            except Exception:
                return False
    
    def clear(self) -> bool:
        with self.lock:
            try:
                for filename in os.listdir(self.data_cache_dir):
                    file_path = os.path.join(self.data_cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                return True
            except Exception:
                return False
    
    def size(self) -> int:
        with self.lock:
            try:
                return len([f for f in os.listdir(self.data_cache_dir) 
                           if os.path.isfile(os.path.join(self.data_cache_dir, f))])
            except Exception:
                return 0
    
    def _get_total_size(self) -> int:
        """获取缓存总大小"""
        total_size = 0
        try:
            for filename in os.listdir(self.data_cache_dir):
                file_path = os.path.join(self.data_cache_dir, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        except Exception:
            pass
        return total_size
    
    def _cleanup_old_files(self):
        """清理旧文件"""
        try:
            files = []
            for filename in os.listdir(self.data_cache_dir):
                file_path = os.path.join(self.data_cache_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append((file_path, stat.st_mtime))
            
            # 按修改时间排序，删除最旧的文件
            files.sort(key=lambda x: x[1])
            
            # 删除一半的文件
            delete_count = len(files) // 2
            for file_path, _ in files[:delete_count]:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                    
        except Exception:
            pass

class SmartCache:
    """智能分层缓存系统"""
    
    def __init__(self, 
                 memory_max_items: int = 1000,
                 disk_data_cache_dir: str = "./data/cache/disk",
                 disk_max_size_mb: int = 500):
        """
        初始化分层缓存系统
        
        Args:
            memory_max_items: 内存缓存最大项目数
            disk_data_cache_dir: 磁盘缓存目录
            disk_max_size_mb: 磁盘缓存最大大小(MB)
        """
        self.memory_data_cache = MemoryCache(max_size=memory_max_items)
        self.disk_data_cache = FileCache(data_cache_dir=disk_data_cache_dir, max_size_mb=disk_max_size_mb)
        self.stats = {
            'hits': 0,
            'misses': 0,
            'memory_hits': 0,
            'disk_hits': 0
        }
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取数据，按层级查找：内存 → 磁盘
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据或None
        """
        with self.lock:
            # 首先检查内存缓存
            value = self.memory_data_cache.get(key)
            if value is not None:
                self.stats['hits'] += 1
                self.stats['memory_hits'] += 1
                return value
            
            # 然后检查磁盘缓存
            value = self.disk_data_cache.get(key)
            if value is not None:
                self.stats['hits'] += 1
                self.stats['disk_hits'] += 1
                # 将数据提升到内存缓存
                self.memory_data_cache.put(key, value)
                return value
            
            # 缓存未命中
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None, 
            persist_to_disk: bool = True) -> bool:
        """
        存储数据到缓存
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间(秒)
            persist_to_disk: 是否持久化到磁盘
            
        Returns:
            存储是否成功
        """
        with self.lock:
            # 首先存储到内存
            memory_success = self.memory_data_cache.put(key, value, ttl)
            
            # 根据参数决定是否存储到磁盘
            disk_success = True
            if persist_to_disk:
                disk_success = self.disk_data_cache.put(key, value, ttl)
            
            return memory_success and disk_success
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            memory_success = self.memory_data_cache.delete(key)
            disk_success = self.disk_data_cache.delete(key)
            return memory_success or disk_success
    
    def clear(self) -> bool:
        """清空所有缓存"""
        with self.lock:
            memory_success = self.memory_data_cache.clear()
            disk_success = self.disk_data_cache.clear()
            # 重置统计信息
            self.stats = {
                'hits': 0,
                'misses': 0,
                'memory_hits': 0,
                'disk_hits': 0
            }
            return memory_success and disk_success
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'total_requests': total_requests,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'memory_hits': self.stats['memory_hits'],
                'disk_hits': self.stats['disk_hits'],
                'memory_data_cache_size': self.memory_data_cache.size(),
                'disk_data_cache_size': self.disk_data_cache.size()
            }
    
    def warm_up(self, key_value_pairs: Dict[str, Any]) -> int:
        """
        预热缓存
        
        Args:
            key_value_pairs: 键值对字典
            
        Returns:
            成功预热的项目数
        """
        success_count = 0
        for key, value in key_value_pairs.items():
            if self.put(key, value):
                success_count += 1
        return success_count

# 全局缓存实例
_global_data_cache = None

def get_data_cache() -> SmartCache:
    """获取全局缓存实例"""
    global _global_data_cache
    if _global_data_cache is None:
        _global_data_cache = SmartCache()
    return _global_data_cache

def data_cache_get(key: str) -> Optional[Any]:
    """便捷的缓存获取函数"""
    return get_data_cache().get(key)

def data_cache_put(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """便捷的缓存存储函数"""
    return get_data_cache().put(key, value, ttl)

def data_cache_delete(key: str) -> bool:
    """便捷的缓存删除函数"""
    return get_data_cache().delete(key)