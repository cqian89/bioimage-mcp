"""Unit tests for Cellpose entrypoint object caching (T017)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def cellpose_entrypoint():
    """Load the cellpose entrypoint module."""
    entrypoint_path = (
        Path(__file__).resolve().parents[3]
        / "tools"
        / "cellpose"
        / "bioimage_mcp_cellpose"
        / "entrypoint.py"
    )

    spec = importlib.util.spec_from_file_location("cellpose_entrypoint", entrypoint_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load entrypoint from {entrypoint_path}")

    module = importlib.util.module_from_spec(spec)
    # Mocking environment for initialization
    import os

    os.environ["BIOIMAGE_MCP_SESSION_ID"] = "test-session"
    os.environ["BIOIMAGE_MCP_ENV_ID"] = "bioimage-mcp-cellpose"

    spec.loader.exec_module(module)
    module._initialize_worker("test-session", "bioimage-mcp-cellpose")
    return module


def test_object_cache_operations(cellpose_entrypoint) -> None:
    """T017: Test _store_object and _load_object with obj:// URIs."""
    ep = cellpose_entrypoint

    # These should fail initially because they are not implemented
    assert hasattr(ep, "_OBJECT_CACHE")
    assert isinstance(ep._OBJECT_CACHE, dict)

    class MockModel:
        pass

    model = MockModel()

    # Store object
    obj_id, obj_uri = ep._store_object(model)

    assert obj_id in ep._OBJECT_CACHE
    assert ep._OBJECT_CACHE[obj_id] is model
    assert obj_uri.startswith("obj://")
    assert "test-session" in obj_uri
    assert "bioimage-mcp-cellpose" in obj_uri
    assert obj_id in obj_uri

    # Load object
    loaded = ep._load_object(obj_uri)
    assert loaded is model


def test_load_object_invalid_uri(cellpose_entrypoint) -> None:
    """T017: Test _load_object with invalid URIs."""
    ep = cellpose_entrypoint

    with pytest.raises(ValueError, match="Invalid object URI"):
        ep._load_object("mem://test-session/env/123")  # Wrong scheme

    with pytest.raises(ValueError, match="Invalid object URI format"):
        ep._load_object("obj://too/short")

    with pytest.raises(ValueError, match="belongs to different worker"):
        ep._load_object("obj://wrong-session/bioimage-mcp-cellpose/123")


def test_load_object_not_found(cellpose_entrypoint) -> None:
    """T017: Test _load_object with non-existent ID."""
    ep = cellpose_entrypoint
    uri = "obj://test-session/bioimage-mcp-cellpose/missing-id"

    with pytest.raises(KeyError, match="Object not found"):
        ep._load_object(uri)
