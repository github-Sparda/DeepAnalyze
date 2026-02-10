#!/usr/bin/env python3
"""
语义缓存功能测试脚本
"""

import sys
import os
import time

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_root = os.path.join(project_root, "src")
if src_root not in sys.path:
    sys.path.insert(0, src_root)

def test_semantic_cache():
    """测试语义缓存功能"""
    print("🚀 开始语义缓存测试...")

    enabled = os.environ.get("DEEPANALYZE_SEMANTIC_CACHE_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        print("⚠️  语义缓存未启用，跳过测试。")
        return True
    
    try:
        from core.cache.semantic_cache import SemanticCache
        
        # 创建语义缓存实例
        print("\n=== 创建语义缓存实例 ===")
        semantic_cache = SemanticCache(similarity_threshold=0.7, max_cache_size=10)
        print("✅ 语义缓存实例创建成功")
        
        # 存储测试数据
        print("\n=== 存储测试数据 ===")
        test_entries = [
            ("计算用户年龄的平均值", {"operation": "mean", "field": "age", "value": 32.5}),
            ("求用户年龄的均值和标准差", {"operation": "stats", "field": "age", "mean": 32.5, "std": 8.2}),
            ("分析销售额的时间趋势", {"operation": "trend", "field": "sales", "direction": "increasing"}),
            ("找出价格最高的商品", {"operation": "max", "field": "price", "product": "iPhone", "value": 9999})
        ]
        
        for text, result in test_entries:
            success = semantic_cache.store(text, result)
            print(f"  存储 '{text}': {'✅' if success else '❌'}")
        
        # 测试语义搜索
        print("\n=== 语义相似性搜索测试 ===")
        search_queries = [
            "用户年龄的平均水平是多少",
            "销售数据的趋势分析",
            "哪个产品价格最高",
            "完全无关的查询内容"
        ]
        
        for query in search_queries:
            print(f"\n🔍 查询: '{query}'")
            results = semantic_cache.search_similar(query, top_k=2)
            
            if results:
                print("  📋 找到相似项:")
                for original_text, similarity, result in results:
                    print(f"    相似度 {similarity:.3f}: {original_text}")
                    print(f"    结果: {result}")
            else:
                print("  ❌ 未找到相似项")
        
        # 测试直接获取
        print("\n=== 直接获取测试 ===")
        get_queries = [
            "计算年龄平均数",
            "分析销售走向"
        ]
        
        for query in get_queries:
            result = semantic_cache.get(query, threshold=0.6)
            print(f"查询 '{query}': {'✅ 命中' if result else '❌ 未命中'}")
        
        # 显示统计信息
        print("\n=== 缓存统计信息 ===")
        stats = semantic_cache.get_stats()
        print(f"总请求数: {stats['total_requests']}")
        print(f"精确命中: {stats['exact_hits']}")
        print(f"语义命中: {stats['semantic_hits']}")
        print(f"未命中: {stats['misses']}")
        print(f"命中率: {stats['hit_rate']:.2%}")
        print(f"缓存大小: {stats['cache_size']}")
        
        print("\n🎉 语义缓存测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_semantic_cache()
    sys.exit(0 if success else 1)
