"""Failing tests for ax parameter passthrough in PhasorPyAdapter."""

import matplotlib.pyplot as plt
import numpy as np
import pytest
from pathlib import Path
from PIL import Image
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


def create_mock_artifact(ref_id: str, path: Path, fmt: str = "OME-TIFF"):
    """Helper to create a mock artifact dict."""
    return {
        "ref_id": ref_id,
        "type": "BioImageRef",
        "uri": f"file://{path.absolute()}",
        "path": str(path.absolute()),
        "format": fmt,
        "metadata": {"axes": "YX", "shape": [32, 32]},
    }


@pytest.fixture
def adapter():
    return PhasorPyAdapter()


@pytest.fixture(autouse=True)
def clear_cache():
    OBJECT_CACHE.clear()
    yield
    OBJECT_CACHE.clear()


@pytest.fixture
def phasor_inputs(tmp_path):
    """Fixture to provide real/imag OME-TIFF artifacts."""
    real = np.random.rand(32, 32).astype(np.float32)
    imag = np.random.rand(32, 32).astype(np.float32)

    real_path = tmp_path / "real.ome.tiff"
    imag_path = tmp_path / "imag.ome.tiff"
    OmeTiffWriter.save(real, str(real_path), dim_order="YX")
    OmeTiffWriter.save(imag, str(imag_path), dim_order="YX")

    return {
        "real": create_mock_artifact("real", real_path),
        "imag": create_mock_artifact("imag", imag_path),
    }


@pytest.mark.slow
@pytest.mark.integration
def test_plot_uses_provided_axes(adapter, phasor_inputs, tmp_path):
    """Verify that 'ax' in params is extracted and passed to plot_phasor.

    This test verifies that the phasor plot is actually drawn on the provided axes
    by checking the number of artists (children) before and after execution.
    """
    fig, ax = plt.subplots()
    ax_uri = "obj://session/env/ax1"
    OBJECT_CACHE[ax_uri] = ax

    # Initial children count (usually just spines, ticks, etc.)
    initial_children = len(ax.get_children())

    adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[
            ("real", phasor_inputs["real"]),
            ("imag", phasor_inputs["imag"]),
        ],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax1"}},
        work_dir=tmp_path,
    )

    # After plotting, there should be more children (the phasor plot)
    assert len(ax.get_children()) > initial_children, (
        "Expected axes to have plot content, but it's empty. Adapter likely dropped 'ax' parameter."
    )
    plt.close(fig)


@pytest.mark.slow
@pytest.mark.integration
def test_subplots_plot_phasor_savefig_workflow(adapter, phasor_inputs, tmp_path):
    """End-to-end: subplots → plot_phasor(ax=...) → savefig has content.

    This simulates the full MCP workflow and verifies visual content.
    """
    # 1. Mock subplots output
    fig, ax = plt.subplots()
    fig_uri = "obj://session/env/fig1"
    ax_uri = "obj://session/env/ax1"
    OBJECT_CACHE[fig_uri] = fig
    OBJECT_CACHE[ax_uri] = ax

    # 2. Call plot_phasor with ax
    initial_children = len(ax.get_children())
    adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[
            ("real", phasor_inputs["real"]),
            ("imag", phasor_inputs["imag"]),
        ],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax1"}},
        work_dir=tmp_path,
    )

    # 3. Assert new content was added to our axes
    assert len(ax.get_children()) > initial_children, (
        "Phasor plot was not drawn on the provided axes"
    )

    # 4. Save figure to verify file exists
    plot_path = tmp_path / "final_plot.png"
    fig.savefig(str(plot_path))
    plt.close(fig)

    # 5. Verify file can be saved
    assert plot_path.exists()
