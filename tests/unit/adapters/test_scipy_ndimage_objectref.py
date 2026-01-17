import pytest
import numpy as np
from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


def test_scipy_load_image_objectref():
    """Test that ScipyNdimageAdapter._load_image properly handles ObjectRef with obj:// URI."""
    adapter = ScipyNdimageAdapter()

    # Mock data
    data = np.zeros((10, 10))
    uri = "obj://default/scipy/test-id"

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


def test_scipy_load_image_objectref_missing_cache():
    """Test that ScipyNdimageAdapter._load_image raises error if ObjectRef URI not in cache."""
    adapter = ScipyNdimageAdapter()
    uri = "obj://default/scipy/non-existent"

    artifact = {
        "type": "ObjectRef",
        "uri": uri,
    }

    with pytest.raises(ValueError, match="Object with URI obj://.* not found in memory cache"):
        adapter._load_image(artifact)


def test_scipy_load_image_file_scheme():
    """Test that file:// URIs still go through normal loading (and fail if file missing)."""
    adapter = ScipyNdimageAdapter()

    artifact = {
        "type": "BioImageRef",
        "uri": "file:///non/existent/path.tif",
        "path": "/non/existent/path.tif",
    }

    # This should fail because the file doesn't exist
    with pytest.raises((FileNotFoundError, RuntimeError, Exception)):
        adapter._load_image(artifact)
