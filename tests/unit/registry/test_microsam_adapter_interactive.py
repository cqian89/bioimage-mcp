from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from bioimage_mcp.registry.dynamic.adapters.microsam import (
    HeadlessDisplayRequiredError,
    MicrosamAdapter,
)


def test_microsam_adapter_interactive_headless_error():
    adapter = MicrosamAdapter()

    with (
        patch("os.environ", {"DISPLAY": None, "WAYLAND_DISPLAY": None}),
        patch("sys.platform", "linux"),
    ):
        with pytest.raises(HeadlessDisplayRequiredError) as exc:
            adapter._check_gui_available()
        assert "HEADLESS_DISPLAY_REQUIRED" in str(exc.value.code)


def test_microsam_adapter_interactive_2d_success(tmp_path):
    adapter = MicrosamAdapter()

    # Mock image data
    image_data = np.zeros((10, 10), dtype=np.uint8)
    image_artifact = {
        "type": "BioImageRef",
        "uri": "file:///tmp/image.tif",
        "path": "/tmp/image.tif",
        "metadata": {"axes": "YX"},
    }

    # Mock labels to export
    labels_data = np.ones((10, 10), dtype=np.uint32)

    mock_napari = MagicMock()
    mock_sam_annotator = MagicMock()
    mock_viewer = MagicMock()
    mock_viewer.layers = {"committed_objects": MagicMock(data=labels_data)}
    mock_sam_annotator.annotator_2d.return_value = mock_viewer

    with (
        patch.dict(
            "sys.modules",
            {"napari": mock_napari, "micro_sam": MagicMock(sam_annotator=mock_sam_annotator)},
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._load_image",
            return_value=image_data,
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._check_gui_available"
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._save_image"
        ) as mock_save,
    ):
        mock_save.return_value = {"type": "LabelImageRef", "uri": "file:///tmp/out.zarr"}

        results = adapter.execute(
            fn_id="micro_sam.sam_annotator.annotator_2d",
            inputs=[image_artifact],
            params={"device": "cpu"},
            work_dir=tmp_path,
        )

        assert len(results) == 1
        assert results[0]["type"] == "LabelImageRef"

        # Verify call arguments
        call_args = mock_sam_annotator.annotator_2d.call_args[1]
        assert np.array_equal(call_args["image"], image_data)
        assert call_args["device"] == "cpu"
        assert call_args["return_viewer"] is True

        assert mock_napari.run.called


def test_microsam_adapter_interactive_no_changes(tmp_path):
    adapter = MicrosamAdapter()

    image_data = np.zeros((10, 10), dtype=np.uint8)
    image_artifact = {"type": "BioImageRef", "uri": "file:///tmp/image.tif"}

    mock_napari = MagicMock()
    mock_sam_annotator = MagicMock()
    mock_viewer = MagicMock()
    mock_viewer.layers = {}  # No committed_objects layer
    mock_sam_annotator.annotator_2d.return_value = mock_viewer

    with (
        patch.dict(
            "sys.modules",
            {"napari": mock_napari, "micro_sam": MagicMock(sam_annotator=mock_sam_annotator)},
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._load_image",
            return_value=image_data,
        ),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._check_gui_available"
        ),
    ):
        results = adapter.execute(
            fn_id="micro_sam.sam_annotator.annotator_2d",
            inputs=[image_artifact],
            params={},
            work_dir=tmp_path,
        )

        assert len(results) == 0
        assert "MICROSAM_NO_CHANGES" in adapter.warnings
