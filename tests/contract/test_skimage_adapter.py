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


@patch("bioio_ome_zarr.writers.OMEZarrWriter")
def test_skimage_adapter_save_image_writes_axes_metadata(mock_writer_cls, tmp_path):
    """_save_image() should include axes metadata for OME-Zarr output."""
    import numpy as np

    adapter = SkimageAdapter()

    array = np.zeros((8, 6), dtype=np.uint8)
    adapter._save_image(array, work_dir=tmp_path)

    assert mock_writer_cls.call_count == 1
    _, kwargs = mock_writer_cls.call_args
    # OMEZarrWriter uses axes_names parameter
    assert kwargs["axes_names"] == ["y", "x"]


@patch("tifffile.imread")
@patch("skimage.measure.regionprops_table")
def test_skimage_adapter_execute_accepts_multiple_inputs(mock_regionprops, mock_imread, tmp_path):
    """execute() should pass multiple image inputs to regionprops_table."""
    import numpy as np

    adapter = SkimageAdapter()

    labels = np.ones((4, 4), dtype="int32")
    intensity = np.zeros((4, 4), dtype="float32")
    mock_imread.side_effect = [labels, intensity]
    mock_regionprops.return_value = {"label": np.array([1]), "area": np.array([16])}

    labels_ref = ArtifactRef(
        ref_id="labels-1",
        type="LabelImageRef",
        uri="file:///tmp/labels.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )
    intensity_ref = ArtifactRef(
        ref_id="image-1",
        type="BioImageRef",
        uri="file:///tmp/intensity.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )

    outputs = adapter.execute(
        fn_id="skimage.measure.regionprops_table",
        inputs=[("labels", labels_ref), ("intensity_image", intensity_ref)],
        params={},
        work_dir=tmp_path,
    )

    mock_regionprops.assert_called_once()
    called_args, called_kwargs = mock_regionprops.call_args
    assert np.array_equal(called_args[0], labels)
    assert np.array_equal(called_kwargs["intensity_image"], intensity)

    assert outputs[0]["type"] == "TableRef"
    assert outputs[0]["path"].endswith(".csv")


def test_skimage_adapter_dimension_hints_for_regionprops():
    """generate_dimension_hints should include regionprops and label in require_2d_or_3d."""
    adapter = SkimageAdapter()

    hint_regionprops = adapter.generate_dimension_hints("skimage.measure", "regionprops_table")
    assert hint_regionprops is not None
    assert hint_regionprops.squeeze_singleton is True
    assert hint_regionprops.min_ndim == 2
    assert hint_regionprops.max_ndim == 3

    hint_label = adapter.generate_dimension_hints("skimage.measure", "label")
    assert hint_label is not None
    assert hint_label.squeeze_singleton is True

    hint_gaussian = adapter.generate_dimension_hints("skimage.filters", "gaussian")
    assert hint_gaussian is not None
    assert hint_gaussian.squeeze_singleton is True


def test_skimage_adapter_omits_artifact_params_from_regionprops():
    """regionprops and regionprops_table should omit label_image/intensity_image from parameters."""
    adapter = SkimageAdapter()

    for name in ["regionprops", "regionprops_table"]:
        module_config = {
            "module_name": "skimage.measure",
            "include": [name],
        }

        discovered = adapter.discover(module_config)
        assert len(discovered) == 1
        fn_meta = discovered[0]

        # Artifact params should be removed
        assert "label_image" not in fn_meta.parameters
        assert "intensity_image" not in fn_meta.parameters
        assert "labels" not in fn_meta.parameters

        # They should also be removed from any higher-level schema representation if present
        # (DiscoveryEngine handles this, but adapter should too)


def test_skimage_threshold_local_method_has_enum():
    """Verify threshold_local method parameter has enum from docstring."""
    adapter = SkimageAdapter()
    discovered = adapter.discover(
        {
            "modules": ["skimage.filters"],
            "include": ["threshold_local"],
        }
    )

    assert len(discovered) == 1
    func = discovered[0]

    # Check method parameter has enum
    assert "method" in func.parameters
    method_param = func.parameters["method"]
    assert method_param.enum is not None
    assert set(method_param.enum) == {"generic", "gaussian", "mean", "median"}


def test_regionprops_table_properties_has_items_enum():
    """Verify regionprops_table properties parameter has items.enum from introspection."""
    adapter = SkimageAdapter()
    discovered = adapter.discover(
        {
            "modules": ["skimage.measure"],
            "include": ["regionprops_table"],
        }
    )

    assert len(discovered) == 1
    func = discovered[0]

    # Check properties parameter has items with enum
    assert "properties" in func.parameters
    props_param = func.parameters["properties"]

    assert props_param.items is not None
    assert "enum" in props_param.items
    enum_values = props_param.items["enum"]

    # Verify expected properties are present
    assert "area" in enum_values
    assert "centroid" in enum_values
    assert "label" in enum_values
    assert "bbox" in enum_values
    # Should have many properties (typically 30+)
    assert len(enum_values) >= 20
