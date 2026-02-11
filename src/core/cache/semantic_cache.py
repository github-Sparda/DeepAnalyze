"""
语义相似性缓存机制
基于内容语义相似性的智能缓存系统
"""

import numpy as np
import hashlib
import time
import threading
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass
import json

# 导入语义处理相关库
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    SEMANTIC_LIBS_AVAILABLE = True
except ImportError:
    SEMANTIC_LIBS_AVAILABLE = False
    print("警告: 语义处理库未安装，语义缓存功能受限")

@dataclass
class SemanticCacheEntry:
    """语义缓存条目"""
    key: str
    original_text: str
    vector: np.ndarray
    result: Any
    timestamp: float
    access_count: int = 1

class SemanticSimilarityCache:
    """语义相似性缓存"""
    
    def __init__(self, 
                 similarity_threshold: float = 0.85,
                 max_data_cache_size: int = 1000,
                 model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """
        初始化语义缓存
        
        Args:
            similarity_threshold: 语义相似度阈值 (0-1)
            max_data_cache_size: 最大缓存条目数
            model_name: 用于语义编码的模型名称
        """
        if not SEMANTIC_LIBS_AVAILABLE:
            raise RuntimeError("缺少必要的语义处理库，请安装: sentence-transformers faiss-cpu")
        
        self.similarity_threshold = similarity_threshold
        self.max_data_cache_size = max_cache_size
        self.model_name = model_name
        
        # 初始化语义模型
        self.model = SentenceTransformer(model_name)
        
        # 初始化向量索引
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)  # 内积用于余弦相似度
        self.faiss.normalize_L2 = True  # 归一化向量
        
        # 缓存存储
        self.entries: Dict[str, SemanticCacheEntry] = {}
        self.text_to_key: Dict[str, str] = {}  # 原始文本到键的映射
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'semantic_hits': 0,
            'exact_hits': 0,
            'misses': 0,
            'data_cache_size': 0
        }
    
    def _text_to_vector(self, text: str) -> np.ndarray:
        """将文本转换为语义向量"""
        vector = self.model.encode(text, convert_to_numpy=True)
        # 确保向量是float32类型并归一化
        vector = vector.astype(np.float32)
        faiss.normalize_L2(vector.reshape(1, -1))
        return vector
    
    def _compute_key(self, text: str) -> str:
        """计算文本的唯一键"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def store(self, text: str, result: Any) -> bool:
        """
        存储文本和结果到语义缓存
        
        Args:
            text: 要缓存的文本
            result: 对应的结果
            
        Returns:
            是否存储成功
        """
        try:
            with self.lock:
                # 检查是否已存在
                key = self._compute_key(text)
                if key in self.entries:
                    # 更新现有条目
                    self.entries[key].result = result
                    self.entries[key].timestamp = time.time()
                    self.entries[key].access_count += 1
                    return True
                
                # 创建新的缓存条目
                vector = self._text_to_vector(text)
                entry = SemanticCacheEntry(
                    key=key,
                    original_text=text,
                    vector=vector,
                    result=result,
                    timestamp=time.time()
                )
                
                # 添加到缓存
                self.entries[key] = entry
                self.text_to_key[text] = key
                
                # 添加到FAISS索引
                self.index.add(vector.reshape(1, -1))
                
                # 检查缓存大小限制
                if len(self.entries) > self.max_data_cache_size:
                    self._evict_least_used()
                
                self.stats['data_cache_size'] = len(self.entries)
                return True
                
        except Exception as e:
            print(f"存储到语义缓存失败: {e}")
            return False
    
    def search_similar(self, query_text: str, top_k: int = 5) -> List[Tuple[str, float, Any]]:
        """
        搜索语义相似的缓存条目
        
        Args:
            query_text: 查询文本
            top_k: 返回最相似的k个结果
            
        Returns:
            [(原始文本, 相似度, 结果), ...] 按相似度降序排列
        """
        try:
            with self.lock:
                # 首先检查精确匹配
                exact_key = self._compute_key(query_text)
                if exact_key in self.entries:
                    self.stats['exact_hits'] += 1
                    self.stats['total_requests'] += 1
                    entry = self.entries[exact_key]
                    entry.access_count += 1
                    entry.timestamp = time.time()
                    return [(entry.original_text, 1.0, entry.result)]
                
                # 语义相似性搜索
                query_vector = self._text_to_vector(query_text)
                similarities, indices = self.index.search(query_vector.reshape(1, -1), top_k)
                
                results = []
                for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                    if idx == -1:  # FAISS返回-1表示没有更多结果
                        break
                    
                    if similarity >= self.similarity_threshold:
                        # 获取对应的条目
                        entries_list = list(self.entries.values())
                        if idx < len(entries_list):
                            entry = entries_list[idx]
                            results.append((entry.original_text, float(similarity), entry.result))
                            entry.access_count += 1
                            entry.timestamp = time.time()
                
                if results:
                    self.stats['semantic_hits'] += 1
                else:
                    self.stats['misses'] += 1
                self.stats['total_requests'] += 1
                
                return results
                
        except Exception as e:
            print(f"语义搜索失败: {e}")
            self.stats['misses'] += 1
            self.stats['total_requests'] += 1
            return []
    
    def get(self, text: str, similarity_threshold: Optional[float] = None) -> Optional[Any]:
        """
        获取语义相似的缓存结果
        
        Args:
            text: 查询文本
            similarity_threshold: 可选的相似度阈值
            
        Returns:
            缓存的结果或None
        """
        threshold = similarity_threshold or self.similarity_threshold
        similar_results = self.search_similar(text, top_k=1)
        
        if similar_results and similar_results[0][1] >= threshold:
            return similar_results[0][2]
        return None
    
    def _evict_least_used(self):
        """淘汰最少使用的缓存条目"""
        if not self.entries:
            return
        
        # 按访问次数和时间排序
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: (x[1].access_count, x[1].timestamp)
        )
        
        # 删除最旧的条目
        key_to_remove = sorted_entries[0][0]
        entry_to_remove = self.entries[key_to_remove]
        
        # 从索引中移除
        # 注意：FAISS不支持直接删除，这里简化处理
        del self.entries[key_to_remove]
        del self.text_to_key[entry_to_remove.original_text]
        
        # 重建索引（简化处理）
        self._rebuild_index()
    
    def _rebuild_index(self):
        """重建FAISS索引"""
        self.index = faiss.IndexFlatIP(self.dimension)
        vectors = np.array([entry.vector for entry in self.entries.values()])
        if len(vectors) > 0:
            self.index.add(vectors)
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.entries.clear()
            self.text_to_key.clear()
            self.index = faiss.IndexFlatIP(self.dimension)
            self.stats = {
                'total_requests': 0,
                'semantic_hits': 0,
                'exact_hits': 0,
                'misses': 0,
                'data_cache_size': 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_requests = self.stats['total_requests']
            if total_requests > 0:
                hit_rate = (self.stats['semantic_hits'] + self.stats['exact_hits']) / total_requests
            else:
                hit_rate = 0.0
            
            return {
                'total_requests': total_requests,
                'semantic_hits': self.stats['semantic_hits'],
                'exact_hits': self.stats['exact_hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'data_cache_size': len(self.entries),
                'similarity_threshold': self.similarity_threshold
            }
    
    def get_similar_texts(self, text: str, threshold: float = 0.7) -> List[str]:
        """
        获取与给定文本语义相似的已缓存文本
        
        Args:
            text: 查询文本
            threshold: 相似度阈值
            
        Returns:
            相似的文本列表
        """
        similar_results = self.search_similar(text, top_k=10)
        return [item[0] for item in similar_results if item[1] >= threshold]

# 全局语义缓存实例
_global_semantic_data_cache = None

def get_semantic_data_cache() -> SemanticSimilarityCache:
    """获取全局语义缓存实例"""
    global _global_semantic_data_cache
    if _global_semantic_data_cache is None:
        _global_semantic_data_cache = SemanticSimilarityCache()
    return _global_semantic_data_cache

# 便捷函数
def semantic_data_cache_store(text: str, result: Any) -> bool:
    """存储到语义缓存"""
    data_cache = get_semantic_data_cache()
    return data/cache.store(text, result)

def semantic_data_cache_get(text: str, threshold: Optional[float] = None) -> Optional[Any]:
    """从语义缓存获取"""
    data_cache = get_semantic_data_cache()
    return data/cache.get(text, threshold)

def semantic_data_cache_search(text: str, top_k: int = 5) -> List[Tuple[str, float, Any]]:
    """搜索语义相似项"""
    data_cache = get_semantic_data_cache()
    return data/cache.search_similar(text, top_k)

def semantic_data_cache_stats() -> Dict[str, Any]:
    """获取语义缓存统计"""
    data_cache = get_semantic_data_cache()
    return data/cache.get_stats()
