"""Failing tests for ax parameter passthrough in PhasorPyAdapter."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from bioio.writers import OmeTiffWriter
from PIL import Image

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

    # 5. Verify file can be saved and has content
    assert plot_path.exists()

    # Check for substantial pixel variation (not just blank axes)
    img = Image.open(plot_path).convert("L")  # Grayscale
    data = np.array(img)
    variance = np.var(data)
    unique_values = len(np.unique(data))

    # A blank plot with just axes has lower variance than a plot with phasor cloud
    # Threshold determined empirically: blank axes ~400-600, with phasor cloud ~2000+
    assert variance > 1000, f"Plot appears blank (variance={variance})"
    assert unique_values > 50, f"Plot lacks detail (only {unique_values} unique values)"


@pytest.mark.slow
@pytest.mark.integration
def test_phasor_plot_content_regression(adapter, tmp_path):
    """Regression test: Saved phasor plot must contain plotted content, not just axes.

    This guards against the bug where plot_phasor drew on an internal figure
    but we saved a different (blank) figure.
    """
    import uuid

    # 1. Create real phasor data (not zeros - use realistic values)
    # Using specific ranges to ensure visible cloud
    real_data = np.random.uniform(0.2, 0.8, (100, 100)).astype(np.float32)
    imag_data = np.random.uniform(0.1, 0.5, (100, 100)).astype(np.float32)

    real_path = tmp_path / "reg_real.ome.tiff"
    imag_path = tmp_path / "reg_imag.ome.tiff"
    OmeTiffWriter.save(real_data, str(real_path), dim_order="YX")
    OmeTiffWriter.save(imag_data, str(imag_path), dim_order="YX")

    real_art = create_mock_artifact("reg_real", real_path)
    imag_art = create_mock_artifact("reg_imag", imag_path)

    # 2. Create figure/axes like subplots would
    fig, ax = plt.subplots()

    # 3. Store axes in OBJECT_CACHE
    ax_uri = f"obj://test/{uuid.uuid4()}"
    OBJECT_CACHE[ax_uri] = ax

    # 4. Create input artifacts and call plot_phasor with ax
    adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[
            ("real", real_art),
            ("imag", imag_art),
        ],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax1"}},
        work_dir=tmp_path,
    )

    # 5. Save the figure (the original figure, not gcf())
    plot_path = tmp_path / "regression_plot.png"
    fig.savefig(str(plot_path))
    plt.close(fig)

    # 6. Verify content: Load image and check for substantial pixel variation
    img = Image.open(plot_path).convert("L")  # Grayscale
    data = np.array(img)

    variance = np.var(data)
    unique_values = len(np.unique(data))

    # A blank plot with just axes has lower variance than a plot with phasor cloud
    # Threshold determined empirically: blank axes ~400-600, with phasor cloud ~2000+
    assert variance > 1000, f"Plot appears blank (variance={variance})"

    # Also verify we have multiple distinct intensity levels
    assert unique_values > 50, f"Plot lacks detail (only {unique_values} unique values)"
