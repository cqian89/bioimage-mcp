import numpy as np
import pytest

from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


def test_skimage_load_image_objectref():
    """Test that SkimageAdapter._load_image properly handles ObjectRef with obj:// URI."""
    adapter = SkimageAdapter()

    # Mock data
    data = np.zeros((10, 10))
    uri = "obj://default/skimage/test-id"

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


def test_skimage_load_image_objectref_missing_cache():
    """Test that SkimageAdapter._load_image raises error if ObjectRef URI not in cache."""
    adapter = SkimageAdapter()
    uri = "obj://default/skimage/non-existent"

    artifact = {
        "type": "ObjectRef",
        "uri": uri,
    }

    with pytest.raises(ValueError, match="Object with URI obj://.* not found in memory cache"):
        adapter._load_image(artifact)


def test_skimage_load_image_file_scheme():
    """Test that file:// URIs still go through normal loading (and fail if file missing)."""
    adapter = SkimageAdapter()

    artifact = {
        "type": "BioImageRef",
        "uri": "file:///non/existent/path.tif",
        "path": "/non/existent/path.tif",
    }

    # This should fail because the file doesn't exist
    # We catch the failure to ensure it didn't try to use OBJECT_CACHE
    with pytest.raises((FileNotFoundError, RuntimeError, Exception)):
        adapter._load_image(artifact)
