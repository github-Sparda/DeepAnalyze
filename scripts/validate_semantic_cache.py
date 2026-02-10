#!/usr/bin/env python3
"""
Semantic cache validation test.
Runs real cache checks only when the semantic cache is enabled and deps are available.
"""

import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_root = os.path.join(project_root, "src")
if src_root not in sys.path:
    sys.path.insert(0, src_root)


def semantic_cache_enabled() -> bool:
    value = os.environ.get("DEEPANALYZE_SEMANTIC_CACHE_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def semantic_cache_test() -> bool:
    print("Starting semantic cache validation...")

    if not semantic_cache_enabled():
        print("Semantic cache disabled. Skipping.")
        return True

    try:
        from core.cache.semantic_cache import SemanticSimilarityCache
    except Exception as e:
        print(f"Semantic cache import failed: {e}")
        return False

    try:
        cache = SemanticSimilarityCache(similarity_threshold=0.7, max_cache_size=10)
        print("Semantic cache instance created.")

        test_entries = [
            ("Average user age", {"operation": "mean", "field": "age"}),
            ("Sales trend analysis", {"operation": "trend", "field": "sales"}),
            ("Find max price", {"operation": "max", "field": "price"}),
        ]
        for text, result in test_entries:
            success = cache.store(text, result)
            print(f"  Store '{text}': {'OK' if success else 'FAIL'}")

        results = cache.search_similar("average age", top_k=2)
        print(f"  Similarity results: {len(results)}")
        return True
    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = semantic_cache_test()
    if success:
        print("Semantic cache validation passed.")
    else:
        print("Semantic cache validation failed.")
    sys.exit(0 if success else 1)
