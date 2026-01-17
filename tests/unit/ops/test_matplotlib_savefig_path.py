"""Tests for savefig with user-provided path."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_savefig_uses_provided_fname():
    """savefig should use fname when provided."""
    from bioimage_mcp_base.ops.matplotlib_ops import savefig, OBJECT_CACHE

    # Create a mock figure
    mock_fig = MagicMock()
    mock_fig.dpi = 100
    mock_fig.get_size_inches.return_value = (8, 6)

    # Register in cache
    uri = "obj://test-session/matplotlib/fig-123"
    OBJECT_CACHE[uri] = mock_fig

    inputs = [("figure", {"uri": uri, "type": "ObjectRef"})]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "my_plot.png"
        params = {"fname": str(out_path)}

        with patch("bioimage_mcp_base.ops.matplotlib_ops.plt"):
            result = savefig(inputs, params, work_dir=Path(tmpdir))

        # Should have called savefig with user path
        mock_fig.savefig.assert_called_once()
        call_args = mock_fig.savefig.call_args
        # The first argument to savefig should be the path
        assert str(out_path) == str(call_args[0][0])

        # Result should reference user path
        assert result[0]["path"] == str(out_path.absolute())

    # Clean up
    if uri in OBJECT_CACHE:
        del OBJECT_CACHE[uri]


def test_savefig_autogenerates_without_fname():
    """savefig should auto-generate path when fname not provided."""
    from bioimage_mcp_base.ops.matplotlib_ops import savefig, OBJECT_CACHE

    mock_fig = MagicMock()
    mock_fig.dpi = 100
    mock_fig.get_size_inches.return_value = (8, 6)

    uri = "obj://test-session/matplotlib/fig-456"
    OBJECT_CACHE[uri] = mock_fig

    inputs = [("figure", {"uri": uri, "type": "ObjectRef"})]

    with tempfile.TemporaryDirectory() as tmpdir:
        params = {"format": "png"}  # No fname

        with patch("bioimage_mcp_base.ops.matplotlib_ops.plt"):
            result = savefig(inputs, params, work_dir=Path(tmpdir))

        # Should have auto-generated path in work_dir
        result_path = Path(result[0]["path"])
        # Use resolve() to handle case variations or symlinks if any, though here absolute() should match
        assert result_path.parent.resolve() == Path(tmpdir).resolve()
        assert "plot_" in result_path.name

    # Clean up
    if uri in OBJECT_CACHE:
        del OBJECT_CACHE[uri]
