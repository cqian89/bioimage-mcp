"""Tests for matplotlib.pyplot.imsave."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np


def test_imsave_with_user_path():
    """imsave should save to user-provided path."""
    from bioimage_mcp_base.ops.matplotlib_ops import OBJECT_CACHE, imsave

    # Create test image data
    arr = np.random.rand(100, 100)

    # Store in cache
    uri = "obj://test-session/base/test-arr"
    OBJECT_CACHE[uri] = arr

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test_image.png"

        inputs = [("image", {"type": "ObjectRef", "uri": uri})]
        params = {"fname": str(out_path)}

        with patch("bioimage_mcp_base.ops.matplotlib_ops.plt.imsave") as mock_imsave:
            result = imsave(inputs, params, work_dir=Path(tmpdir))

        mock_imsave.assert_called_once()
        call_args = mock_imsave.call_args
        assert call_args[0][0] == str(out_path)

        # Verify result
        assert result[0]["path"] == str(out_path.absolute())
        assert result[0]["type"] == "PlotRef"

    # Clean up
    if uri in OBJECT_CACHE:
        del OBJECT_CACHE[uri]


def test_imsave_autogenerates_path():
    """imsave should auto-generate path when fname not provided."""
    from bioimage_mcp_base.ops.matplotlib_ops import OBJECT_CACHE, imsave

    arr = np.random.rand(100, 100)

    uri = "obj://test-session/base/test-arr2"
    OBJECT_CACHE[uri] = arr

    with tempfile.TemporaryDirectory() as tmpdir:
        inputs = [("image", {"type": "ObjectRef", "uri": uri})]
        params = {"format": "png"}  # No fname

        with patch("bioimage_mcp_base.ops.matplotlib_ops.plt.imsave") as mock_imsave:
            result = imsave(inputs, params, work_dir=Path(tmpdir))

        mock_imsave.assert_called_once()
        call_path = mock_imsave.call_args[0][0]
        assert tmpdir in call_path
        assert "image_" in call_path

    # Clean up
    if uri in OBJECT_CACHE:
        del OBJECT_CACHE[uri]
