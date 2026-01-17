import pytest
import numpy as np
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


def test_load_image_objectref():
    """Test that _load_image properly handles ObjectRef with obj:// URI."""
    adapter = PhasorPyAdapter()

    # Mock data
    data = np.zeros((10, 10))
    uri = "obj://default/base/test-id"

    # Put data in cache
    OBJECT_CACHE[uri] = data

    try:
        # Test ObjectRef
        artifact = {
            "type": "ObjectRef",
            "uri": uri,
            "metadata": {"shape": [10, 10], "dtype": "float64"},
        }

        loaded_data = adapter._load_image(artifact)

        assert np.array_equal(loaded_data, data)
        assert loaded_data is data
    finally:
        # Cleanup
        if uri in OBJECT_CACHE:
            del OBJECT_CACHE[uri]


def test_load_image_objectref_missing_cache():
    """Test that _load_image raises error if ObjectRef URI not in cache."""
    adapter = PhasorPyAdapter()
    uri = "obj://default/base/non-existent"

    artifact = {
        "type": "ObjectRef",
        "uri": uri,
    }

    with pytest.raises(ValueError, match="Object with URI obj://.* not found in memory cache"):
        adapter._load_image(artifact)


def test_load_image_file_validation():
    """Test that file:// URIs still go through normal validation."""
    adapter = PhasorPyAdapter()

    # Mock allowlist to force PermissionError
    # Set allowlist to something that won't match our test path
    with patch.dict(os.environ, {"BIOIMAGE_MCP_FS_ALLOWLIST_READ": json.dumps(["/allowed/path"])}):
        artifact = {
            "type": "BioImageRef",
            "uri": "file:///disallowed/path/image.tif",
            "path": "/disallowed/path/image.tif",
        }

        # This should fail either because the path doesn't exist (when it tries to load it)
        # OR because of PermissionError. We want to see PermissionError first.
        with pytest.raises(PermissionError, match="Path not under any allowed read root"):
            adapter._load_image(artifact)


@patch("bioio.BioImage")
def test_load_image_bioimage_call(mock_bioimage):
    """Test that BioImageRef still calls BioImage."""
    adapter = PhasorPyAdapter()

    # Mock BioImage return value
    mock_img = MagicMock()
    mock_img.reader.xarray_data.values = np.zeros((5, 5))
    mock_bioimage.return_value = mock_img

    artifact = {"type": "BioImageRef", "uri": "file:///tmp/test.tif", "path": "/tmp/test.tif"}

    # Ensure no allowlist for this test
    with patch.dict(os.environ, {}, clear=False):
        if "BIOIMAGE_MCP_FS_ALLOWLIST_READ" in os.environ:
            del os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"]

        data = adapter._load_image(artifact)

        assert mock_bioimage.called
        assert data.shape == (5, 5)
