import threading
import pytest
from bioimage_mcp.registry.dynamic.object_cache import (
    LRUCache,
    get_by_artifact_id,
    register,
    evict,
    clear,
    OBJECT_CACHE,
)


def test_basic_ops():
    clear()
    register("obj://test/1", {"a": 1})
    assert "obj://test/1" in OBJECT_CACHE
    assert OBJECT_CACHE.get("obj://test/1") == {"a": 1}

    evict("obj://test/1")
    assert "obj://test/1" not in OBJECT_CACHE
    assert OBJECT_CACHE.get("obj://test/1") is None


def test_lru_eviction_count():
    cache = LRUCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache

    # Access b to make it MRU
    _ = cache.get("b")
    cache.set("d", 4)

    assert "c" not in cache
    assert "b" in cache
    assert "d" in cache


def test_memory_eviction():
    # Cache that can hold about 2 small objects
    # Each default object is 10KB (10240 bytes)
    cache = LRUCache(max_memory=25000)

    cache.set("obj1", "data1")  # 10240
    cache.set("obj2", "data2")  # 10240
    assert "obj1" in cache
    assert "obj2" in cache

    # Adding obj3 (10240) will make total 30720 > 25000
    # Should evict obj1
    cache.set("obj3", "data3")
    assert "obj1" not in cache
    assert "obj2" in cache
    assert "obj3" in cache


def test_get_by_artifact_id():
    clear()
    register("obj://session1/env1/art1", "data1")
    register("mem://art2", "data2")
    register("art3", "data3")

    assert get_by_artifact_id("art1") == "data1"
    assert get_by_artifact_id("art2") == "data2"
    assert get_by_artifact_id("art3") == "data3"
    assert get_by_artifact_id("nonexistent") is None


def test_thread_safety():
    cache = LRUCache(max_size=100)  # Smaller for faster test

    def worker(worker_id):
        for i in range(50):  # Fewer iterations
            cache.set(f"w{worker_id}_{i}", i)
            _ = cache.get(f"w{worker_id}_{i}")

    threads = []
    for i in range(5):  # Fewer threads
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Since we have 5 * 50 = 250 insertions, but max_size is 100,
    # the cache should be full (100 items).
    assert len(cache) == 100


def test_memory_usage_estimation():
    cache = LRUCache()

    # Test Mock DataFrame
    class MockDF:
        def memory_usage(self, deep=True):
            class MockUsage:
                def sum(self):
                    return 5000

            return MockUsage()

    df = MockDF()
    usage = cache._get_memory_usage(df)
    assert usage == 5000

    # Test Numpy-like (Xarray DataArray mock)
    class MockDataArray:
        def __init__(self, nbytes):
            self.nbytes = nbytes

    da = MockDataArray(1234)
    assert cache._get_memory_usage(da) == 1234

    # Test default
    assert cache._get_memory_usage("string") == 10240


def test_dict_access():
    cache = LRUCache(max_size=2)
    cache["a"] = 1
    assert cache["a"] == 1

    with pytest.raises(KeyError):
        _ = cache["nonexistent"]

    cache["b"] = 2
    cache["c"] = 3
    assert "a" not in cache
