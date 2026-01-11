from __future__ import annotations

import pytest

# Shared pytest fixtures live here.


@pytest.fixture(autouse=True)
def clear_object_cache():
    """Clear the unified object cache before each test to prevent pollution."""
    try:
        from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

        OBJECT_CACHE.clear()
    except ImportError:
        pass  # Module not available in all test environments
    yield
    # Optionally clear after test as well for cleanup
    try:
        from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

        OBJECT_CACHE.clear()
    except ImportError:
        pass
