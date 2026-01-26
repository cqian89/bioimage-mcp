"""
Contract tests for ScipyNdimageAdapter.

Verifies that ScipyNdimageAdapter correctly implements the BaseAdapter protocol
for discovering and executing scipy.ndimage functions.
"""

from unittest.mock import MagicMock, patch

from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_scipy_adapter_discovers_gaussian_filter():
    """discover() should return metadata for scipy.ndimage.gaussian_filter."""
    adapter = ScipyNdimageAdapter()

    module_config = {
        "module_name": "scipy.ndimage",
        "include": ["gaussian_filter"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    fn_meta = discovered[0]
    assert fn_meta.name == "gaussian_filter"
    assert fn_meta.module == "scipy.ndimage"
    assert fn_meta.qualified_name == "scipy.ndimage.gaussian_filter"
    assert fn_meta.fn_id == "scipy.ndimage.gaussian_filter"


def test_scipy_adapter_discovers_sobel():
    """discover() should return metadata for scipy.ndimage.sobel."""
    adapter = ScipyNdimageAdapter()

    module_config = {
        "module_name": "scipy.ndimage",
        "include": ["sobel"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    fn_meta = discovered[0]
    assert fn_meta.name == "sobel"
    assert fn_meta.module == "scipy.ndimage"
    assert fn_meta.qualified_name == "scipy.ndimage.sobel"
    assert fn_meta.fn_id == "scipy.ndimage.sobel"


def test_scipy_adapter_resolves_io_pattern_defaults():
    """resolve_io_pattern should default to IMAGE_TO_IMAGE for scipy.ndimage."""
    adapter = ScipyNdimageAdapter()

    mock_signature = MagicMock()

    # Most scipy.ndimage functions are image-to-image transformations
    assert adapter.resolve_io_pattern("gaussian_filter", mock_signature) == IOPattern.IMAGE_TO_IMAGE
    assert adapter.resolve_io_pattern("sobel", mock_signature) == IOPattern.IMAGE_TO_IMAGE
    assert adapter.resolve_io_pattern("median_filter", mock_signature) == IOPattern.IMAGE_TO_IMAGE
    assert adapter.resolve_io_pattern("zoom", mock_signature) == IOPattern.IMAGE_TO_IMAGE


def test_scipy_adapter_io_pattern_inference_for_ndimage():
    """module-level inference should drive IO pattern selection for scipy.ndimage."""
    adapter = ScipyNdimageAdapter()

    # scipy.ndimage filters are predominantly image-to-image
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "gaussian_filter") == IOPattern.IMAGE_TO_IMAGE
    )
    assert adapter.determine_io_pattern("scipy.ndimage", "sobel") == IOPattern.IMAGE_TO_IMAGE
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "median_filter") == IOPattern.IMAGE_TO_IMAGE
    )

    # Morphological operations are also image-to-image
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "binary_erosion") == IOPattern.IMAGE_TO_IMAGE
    )
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "binary_dilation") == IOPattern.IMAGE_TO_IMAGE
    )


def test_scipy_adapter_discover_uses_module_context_for_io_pattern():
    """discover() should use module context for IO patterns."""
    adapter = ScipyNdimageAdapter()

    module_config = {
        "module_name": "scipy.ndimage",
        "include": ["gaussian_filter", "sobel"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 2
    # All discovered functions should have IMAGE_TO_IMAGE pattern
    for fn_meta in discovered:
        assert fn_meta.io_pattern == IOPattern.IMAGE_TO_IMAGE


@patch("bioio.BioImage")
@patch("scipy.ndimage.gaussian_filter")
def test_scipy_adapter_execute_calls_gaussian_filter(mock_gaussian_filter, mock_bioimage):
    """execute() should call scipy.ndimage.gaussian_filter and return ArtifactRefs."""
    import numpy as np

    adapter = ScipyNdimageAdapter()

    # Mock image loading to return a fake array
    mock_img = MagicMock()
    mock_img.reader.data = np.zeros((10, 10))
    mock_bioimage.return_value = mock_img
    mock_gaussian_filter.return_value = np.zeros((10, 10))

    input_artifact = ArtifactRef(
        ref_id="test-image-1",
        type="BioImageRef",
        uri="file:///tmp/test_image.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )

    outputs = adapter.execute(
        fn_id="scipy.ndimage.gaussian_filter",
        inputs=[("image", input_artifact)],
        params={"sigma": 2.0},
    )

    assert mock_gaussian_filter.called
    assert isinstance(outputs, list)
    assert len(outputs) == 1
    assert isinstance(outputs[0], dict)
    assert outputs[0]["type"] == "BioImageRef"


@patch("bioio.BioImage")
@patch("scipy.ndimage.sobel")
def test_scipy_adapter_execute_calls_sobel(mock_sobel, mock_bioimage):
    """execute() should call scipy.ndimage.sobel and return ArtifactRefs."""
    import numpy as np

    adapter = ScipyNdimageAdapter()

    # Mock image loading to return a fake array
    mock_img = MagicMock()
    mock_img.reader.data = np.zeros((10, 10))
    mock_bioimage.return_value = mock_img
    mock_sobel.return_value = np.zeros((10, 10))

    input_artifact = ArtifactRef(
        ref_id="test-image-2",
        type="BioImageRef",
        uri="file:///tmp/test_image.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )

    outputs = adapter.execute(
        fn_id="scipy.ndimage.sobel",
        inputs=[("image", input_artifact)],
        params={},
    )

    assert mock_sobel.called
    assert isinstance(outputs, list)
    assert len(outputs) == 1
    assert isinstance(outputs[0], dict)
    assert outputs[0]["type"] == "BioImageRef"


def test_scipy_adapter_signature_analysis():
    """Adapter should correctly analyze function signatures."""
    adapter = ScipyNdimageAdapter()

    module_config = {
        "module_name": "scipy.ndimage",
        "include": ["gaussian_filter"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    fn_meta = discovered[0]

    # Should have analyzed the signature and identified key parameters
    # gaussian_filter has parameters like: input, sigma, order, output, mode, cval, truncate
    assert fn_meta.parameters is not None
    assert len(fn_meta.parameters) > 0


def test_scipy_adapter_discovers_label():
    """discover() should return metadata for scipy.ndimage.label with correct pattern."""
    adapter = ScipyNdimageAdapter()

    module_config = {
        "module_name": "scipy.ndimage",
        "include": ["label"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    fn_meta = discovered[0]
    assert fn_meta.name == "label"
    assert fn_meta.io_pattern == IOPattern.IMAGE_TO_LABELS_AND_JSON


def test_scipy_adapter_io_pattern_inference_for_measurements():
    """Adapter should correctly identify IO patterns for measurements and labeling."""
    adapter = ScipyNdimageAdapter()

    assert (
        adapter.determine_io_pattern("scipy.ndimage", "label") == IOPattern.IMAGE_TO_LABELS_AND_JSON
    )
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "center_of_mass")
        == IOPattern.IMAGE_AND_LABELS_TO_JSON
    )
    assert (
        adapter.determine_io_pattern("scipy.ndimage", "mean") == IOPattern.IMAGE_AND_LABELS_TO_JSON
    )


@patch("bioio.BioImage")
@patch("scipy.ndimage.label")
def test_scipy_adapter_execute_label(mock_label, mock_bioimage):
    """execute() for label should return two artifacts (labels and count)."""
    import numpy as np

    adapter = ScipyNdimageAdapter()

    mock_img = MagicMock()
    mock_img.reader.data = np.zeros((10, 10))
    mock_bioimage.return_value = mock_img

    labeled = np.zeros((10, 10), dtype=np.int32)
    labeled[1:3, 1:3] = 1
    mock_label.return_value = (labeled, 1)

    input_artifact = {
        "ref_id": "test-image",
        "type": "BioImageRef",
        "uri": "file:///tmp/test.tif",
        "metadata": {"axes": "YX"},
    }

    outputs = adapter.execute(
        fn_id="scipy.ndimage.label",
        inputs=[("image", input_artifact)],
        params={},
    )

    assert mock_label.called
    assert len(outputs) == 2
    # First output should be labels
    assert outputs[0]["type"] == "LabelImageRef"
    assert outputs[0]["metadata"]["output_name"] == "labels"
    # Second output should be count (JSON)
    assert outputs[1]["type"] == "NativeOutputRef"
    assert outputs[1]["metadata"]["output_name"] == "counts"


@patch("bioio.BioImage")
@patch("scipy.ndimage.mean")
def test_scipy_adapter_execute_measurement(mock_mean, mock_bioimage):
    """execute() for measurements should return a JSON artifact."""
    import numpy as np

    adapter = ScipyNdimageAdapter()

    mock_img = MagicMock()
    mock_img.reader.data = np.zeros((10, 10))
    mock_bioimage.return_value = mock_img
    mock_mean.return_value = 5.5

    input_artifact = {
        "ref_id": "test-image",
        "type": "BioImageRef",
        "uri": "file:///tmp/test.tif",
    }

    outputs = adapter.execute(
        fn_id="scipy.ndimage.mean",
        inputs=[("image", input_artifact)],
        params={},
    )

    assert mock_mean.called
    assert len(outputs) == 1
    assert outputs[0]["type"] == "NativeOutputRef"
    assert outputs[0]["format"] == "json"
