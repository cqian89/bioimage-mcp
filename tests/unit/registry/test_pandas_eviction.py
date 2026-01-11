import pandas as pd
import pytest
import logging
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE
from bioimage_mcp.registry.dynamic.pandas_adapter import (
    ObjectNotFoundError,
)


def test_lru_eviction(caplog):
    """T050: Verify LRU eviction and warning (count-based)."""
    OBJECT_CACHE.clear()
    original_size = OBJECT_CACHE.max_size
    OBJECT_CACHE.max_size = 3  # Small size for testing

    try:
        with caplog.at_level(logging.WARNING):
            # Fill cache
            for i in range(3):
                uri = f"obj://test/{i}"
                OBJECT_CACHE[uri] = pd.DataFrame({"a": [i]})

            assert len(OBJECT_CACHE) == 3
            assert "obj://test/0" in OBJECT_CACHE

            # Access 0 to make it MRU
            _ = OBJECT_CACHE["obj://test/0"]

            # Add new item, should evict 1 (the oldest LRU)
            OBJECT_CACHE["obj://test/3"] = pd.DataFrame({"a": [3]})

            assert len(OBJECT_CACHE) == 3
            assert "obj://test/1" not in OBJECT_CACHE
            assert "obj://test/0" in OBJECT_CACHE
            assert "obj://test/2" in OBJECT_CACHE
            assert "obj://test/3" in OBJECT_CACHE

            assert "Evicting LRU object: obj://test/1" in caplog.text
    finally:
        OBJECT_CACHE.max_size = original_size


def test_memory_eviction(caplog):
    """T050: Verify LRU eviction based on memory limit."""
    OBJECT_CACHE.clear()
    original_mem = OBJECT_CACHE.max_memory
    # Set limit to something small, e.g., 2000 bytes
    OBJECT_CACHE.max_memory = 2000

    try:
        with caplog.at_level(logging.WARNING):
            # Each row is about 8 bytes + overhead
            df1 = pd.DataFrame({"a": range(100)})  # ~800 bytes + overhead
            OBJECT_CACHE["obj://mem/1"] = df1

            df2 = pd.DataFrame({"a": range(100)})
            OBJECT_CACHE["obj://mem/2"] = df2

            # Adding df3 should trigger eviction if total > 2000
            df3 = pd.DataFrame({"a": range(100)})
            OBJECT_CACHE["obj://mem/3"] = df3

            # Exact memory usage depends on pandas version, but 3 dfs of 100 ints
            # will definitely exceed 2000 bytes with deep=True (due to overhead).
            assert len(OBJECT_CACHE) < 3
            assert "limit reached" in caplog.text
    finally:
        OBJECT_CACHE.max_memory = original_mem


def test_object_not_found_error():
    """T051: Verify ObjectNotFoundError structured error."""
    from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter

    adapter = PandasAdapter()

    # Try to execute on non-existent ObjectRef
    with pytest.raises(ObjectNotFoundError) as excinfo:
        adapter.execute("query", "obj://non-existent", expr="a > 0")

    assert excinfo.value.code == "OBJECT_NOT_FOUND"
    assert "not found in cache" in str(excinfo.value)
    assert (
        excinfo.value.details["hint"]
        == "The object may have been evicted. Re-run the operation that created it."
    )
