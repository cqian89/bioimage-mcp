"""
Unit tests for PhasorPyAdapter.
"""

from unittest.mock import MagicMock, patch

import numpy as np

from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter


def test_load_image_with_format_hint():
    """_load_image should use format hint to select the correct reader."""
    adapter = PhasorPyAdapter()

    # Create a mock artifact with an extensionless path but format="OME-TIFF"
    artifact = {"uri": "file:///tmp/extensionless_file", "format": "OME-TIFF"}

    # We want to verify that BioImage is called with reader=OmeTiffReader
    with patch("bioio.BioImage") as mock_bioimage:
        mock_img = MagicMock()
        mock_img.data = np.zeros((1, 1, 1, 10, 10))
        mock_bioimage.return_value = mock_img

        adapter._load_image(artifact)

        # Verify BioImage was called with the correct reader
        # Since we are mocking bioio_ome_tiff.Reader in the implementation,
        # we need to be careful how we check this in the test.
        # For now, let's just check that it WAS called with SOME reader if we can.

        args, kwargs = mock_bioimage.call_args
        assert args[0] == "/tmp/extensionless_file"
        assert "reader" in kwargs
        assert kwargs["reader"] is not None
        # We can further verify it's the OmeTiffReader if we import it
        from bioio_ome_tiff import Reader as OmeTiffReader

        assert kwargs["reader"] == OmeTiffReader


def test_load_image_ome_zarr_hint():
    """_load_image should use OME-Zarr format hint."""
    adapter = PhasorPyAdapter()

    artifact = {"uri": "file:///tmp/zarr_store", "format": "OME-Zarr"}

    with patch("bioio.BioImage") as mock_bioimage:
        mock_img = MagicMock()
        mock_img.data = np.zeros((1, 1, 1, 10, 10))
        mock_bioimage.return_value = mock_img

        adapter._load_image(artifact)

        args, kwargs = mock_bioimage.call_args
        from bioio_ome_zarr import Reader as OmeZarrReader

        assert kwargs["reader"] == OmeZarrReader


def test_load_image_object_artifact():
    """_load_image should work with Artifact object as well as dict."""
    adapter = PhasorPyAdapter()

    artifact = ArtifactRef(
        ref_id="test",
        type="BioImageRef",
        uri="file:///tmp/file.ome.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=0,
        created_at=ArtifactRef.now(),
    )

    with patch("bioio.BioImage") as mock_bioimage:
        mock_img = MagicMock()
        mock_img.data = np.zeros((1, 1, 1, 10, 10))
        mock_bioimage.return_value = mock_img

        adapter._load_image(artifact)

        args, kwargs = mock_bioimage.call_args
        from bioio_ome_tiff import Reader as OmeTiffReader

        assert kwargs["reader"] == OmeTiffReader
