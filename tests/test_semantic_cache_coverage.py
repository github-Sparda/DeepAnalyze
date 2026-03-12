from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import src.core.cache.semantic_cache as semantic_cache


class _FakeModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def encode(self, text: str, convert_to_numpy: bool = True):
        mapping = {
            "alpha": np.array([1.0, 0.0, 0.0], dtype=np.float32),
            "beta": np.array([0.95, 0.05, 0.0], dtype=np.float32),
            "gamma": np.array([0.0, 1.0, 0.0], dtype=np.float32),
        }
        return mapping.get(text, np.array([0.2, 0.2, 0.2], dtype=np.float32))


class _FakeIndex:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.vectors: list[np.ndarray] = []

    def add(self, vectors):
        for vector in vectors:
            self.vectors.append(np.array(vector, dtype=np.float32))

    def search(self, query, top_k: int):
        if not self.vectors:
            return np.array([[0.0] * top_k], dtype=np.float32), np.array([[-1] * top_k], dtype=np.int64)
        query_vec = np.array(query[0], dtype=np.float32)
        scores = []
        for idx, vector in enumerate(self.vectors):
            scores.append((float(np.dot(query_vec, vector)), idx))
        scores.sort(reverse=True)
        top = scores[:top_k]
        while len(top) < top_k:
            top.append((0.0, -1))
        similarities = np.array([[score for score, _ in top]], dtype=np.float32)
        indices = np.array([[idx for _, idx in top]], dtype=np.int64)
        return similarities, indices


@pytest.fixture
def patched_semantic_cache(monkeypatch):
    monkeypatch.setattr(semantic_cache, "SEMANTIC_LIBS_AVAILABLE", True)
    monkeypatch.setattr(semantic_cache, "SentenceTransformer", _FakeModel)
    monkeypatch.setattr(
        semantic_cache,
        "faiss",
        SimpleNamespace(
            IndexFlatIP=lambda dim: _FakeIndex(dim),
            normalize_L2=lambda arr: None,
        ),
    )
    semantic_cache._global_semantic_data_cache = None
    yield
    semantic_cache._global_semantic_data_cache = None


def test_semantic_cache_store_search_evict_and_stats(patched_semantic_cache):
    cache = semantic_cache.SemanticSimilarityCache(similarity_threshold=0.7, max_data_cache_size=2)
    assert cache.store("alpha", {"v": 1}) is True
    assert cache.store("gamma", {"v": 2}) is True
    assert cache.get("alpha") == {"v": 1}

    similar = cache.search_similar("beta", top_k=2)
    assert similar
    assert similar[0][0] == "alpha"
    assert cache.get("beta", similarity_threshold=0.7) == {"v": 1}
    assert cache.get("beta", similarity_threshold=0.99) is None
    assert cache.get_similar_texts("beta", threshold=0.7) == ["alpha"]

    assert cache.store("delta", {"v": 3}) is True
    assert len(cache.entries) == 2

    stats = cache.get_stats()
    assert stats["total_requests"] >= 3
    assert stats["hit_rate"] >= 0

    cache.clear()
    assert cache.get_stats()["data_cache_size"] == 0


def test_semantic_cache_handles_store_and_search_failures(patched_semantic_cache, monkeypatch):
    cache = semantic_cache.SemanticSimilarityCache()
    monkeypatch.setattr(cache, "_text_to_vector", lambda text: (_ for _ in ()).throw(RuntimeError("boom")))
    assert cache.store("alpha", 1) is False
    assert cache.search_similar("alpha") == []
    assert cache.get("alpha") is None


def test_semantic_cache_global_helpers(patched_semantic_cache):
    assert semantic_cache.semantic_data_cache_store("alpha", 1) is True
    assert semantic_cache.semantic_data_cache_get("alpha") == 1
    results = semantic_cache.semantic_data_cache_search("beta", top_k=1)
    assert results and results[0][2] == 1
    stats = semantic_cache.semantic_data_cache_stats()
    assert "similarity_threshold" in stats

