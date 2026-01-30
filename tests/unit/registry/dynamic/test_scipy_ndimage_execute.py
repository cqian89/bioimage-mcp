import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern
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

    @staticmethod
    def zoom(image, zoom, **kwargs):
        return image

    @staticmethod
    def rotate(image, angle, **kwargs):
        return image

    @staticmethod
    def shift(image, shift, **kwargs):
        return image

    @staticmethod
    def label(input, structure=None, output=None):
        return (input.astype(np.int32), 2)

    @staticmethod
    def center_of_mass(input, labels=None, index=None):
        if index is None:
            return (1.0, 1.0)
        if np.isscalar(index):
            return (float(index), float(index))
        return [(float(i), float(i)) for i in index]

    @staticmethod
    def extrema(input, labels=None, index=None):
        return (0.0, 10.0, (0, 0), (1, 1))

    @staticmethod
    def sum(input, labels=None, index=None):
        if index is None:
            return 100.0
        if np.isscalar(index):
            return float(index) * 10.0
        return [float(i) * 10.0 for i in index]


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
    mock_mod.zoom = MockFilters.zoom
    mock_mod.rotate = MockFilters.rotate
    mock_mod.shift = MockFilters.shift
    mock_mod.label = MockFilters.label
    mock_mod.center_of_mass = MockFilters.center_of_mass
    mock_mod.extrema = MockFilters.extrema
    mock_mod.sum = MockFilters.sum

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
    assert out["format"] == "OME-Zarr"
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

    with open(results[0]["path"]) as f:
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
    data = np.random.rand(1, 10, 10).astype(np.float32)
    uri = "obj://test_meta_persist"
    OBJECT_CACHE[uri] = data

    inputs = [
        (
            "image",
            {
                "uri": uri,
                "metadata": {
                    "axes": "CYX",
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


def test_execute_zoom_metadata_updates(adapter, mock_module, tmp_path):
    # Setup 2D input with YX axes
    data = np.random.rand(10, 10).astype(np.float32)
    uri = "obj://zoom_yx"
    OBJECT_CACHE[uri] = data

    inputs = [
        (
            "image",
            {
                "uri": uri,
                "metadata": {
                    "axes": "YX",
                    "physical_pixel_sizes": {"Y": 0.5, "X": 0.25},
                },
            },
        )
    ]
    # Zoom Y by 1.0 (no change), X by 2.0 (pixel size should be halved)
    params = {"zoom": [1.0, 2.0]}

    results = adapter.execute(
        fn_id="scipy.ndimage.zoom", inputs=inputs, params=params, work_dir=tmp_path
    )

    out_pps = results[0]["metadata"]["physical_pixel_sizes"]
    assert out_pps["Y"] == 0.5
    assert out_pps["X"] == 0.125


def test_execute_zoom_5d_metadata_updates(adapter, mock_module, tmp_path):
    # Setup 5D input TCZYX
    data = np.random.rand(1, 1, 1, 10, 10).astype(np.float32)
    uri = "obj://zoom_5d"
    OBJECT_CACHE[uri] = data

    inputs = [
        (
            "image",
            {
                "uri": uri,
                "metadata": {
                    "axes": "TCZYX",
                    "physical_pixel_sizes": {"Z": 1.0, "Y": 0.5, "X": 0.25},
                },
            },
        )
    ]
    # Zoom factors for T, C, Z, Y, X
    # T, C factors should be ignored for physical size updates
    params = {"zoom": [1.0, 1.0, 2.0, 1.0, 0.5]}

    results = adapter.execute(
        fn_id="scipy.ndimage.zoom", inputs=inputs, params=params, work_dir=tmp_path
    )

    out_pps = results[0]["metadata"]["physical_pixel_sizes"]
    assert out_pps["Z"] == 0.5  # 1.0 / 2.0
    assert out_pps["Y"] == 0.5  # 0.5 / 1.0
    assert out_pps["X"] == 0.5  # 0.25 / 0.5


def test_execute_transform_pass_through(adapter, mock_module, tmp_path):
    # Proves rotate and shift preserve metadata without changes
    data = np.random.rand(10, 10).astype(np.float32)
    uri = "obj://transform_pass"
    OBJECT_CACHE[uri] = data

    metadata = {
        "axes": "YX",
        "physical_pixel_sizes": {"Y": 0.5, "X": 0.25},
        "channel_names": ["Green"],
    }
    inputs = [("image", {"uri": uri, "metadata": metadata})]

    # 1) Rotate
    res_rotate = adapter.execute(
        fn_id="scipy.ndimage.rotate", inputs=inputs, params={"angle": 45}, work_dir=tmp_path
    )
    meta_rotate = res_rotate[0]["metadata"]
    assert meta_rotate["physical_pixel_sizes"] == metadata["physical_pixel_sizes"]
    assert meta_rotate["channel_names"] == metadata["channel_names"]

    # 2) Shift
    res_shift = adapter.execute(
        fn_id="scipy.ndimage.shift", inputs=inputs, params={"shift": [1, 1]}, work_dir=tmp_path
    )
    meta_shift = res_shift[0]["metadata"]
    assert meta_shift["physical_pixel_sizes"] == metadata["physical_pixel_sizes"]
    assert meta_shift["channel_names"] == metadata["channel_names"]


def test_execute_label_returns_labels_and_counts_json(adapter, mock_module, tmp_path):
    # Setup data
    data = np.zeros((10, 10), dtype=np.float32)
    data[2:5, 2:5] = 1.0
    data[7:9, 7:9] = 1.0
    uri = "obj://label_input"
    OBJECT_CACHE[uri] = data

    inputs = [("image", {"uri": uri, "metadata": {"axes": "YX"}})]

    # Mock label to return (data, 2)
    mock_module.label = MagicMock(return_value=(data.astype(np.int32), 2))

    results = adapter.execute(
        fn_id="scipy.ndimage.label", inputs=inputs, params={}, work_dir=tmp_path
    )

    assert len(results) == 2
    labels_ref = next(r for r in results if r.get("type") == "LabelImageRef")
    counts_ref = next(r for r in results if r.get("format") == "json")

    assert labels_ref["path"].endswith("labels.ome.zarr")
    assert counts_ref["path"].endswith("counts.json")

    assert Path(labels_ref["path"]).exists()
    assert Path(counts_ref["path"]).exists()

    import json

    with open(counts_ref["path"]) as f:
        counts = json.load(f)
    assert counts["num_features"] == 2


def test_execute_center_of_mass_json_index_and_missing_labels(adapter, mock_module, tmp_path):
    # Setup intensity image
    img_data = np.ones((10, 10), dtype=np.float32)
    # Setup labels: only label 1 is present
    labels_data = np.zeros((10, 10), dtype=np.int32)
    labels_data[2:5, 2:5] = 1

    img_uri = "obj://com_img"
    labels_uri = "obj://com_labels"
    OBJECT_CACHE[img_uri] = img_data
    OBJECT_CACHE[labels_uri] = labels_data

    inputs = [
        ("image", {"uri": img_uri}),
        ("labels", {"uri": labels_uri, "type": "LabelImageRef"}),
    ]
    # Request labels 1 (present) and 3 (missing)
    params = {"index": [1, 3]}

    # Mock center_of_mass to return results for 2 labels
    mock_module.center_of_mass = MagicMock(return_value=[(3.0, 3.0), (0.0, 0.0)])

    results = adapter.execute(
        fn_id="scipy.ndimage.center_of_mass", inputs=inputs, params=params, work_dir=tmp_path
    )

    assert len(results) == 1
    out = results[0]
    assert out["format"] == "json"

    import json

    with open(out["path"]) as f:
        payload = json.load(f)

    # Label 1 should be (3.0, 3.0)
    assert payload["1"] == [3.0, 3.0]
    # Label 3 should be null because it's missing from labels_data
    assert payload["3"] is None

    # Verify mock call - CRITICAL wiring proof
    call_args, call_kwargs = mock_module.center_of_mass.call_args
    # First positional arg is image_data
    assert np.all(call_args[0] == img_data)
    # labels should be passed in params
    assert "labels" in call_kwargs
    assert np.all(call_kwargs["labels"] == labels_data)


def test_execute_extrema_json_missing_labels(adapter, mock_module, tmp_path):
    # Setup labels: label 5 is missing
    labels_data = np.zeros((5, 5), dtype=np.int32)
    labels_data[0:2, 0:2] = 1
    labels_uri = "obj://extrema_labels"
    OBJECT_CACHE[labels_uri] = labels_data

    inputs = [
        ("image", {"uri": "obj://any"}),
        ("labels", {"uri": labels_uri, "type": "LabelImageRef"}),
    ]
    OBJECT_CACHE["obj://any"] = np.ones((5, 5))

    params = {"index": [5]}

    # Mock extrema to return a tuple (min, max, min_loc, max_loc)
    mock_module.extrema = MagicMock(return_value=(0.0, 1.0, (0, 0), (1, 1)))

    results = adapter.execute(
        fn_id="scipy.ndimage.extrema", inputs=inputs, params=params, work_dir=tmp_path
    )

    import json

    with open(results[0]["path"]) as f:
        payload = json.load(f)

    assert payload == {"5": None}


def test_execute_sum_or_mean_json_scalar_output(adapter, mock_module, tmp_path):
    labels_data = np.zeros((5, 5), dtype=np.int32)
    labels_data[0:2, 0:2] = 1
    labels_uri = "obj://sum_labels"
    OBJECT_CACHE[labels_uri] = labels_data

    inputs = [
        ("image", {"uri": "obj://any"}),
        ("labels", {"uri": labels_uri, "type": "LabelImageRef"}),
    ]
    OBJECT_CACHE["obj://any"] = np.ones((5, 5))

    # Single index
    params = {"index": 1}
    mock_module.sum = MagicMock(return_value=10.0)

    results = adapter.execute(
        fn_id="scipy.ndimage.sum", inputs=inputs, params=params, work_dir=tmp_path
    )

    import json

    with open(results[0]["path"]) as f:
        payload = json.load(f)

    assert payload == {"1": 10.0}


def test_execute_fourier_complex_workflow(adapter, tmp_path):
    # Setup mock for scipy.fft
    mock_fft = MagicMock()

    # fftn returns complex data
    complex_data = (np.random.rand(4, 4) + 1j * np.random.rand(4, 4)).astype(np.complex128)
    mock_fft.fftn = MagicMock(return_value=complex_data)

    # ifftn returns complex, but we'll test the auto-real-cast
    real_data = np.random.rand(4, 4).astype(np.float32)
    # Return complex with effectively zero imaginary part
    mock_fft.ifftn = MagicMock(return_value=real_data.astype(np.complex128))

    real_import = importlib.import_module

    def side_effect(name, *args, **kwargs):
        if name == "scipy.fft":
            return mock_fft
        return real_import(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=side_effect):
        # 1) Test FFT (Real -> Complex)
        uri_real = "obj://fft_input"
        OBJECT_CACHE[uri_real] = np.random.rand(4, 4).astype(np.float32)

        res_fft = adapter.execute(
            fn_id="scipy.fft.fftn",
            inputs=[("image", {"uri": uri_real})],
            params={},
            work_dir=tmp_path,
        )

        assert "complex" in res_fft[0]["metadata"]["dtype"]

        # 2) Test IFFT (Complex -> Real auto-cast)
        uri_complex = "obj://ifft_input"
        OBJECT_CACHE[uri_complex] = complex_data

        res_ifft = adapter.execute(
            fn_id="scipy.fft.ifftn",
            inputs=[("image", {"uri": uri_complex})],
            params={},
            work_dir=tmp_path,
        )

        # Should be cast to real because mock returns complex with 0 imag
        assert res_ifft[0]["metadata"]["dtype"] == "float64"  # complex128.real is float64


def test_determine_io_pattern_fourier(adapter):
    # Test fourier functions in ndimage
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "fourier_gaussian")
        == IOPattern.IMAGE_TO_IMAGE
    )
    # Test fft module functions
    assert adapter.determine_io_pattern("scipy.fft", "fft") == IOPattern.IMAGE_TO_IMAGE
    assert adapter.determine_io_pattern("scipy.fft", "ifft2") == IOPattern.IMAGE_TO_IMAGE
