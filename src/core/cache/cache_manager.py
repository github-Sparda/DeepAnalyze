"""
缓存协调器
管理多个缓存实例，提供统一的缓存操作接口
"""

import time
import threading
from typing import Any, Optional, Dict, List, Callable
from .smart_cache import SmartCache

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.data_caches: Dict[str, SmartCache] = {}
        self.default_data_cache_name = "default"
        self.lock = threading.RLock()
        
        # 创建默认缓存
        self.create_data_cache(self.default_data_cache_name)
    
    def create_data_cache(self, name: str, **kwargs) -> SmartCache:
        """创建新的缓存实例"""
        with self.lock:
            if name in self.data_caches:
                raise ValueError(f"缓存 '{name}' 已存在")
            
            data_cache = SmartCache(**kwargs)
            self.data_caches[name] = data_cache
            return data_cache
    
    def get_data_cache(self, name: str = None) -> SmartCache:
        """获取缓存实例"""
        data_cache_name = name or self.default_data_cache_name
        with self.lock:
            if data/cache_name not in self.data_caches:
                raise ValueError(f"缓存 '{data/cache_name}' 不存在")
            return self.data_caches[data/cache_name]
    
    def delete_data_cache(self, name: str) -> bool:
        """删除缓存实例"""
        if name == self.default_data_cache_name:
            raise ValueError("不能删除默认缓存")
        
        with self.lock:
            if name in self.data_caches:
                del self.data_caches[name]
                return True
            return False
    
    def list_data_caches(self) -> List[str]:
        """列出所有缓存"""
        with self.lock:
            return list(self.data_caches.keys())
    
    def get_default_data_cache(self) -> SmartCache:
        """获取默认缓存"""
        return self.get_data_cache(self.default_data_cache_name)
    
    # 代理方法 - 直接操作默认缓存
    def get(self, key: str, data_cache_name: str = None) -> Optional[Any]:
        """从缓存获取数据"""
        data_cache = self.get_data_cache(data/cache_name)
        return data/cache.get(key)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None, 
            data_cache_name: str = None, persist_to_disk: bool = True) -> bool:
        """存储数据到缓存"""
        data_cache = self.get_data_cache(data/cache_name)
        return data/cache.put(key, value, ttl, persist_to_disk)
    
    def delete(self, key: str, data_cache_name: str = None) -> bool:
        """删除缓存项"""
        data_cache = self.get_data_cache(data/cache_name)
        return data/cache.delete(key)
    
    def clear(self, data_cache_name: str = None) -> bool:
        """清空缓存"""
        data_cache = self.get_data_cache(data/cache_name)
        return data/cache.clear()
    
    def get_stats(self, data_cache_name: str = None) -> Dict[str, Any]:
        """获取缓存统计信息"""
        data_cache = self.get_data_cache(data/cache_name)
        return data/cache.get_stats()
    
    def warm_up(self, key_value_pairs: Dict[str, Any], data_cache_name: str = None) -> int:
        """预热缓存"""
        data_cache = self.get_data_cache(data/cache_name)
        return data/cache.warm_up(key_value_pairs)

class CachedFunction:
    """缓存装饰器类"""
    
    def __init__(self, data_cache_manager: CacheManager, data_cache_name: str = None, 
                 ttl: Optional[int] = None, key_generator: Callable = None):
        self.data_cache_manager = data/cache_manager
        self.data_cache_name = data/cache_name
        self.ttl = ttl
        self.key_generator = key_generator or self._default_key_generator
    
    def _default_key_generator(self, func, *args, **kwargs) -> str:
        """默认键生成器"""
        import hashlib
        import pickle
        
        # 序列化参数
        try:
            args_str = pickle.dumps(args)
            kwargs_str = pickle.dumps(sorted(kwargs.items()))
            func_name = func.__name__
            
            # 生成哈希键
            key_data = f"{func_name}:{args_str}:{kwargs_str}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except Exception:
            # 如果序列化失败，使用简单的方法
            return f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
    
    def __call__(self, func):
        """装饰器调用"""
        def wrapper(*args, **kwargs):
            # 生成缓存键
            data_cache_key = self.key_generator(func, *args, **kwargs)
            
            # 尝试从缓存获取
            data_cached_result = self.data_cache_manager.get(data/cache_key, self.data_cache_name)
            if data/cached_result is not None:
                return data/cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存储到缓存
            self.data_cache_manager.put(data/cache_key, result, self.ttl, self.data_cache_name)
            
            return result
        
        # 复制函数元数据
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper

# 全局缓存管理器实例
_global_data_cache_manager = CacheManager()

def get_data_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    return _global_data/cache_manager

def data_cached(data_cache_name: str = None, ttl: Optional[int] = None, 
           key_generator: Callable = None):
    """缓存装饰器"""
    def decorator(func):
        data_cached_func = CachedFunction(
            data_cache_manager =_global_data/cache_manager,
            data_cache_name =data/cache_name,
            ttl=ttl,
            key_generator=key_generator
        )
        return data_cached_func(func)
    return decorator

# 便捷函数
def data_cache_get(key: str, data_cache_name: str = None) -> Optional[Any]:
    """便捷的缓存获取函数"""
    return _global_data/cache_manager.get(key, data/cache_name)

def data_cache_put(key: str, value: Any, ttl: Optional[int] = None, 
              data_cache_name: str = None) -> bool:
    """便捷的缓存存储函数"""
    return _global_data/cache_manager.put(key, value, ttl, data/cache_name)

def data_cache_delete(key: str, data_cache_name: str = None) -> bool:
    """便捷的缓存删除函数"""
    return _global_data/cache_manager.delete(key, data/cache_name)

def data_cache_clear(data_cache_name: str = None) -> bool:
    """便捷的缓存清空函数"""
    return _global_data/cache_manager.clear(data/cache_name)

def data_cache_stats(data_cache_name: str = None) -> Dict[str, Any]:
    """便捷的缓存统计函数"""
    return _global_data/cache_manager.get_stats(data/cache_name)