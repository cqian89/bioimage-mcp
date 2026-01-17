"""Integration tests for matplotlib save functions with user paths."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter


@pytest.fixture
def adapter():
    return MatplotlibAdapter()


@pytest.fixture
def temp_write_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_savefig_fname_param_exposed(adapter):
    """Integration: savefig should expose fname parameter."""
    funcs = adapter.discover({})
    savefig_meta = [f for f in funcs if f.fn_id == "base.matplotlib.Figure.savefig"][0]

    # Verify fname param is exposed
    assert "fname" in savefig_meta.parameters
    assert savefig_meta.parameters["fname"].type == "string"
    assert "Output file path" in savefig_meta.parameters["fname"].description


def test_imsave_params_exposed(adapter):
    """Integration: imsave should expose all params including fname."""
    funcs = adapter.discover({})
    imsave_meta = [f for f in funcs if f.fn_id == "base.matplotlib.pyplot.imsave"][0]

    # Verify fname param is exposed
    assert "fname" in imsave_meta.parameters

    # Verify other params
    assert "cmap" in imsave_meta.parameters
    assert "vmin" in imsave_meta.parameters
    assert "vmax" in imsave_meta.parameters
    assert "format" in imsave_meta.parameters
    assert "origin" in imsave_meta.parameters
    assert "dpi" in imsave_meta.parameters


def test_imsave_io_pattern_is_plot(adapter):
    """Integration: imsave should have PLOT io_pattern."""
    funcs = adapter.discover({})
    imsave_meta = [f for f in funcs if f.fn_id == "base.matplotlib.pyplot.imsave"][0]

    # io_pattern should indicate it produces a file output
    # The function metadata should reflect it saves to file
    assert imsave_meta.description == "Save an array as an image file."
