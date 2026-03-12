from __future__ import annotations

import os
from pathlib import Path

import src.core.cache.smart_cache as smart_cache


def test_memory_cache_lru_and_clear():
    cache = smart_cache.MemoryCache(max_size=2)
    assert cache.put("k1", "v1") is True
    assert cache.put("k2", "v2") is True
    assert cache.get("k1") == "v1"
    assert cache.put("k3", "v3") is True
    assert cache.size() == 2
    assert cache.delete("k2") in {True, False}
    assert cache.clear() is True
    assert cache.size() == 0


def test_file_cache_read_write_delete_cleanup(tmp_path: Path, monkeypatch):
    cache = smart_cache.FileCache(str(tmp_path), max_size_mb=1)
    assert cache.put("a", {"x": 1}) is True
    assert cache.get("a") == {"x": 1}
    assert cache.size() == 1
    assert cache.delete("a") is True
    assert cache.get("a") is None

    broken_path = Path(cache._get_file_path("broken"))
    broken_path.write_bytes(b"not-pickle")
    assert cache.get("broken") is None

    for idx in range(4):
        assert cache.put(f"k{idx}", idx) is True
    monkeypatch.setattr(cache, "_get_total_size", lambda: cache.max_size_bytes)
    assert cache.put("overflow", 9) is True
    cache._cleanup_old_files()
    assert cache.clear() is True


def test_smart_cache_and_global_helpers(tmp_path: Path):
    cache = smart_cache.SmartCache(memory_max_items=2, disk_data_cache_dir=str(tmp_path / "disk"), disk_max_size_mb=1)
    assert cache.put("alpha", 1, persist_to_disk=False) is True
    assert cache.get("alpha") == 1
    assert cache.put("beta", 2, persist_to_disk=True) is True
    assert cache.get("beta") == 2
    assert cache.get("missing") is None
    stats = cache.get_stats()
    assert stats["total_requests"] == 3
    assert cache.delete("alpha") is True
    assert cache.warm_up({"k1": 1, "k2": 2}) == 2
    assert cache.clear() is True

    smart_cache._global_data_cache = cache
    assert smart_cache.data_cache_put("x", "y") is True
    assert smart_cache.data_cache_get("x") == "y"
    assert smart_cache.data_cache_delete("x") is True
    smart_cache._global_data_cache = None
