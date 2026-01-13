from __future__ import annotations

import os

import pytest

# Shared pytest fixtures live here.


@pytest.fixture(autouse=True)
def reset_fs_allowlist_env():
    """Reset filesystem allowlist environment variables to prevent test pollution."""
    # Clear before test
    for key in ["BIOIMAGE_MCP_FS_ALLOWLIST_READ", "BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"]:
        os.environ.pop(key, None)
    yield
    # Clear after test as well
    for key in ["BIOIMAGE_MCP_FS_ALLOWLIST_READ", "BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"]:
        os.environ.pop(key, None)


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
