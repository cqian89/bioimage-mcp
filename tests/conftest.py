from __future__ import annotations

import os
import subprocess
import warnings

import pytest

from bioimage_mcp.bootstrap.env_manager import detect_env_manager

# Shared pytest fixtures live here.


@pytest.fixture(scope="session")
def _env_availability_cache():
    """Cache environment availability results for the duration of the session."""
    return {}


def _is_env_available(env_name: str, cache: dict) -> bool:
    """Check if a conda environment is available and functional, with caching."""
    if env_name in cache:
        return cache[env_name]

    try:
        detected = detect_env_manager()
        if not detected:
            cache[env_name] = False
            return False

        _manager, exe, _version = detected
        # Do not hard-fail if no conda-like manager is installed; treat env as unavailable.
        # Use the detected manager to verify the target env can run Python.
        result = subprocess.run(
            [exe, "run", "-n", env_name, "python", "-c", "print('ok')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        available = result.returncode == 0
    except Exception:
        available = False

    cache[env_name] = available
    return available


@pytest.fixture(autouse=True)
def check_required_env(request, _env_availability_cache):
    """Global fixture to skip tests if required bioimage-mcp environment is missing."""
    # Check for explicit requires_env marker
    marker = request.node.get_closest_marker("requires_env")

    # Legacy convenience environment markers (no new tests should use these)
    env_mapping = {
        "requires_stardist": "bioimage-mcp-stardist",
        "requires_cellpose": "bioimage-mcp-cellpose",
        "requires_base": "bioimage-mcp-base",
    }

    env_name = None
    if marker:
        env_name = marker.args[0]
    else:
        for marker_name, mapped_env in env_mapping.items():
            if request.node.get_closest_marker(marker_name):
                env_name = mapped_env
                break

    if env_name:
        if not _is_env_available(env_name, _env_availability_cache):
            tool_name = env_name.replace("bioimage-mcp-", "")
            install_cmd = f"bioimage-mcp install {tool_name}"
            msg = f"Environment '{env_name}' not found. To install, run: {install_cmd}"
            warnings.warn(msg, stacklevel=2)
            pytest.skip(f"Required environment {env_name} missing.")


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
