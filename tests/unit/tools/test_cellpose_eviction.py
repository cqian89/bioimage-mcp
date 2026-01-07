from __future__ import annotations

import pytest
from typing import Any
from pathlib import Path
import unittest.mock as mock

# Import the module to test
import tools.cellpose.bioimage_mcp_cellpose.entrypoint as entrypoint


class TestCellposeEviction:
    """T035: Tests for ObjectRef eviction in Cellpose tool pack."""

    @pytest.fixture(autouse=True)
    def setup_worker(self):
        """Initialize worker identity and clear caches."""
        entrypoint._SESSION_ID = "test-session"
        entrypoint._ENV_ID = "test-env"
        entrypoint._MEMORY_ARTIFACTS.clear()
        entrypoint._OBJECT_CACHE.clear()
        yield
        entrypoint._SESSION_ID = None
        entrypoint._ENV_ID = None
        entrypoint._MEMORY_ARTIFACTS.clear()
        entrypoint._OBJECT_CACHE.clear()

    def test_evict_object_ref_success(self):
        """Test that evicting an obj:// URI removes the object from cache."""
        # 1. Store an object
        obj = {"some": "data"}
        obj_id, obj_uri = entrypoint._store_object(obj)
        assert obj_id in entrypoint._OBJECT_CACHE

        # 2. Evict it
        request = {"command": "evict", "ref_id": obj_uri, "ordinal": 1}
        response = entrypoint.handle_evict(request)

        # 3. Verify response and cache
        assert response["ok"] is True
        assert response["command"] == "evict_result"
        assert obj_id not in entrypoint._OBJECT_CACHE

    def test_evict_non_existent_object_ref_fails(self):
        """Test that evicting a non-existent obj:// returns appropriate error."""
        obj_uri = "obj://test-session/test-env/missing-id"

        request = {"command": "evict", "ref_id": obj_uri, "ordinal": 2}
        response = entrypoint.handle_evict(request)

        # 3. Verify response
        assert response["ok"] is False
        assert response["error"]["code"] == "NOT_FOUND"
        assert "not found" in response["error"]["message"]

    def test_evict_invalid_uri_fails(self):
        """Test that evicting an invalid URI format returns error."""
        request = {"command": "evict", "ref_id": "invalid-uri", "ordinal": 3}
        response = entrypoint.handle_evict(request)

        assert response["ok"] is False
        assert response["error"]["code"] == "INVALID_REF_ID"
