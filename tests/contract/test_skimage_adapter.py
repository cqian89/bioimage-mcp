"""
Contract tests for SkimageAdapter.

Verifies that SkimageAdapter correctly implements the BaseAdapter protocol
for discovering and executing scikit-image functions.
"""

from unittest.mock import MagicMock, patch

from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_skimage_adapter_discovers_gaussian():
    """discover() should return metadata for skimage.filters.gaussian."""
    adapter = SkimageAdapter()

    module_config = {
        "module_name": "skimage.filters",
        "include": ["gaussian"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    fn_meta = discovered[0]
    assert fn_meta.name == "gaussian"
    assert fn_meta.module == "skimage.filters"
    assert fn_meta.qualified_name == "skimage.filters.gaussian"
    assert fn_meta.fn_id == "skimage.filters.gaussian"


def test_skimage_adapter_resolves_io_pattern_defaults_and_overrides():
    """resolve_io_pattern should use module defaults and overrides."""
    adapter = SkimageAdapter()

    mock_signature = MagicMock()

    assert adapter.resolve_io_pattern("gaussian", mock_signature) == IOPattern.IMAGE_TO_IMAGE
    assert adapter.resolve_io_pattern("threshold_otsu", mock_signature) == IOPattern.ARRAY_TO_SCALAR


def test_skimage_adapter_module_level_io_pattern_inference():
    """module-level inference should drive IO pattern selection."""
    adapter = SkimageAdapter()

    assert adapter.determine_io_pattern("skimage.filters", "gaussian") == IOPattern.IMAGE_TO_IMAGE
    assert adapter.determine_io_pattern("skimage.segmentation", "slic") == IOPattern.IMAGE_TO_LABELS
    assert (
        adapter.determine_io_pattern("skimage.measure", "regionprops_table")
        == IOPattern.LABELS_TO_TABLE
    )


def test_skimage_adapter_discover_uses_module_context_for_io_pattern():
    """discover() should use module context for IO patterns."""
    adapter = SkimageAdapter()

    module_config = {
        "module_name": "skimage.measure",
        "include": ["regionprops_table"],
    }

    discovered = adapter.discover(module_config)

    assert len(discovered) == 1
    assert discovered[0].io_pattern == IOPattern.LABELS_TO_TABLE


@patch("tifffile.imread")
@patch("skimage.filters.gaussian")
def test_skimage_adapter_execute_calls_gaussian(mock_gaussian, mock_imread):
    """execute() should call skimage.filters.gaussian and return ArtifactRefs."""
    import numpy as np

    adapter = SkimageAdapter()

    # Mock image loading to return a fake array
    mock_imread.return_value = np.zeros((10, 10))
    mock_gaussian.return_value = np.zeros((10, 10))

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
        fn_id="skimage.filters.gaussian",
        inputs=[input_artifact],
        params={"sigma": 1.25},
    )

    assert mock_gaussian.called
    assert isinstance(outputs, list)
    assert len(outputs) == 1
    assert isinstance(outputs[0], dict)
    assert outputs[0]["type"] == "BioImageRef"
