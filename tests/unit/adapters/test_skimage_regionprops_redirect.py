import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter
from bioimage_mcp.artifacts.models import ArtifactRef


def test_regionprops_redirect_to_regionprops_table():
    """
    Test that calling regionprops redirects to regionprops_table and adds a notice.
    """
    adapter = SkimageAdapter()

    # Create dummy label image
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[2:5, 2:5] = 1
    labels[7:9, 7:9] = 2

    # Create artifact ref for labels
    labels_ref = {
        "type": "LabelImageRef",
        "uri": "file:///tmp/labels.tif",
        "path": "/tmp/labels.tif",
        "metadata": {"axes": "YX"},
    }

    # Mock _load_image to return our labels
    with patch.object(adapter, "_load_image", return_value=labels):
        # Mock the actual skimage functions
        with patch("skimage.measure.regionprops") as mock_rp:
            with patch("skimage.measure.regionprops_table") as mock_rpt:
                # Mock regionprops_table to return a dict (as it normally does)
                mock_rpt.return_value = {
                    "label": np.array([1, 2]),
                    "area": np.array([9, 4]),
                    "centroid-0": np.array([3.0, 7.5]),
                    "centroid-1": np.array([3.0, 7.5]),
                }

                # Execute regionprops
                outputs = adapter.execute(
                    fn_id="skimage.measure.regionprops",
                    inputs=[("labels", labels_ref)],
                    params={"cache": True, "offset": (0, 0)},  # offset is only in regionprops
                )

                # Verify regionprops was NOT called
                assert not mock_rp.called

                # Verify regionprops_table WAS called
                assert mock_rpt.called

                # Verify params were mapped correctly
                args, kwargs = mock_rpt.call_args
                assert np.array_equal(args[0], labels)
                assert kwargs["cache"] is True
                assert "offset" not in kwargs  # Should be dropped
                # Should have default properties
                assert "properties" in kwargs
                assert "label" in kwargs["properties"]

                # Verify output is a TableRef (CSV)
                assert len(outputs) == 1
                assert outputs[0]["type"] == "TableRef"

                # Verify notice is present
                assert "notice" in outputs[0]
                assert "redirected" in outputs[0]["notice"].lower()
                assert "regionprops_table" in outputs[0]["notice"]


def test_regionprops_table_no_redirect():
    """
    Test that calling regionprops_table directly works as expected without a redirect notice.
    """
    adapter = SkimageAdapter()

    # Create dummy label image
    labels = np.zeros((10, 10), dtype=np.int32)

    # Create artifact ref for labels
    labels_ref = {
        "type": "LabelImageRef",
        "uri": "file:///tmp/labels.tif",
        "path": "/tmp/labels.tif",
        "metadata": {"axes": "YX"},
    }

    # Mock _load_image to return our labels
    with patch.object(adapter, "_load_image", return_value=labels):
        with patch("skimage.measure.regionprops_table") as mock_rpt:
            mock_rpt.return_value = {"label": np.array([1])}

            # Execute regionprops_table directly
            outputs = adapter.execute(
                fn_id="skimage.measure.regionprops_table",
                inputs=[("labels", labels_ref)],
                params={"properties": ["label"]},
            )

            assert mock_rpt.called
            assert len(outputs) == 1
            assert outputs[0]["type"] == "TableRef"
            assert "notice" not in outputs[0]


def test_regionprops_discovery():
    """
    Verify that regionprops is still discovered by the adapter.
    """
    adapter = SkimageAdapter()
    module_config = {
        "module_name": "skimage.measure",
        "include": ["regionprops"],
    }
    discovered = adapter.discover(module_config)
    assert len(discovered) == 1
    assert discovered[0].name == "regionprops"
    assert discovered[0].fn_id == "skimage.measure.regionprops"


if __name__ == "__main__":
    pytest.main([__file__])
