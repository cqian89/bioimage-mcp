import os
import sys
import importlib
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


# Create a mock module structure for testing
class MockFilters:
    @staticmethod
    def simple_filter(image, sigma=1.0):
        return image * sigma

    @staticmethod
    def auxiliary_filter(image, structure=None):
        if structure is None:
            return image
        return image + structure

    @staticmethod
    def callable_filter(image, function=None):
        if function is None:
            return image
        # Simulate a filter that uses the callable result
        val = function(image)
        if np.isscalar(val):
            # If scalar (like mean), return an array filled with that value
            return np.full_like(image, val)
        return val


class MockNdimage:
    filters = MockFilters()


# We'll use a local mock for importlib.import_module
@pytest.fixture
def adapter():
    return ScipyNdimageAdapter()


@pytest.fixture
def mock_module(tmp_path):
    # Create a mock module in sys.modules
    mock_mod = MagicMock()
    mock_mod.simple_filter = MockFilters.simple_filter
    mock_mod.auxiliary_filter = MockFilters.auxiliary_filter
    mock_mod.callable_filter = MockFilters.callable_filter

    real_import = importlib.import_module

    def side_effect(name, *args, **kwargs):
        if name.startswith("scipy.ndimage"):
            return mock_mod
        return real_import(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=side_effect):
        yield mock_mod


def test_execute_named_inputs_and_metadata(adapter, mock_module, tmp_path):
    # Setup input data in OBJECT_CACHE
    data = np.random.rand(10, 10).astype(np.float32)
    uri = "obj://test_image"
    OBJECT_CACHE[uri] = data

    inputs = [
        (
            "image",
            {
                "uri": uri,
                "metadata": {
                    "axes": "YX",
                    "physical_pixel_sizes": [1.0, 1.0],
                    "channel_names": ["Ch1"],
                },
            },
        )
    ]
    params = {"sigma": 2.0}

    # Execute
    results = adapter.execute(
        fn_id="scipy.ndimage.simple_filter", inputs=inputs, params=params, work_dir=tmp_path
    )

    # Assertions
    assert len(results) == 1
    out = results[0]
    assert out["type"] == "BioImageRef"
    assert out["format"] == "OME-TIFF"
    assert "metadata" in out
    meta = out["metadata"]
    assert meta["axes"] == "YX"
    assert meta["physical_pixel_sizes"] == [1.0, 1.0]
    assert meta["channel_names"] == ["Ch1"]
    assert meta["dtype"] == "float32"

    # Verify result file exists and has correct data (approx)
    from bioio import BioImage

    img = BioImage(out["path"])
    assert np.allclose(img.reader.data, data * 2.0)


def test_execute_auxiliary_artifacts(adapter, mock_module, tmp_path):
    # Setup data
    img_data = np.ones((5, 5), dtype=np.float32)
    struct_data = np.ones((5, 5), dtype=np.float32) * 5

    img_uri = "obj://img"
    struct_uri = "obj://struct"
    OBJECT_CACHE[img_uri] = img_data
    OBJECT_CACHE[struct_uri] = struct_data

    inputs = [("image", {"uri": img_uri}), ("structure", {"uri": struct_uri})]

    # Execute
    results = adapter.execute(
        fn_id="scipy.ndimage.auxiliary_filter", inputs=inputs, params={}, work_dir=tmp_path
    )

    # Verify
    from bioio import BioImage

    img = BioImage(results[0]["path"])
    # Result should be img_data + struct_data = 6
    assert np.all(img.reader.data == 6)


def test_execute_callable_resolution(adapter, mock_module, tmp_path):
    # Setup data - use 2D to avoid bioio dimension confusion
    img_data = np.array([[10, 20], [30, 40]], dtype=np.float32)
    img_uri = "obj://img_callable"
    OBJECT_CACHE[img_uri] = img_data

    inputs = [("image", {"uri": img_uri, "metadata": {"axes": "YX"}})]
    # Test numpy.mean resolution
    params = {"function": "numpy.mean"}

    results = adapter.execute(
        fn_id="scipy.ndimage.callable_filter", inputs=inputs, params=params, work_dir=tmp_path
    )

    # Verify
    from bioio import BioImage

    img = BioImage(results[0]["path"])
    # Result should be an array filled with 25
    assert np.allclose(np.squeeze(img.reader.data), 25)


def test_execute_dtype_safety_uint16_cast(adapter, mock_module, tmp_path):
    # Setup large uint16 data (16 MB)
    # uint16 is 2 bytes per element. 16MB = 8M elements.
    # 2048 * 4096 = 8,388,608 elements.
    data = np.ones((2048, 4096), dtype=np.uint16)
    assert data.nbytes >= 16 * 1024 * 1024

    uri = "obj://large_uint16"
    OBJECT_CACHE[uri] = data

    inputs = [("image", {"uri": uri})]

    # We want to check if the data passed to the function is float32
    def check_dtype(image, **kwargs):
        assert image.dtype == np.float32
        return image

    mock_module.simple_filter = check_dtype

    adapter.execute(
        fn_id="scipy.ndimage.simple_filter", inputs=inputs, params={}, work_dir=tmp_path
    )


def test_execute_dtype_safety_int64_output(adapter, mock_module, tmp_path):
    # Setup int64 output from mock
    def int64_func(image):
        return np.array([1, 2, 3], dtype=np.int64)

    mock_module.simple_filter = int64_func

    data = np.ones((3,), dtype=np.float32)
    uri = "obj://input"
    OBJECT_CACHE[uri] = data

    results = adapter.execute(
        fn_id="scipy.ndimage.simple_filter",
        inputs=[("image", {"uri": uri})],
        params={},
        work_dir=tmp_path,
    )

    # Verify output dtype is int32 (per our implementation for int64)
    assert results[0]["metadata"]["dtype"] == "int32"


def test_execute_scalar_output(adapter, mock_module, tmp_path):
    # Setup mock to return a scalar
    def scalar_func(image):
        return 42.0

    mock_module.simple_filter = scalar_func

    data = np.ones((3, 3), dtype=np.float32)
    uri = "obj://input_scalar"
    OBJECT_CACHE[uri] = data

    results = adapter.execute(
        fn_id="scipy.ndimage.simple_filter",
        inputs=[("image", {"uri": uri})],
        params={},
        work_dir=tmp_path,
    )

    # Verify result is JSON
    assert results[0]["type"] == "NativeOutputRef"
    assert results[0]["format"] == "json"

    # Read JSON content
    import json

    with open(results[0]["path"], "r") as f:
        content = json.load(f)
    assert content["value"] == 42.0


def test_execute_callable_error(adapter, mock_module, tmp_path):
    inputs = [("image", {"uri": "obj://any"})]
    OBJECT_CACHE["obj://any"] = np.ones((1,))

    params = {"function": "non_existent_callable"}

    with pytest.raises(ValueError, match="Unauthorized or unknown callable reference"):
        adapter.execute(
            fn_id="scipy.ndimage.callable_filter", inputs=inputs, params=params, work_dir=tmp_path
        )


def test_execute_metadata_file_persistence(adapter, mock_module, tmp_path):
    # Setup input data in OBJECT_CACHE
    data = np.random.rand(10, 10).astype(np.float32)
    uri = "obj://test_meta_persist"
    OBJECT_CACHE[uri] = data

    inputs = [
        (
            "image",
            {
                "uri": uri,
                "metadata": {
                    "axes": "YX",
                    "physical_pixel_sizes": {"Y": 1.0, "X": 2.0},
                    "channel_names": ["Ch1"],
                },
            },
        )
    ]

    # Execute
    results = adapter.execute(
        fn_id="scipy.ndimage.simple_filter", inputs=inputs, params={"sigma": 1.0}, work_dir=tmp_path
    )

    out = results[0]
    out_path = Path(out["path"])

    # Verify file metadata persistence (UAT gap)
    from bioimage_mcp.artifacts.metadata import extract_image_metadata

    file_meta = extract_image_metadata(out_path)
    assert file_meta is not None

    # Check physical pixel sizes in the file itself (should fail before fix)
    pps = file_meta.get("physical_pixel_sizes")
    assert pps is not None, "Physical pixel sizes missing from written file metadata"
    assert pps["Y"] == 1.0
    assert pps["X"] == 2.0

    # Check channel names
    assert "channel_names" in file_meta
    assert "Ch1" in file_meta["channel_names"]


def test_execute_metadata_list_form_persistence(adapter, mock_module, tmp_path):
    # Setup input data
    data = np.random.rand(5, 5).astype(np.float32)
    uri = "obj://test_meta_list"
    OBJECT_CACHE[uri] = data

    inputs = [
        (
            "image",
            {
                "uri": uri,
                "metadata": {
                    "axes": "YX",
                    "physical_pixel_sizes": [0.5, 0.25],  # [Y, X]
                },
            },
        )
    ]

    results = adapter.execute(
        fn_id="scipy.ndimage.simple_filter", inputs=inputs, params={"sigma": 1.0}, work_dir=tmp_path
    )

    from bioimage_mcp.artifacts.metadata import extract_image_metadata

    file_meta = extract_image_metadata(Path(results[0]["path"]))
    pps = file_meta.get("physical_pixel_sizes")
    assert pps is not None
    assert pps["Y"] == 0.5
    assert pps["X"] == 0.25
