"""Failing tests for ax parameter passthrough in PhasorPyAdapter."""

import numpy as np
import pytest
import matplotlib.pyplot as plt
from pathlib import Path
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


@pytest.mark.slow
@pytest.mark.integration
def test_ax_parameter_forwarded_to_phasorpy(adapter, tmp_path):
    """Verify that 'ax' in params is extracted and passed to plot_phasor.

    This test will fail because PhasorPyAdapter.execute drops VAR_KEYWORD params like 'ax'.
    """
    # Create mock real/imag data
    real = np.zeros((32, 32), dtype=np.float32)
    imag = np.zeros((32, 32), dtype=np.float32)

    from bioio.writers import OmeTiffWriter

    real_path = tmp_path / "real.ome.tiff"
    imag_path = tmp_path / "imag.ome.tiff"
    OmeTiffWriter.save(real, str(real_path), dim_order="YX")
    OmeTiffWriter.save(imag, str(imag_path), dim_order="YX")

    input_real = create_mock_artifact("real", real_path)
    input_imag = create_mock_artifact("imag", imag_path)

    # Create mock axes in OBJECT_CACHE
    fig, ax = plt.subplots()
    ax_uri = "obj://session/env/ax1"
    OBJECT_CACHE[ax_uri] = ax

    # Call adapter.execute with ax in params
    # We use a mock/spy for phasorpy.plot.plot_phasor if possible,
    # but here we'll just check if the internal figure of phasorpy was used or not.
    # Actually, the requirement is to verify it's FORWARDED.

    # In a real TDD scenario, we might want to check if plot_phasor was called with ax.
    # Since we are testing the adapter, we can check if it tries to pass it.

    outputs = adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[("real", input_real), ("imag", input_imag)],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax1"}},
        work_dir=tmp_path,
    )

    # If the adapter dropped 'ax', phasorpy would have created a new figure.
    # We can verify if our axes 'ax' has any new artists (like the phasor plot).
    # phasorpy's plot_phasor typically adds a collection or similar.
    # Standard for a fresh axes (4 spines, 2 axes, patch, etc) is around 10.
    initial_children = len(ax.get_children())

    outputs = adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[("real", input_real), ("imag", input_imag)],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax1"}},
        work_dir=tmp_path,
    )

    assert len(ax.get_children()) > initial_children, (
        "Expected axes to have plot content, but it's empty. Adapter likely dropped 'ax' parameter."
    )
    plt.close(fig)


@pytest.mark.slow
@pytest.mark.integration
def test_plot_uses_provided_axes(adapter, tmp_path):
    """Verify that phasor plot is drawn on the provided axes.

    Similar to above, but focuses on the content of the axes.
    """
    real = np.random.rand(32, 32).astype(np.float32)
    imag = np.random.rand(32, 32).astype(np.float32)

    from bioio.writers import OmeTiffWriter

    real_path = tmp_path / "real_2.ome.tiff"
    imag_path = tmp_path / "imag_2.ome.tiff"
    OmeTiffWriter.save(real, str(real_path), dim_order="YX")
    OmeTiffWriter.save(imag, str(imag_path), dim_order="YX")

    fig, ax = plt.subplots()
    ax_uri = "obj://session/env/ax2"
    OBJECT_CACHE[ax_uri] = ax

    # Initial children count (usually just spines, ticks, etc.)
    initial_children = len(ax.get_children())

    adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[
            ("real", create_mock_artifact("real", real_path)),
            ("imag", create_mock_artifact("imag", imag_path)),
        ],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax2"}},
        work_dir=tmp_path,
    )

    # After plotting, there should be more children (the phasor plot)
    assert len(ax.get_children()) > initial_children, "No new artists added to the provided axes."
    plt.close(fig)


@pytest.mark.slow
@pytest.mark.integration
def test_subplots_plot_phasor_savefig_workflow(adapter, tmp_path):
    """End-to-end: subplots → plot_phasor(ax=...) → savefig has content.

    This simulates the full MCP workflow.
    """
    # 1. Mock subplots output
    fig, ax = plt.subplots()
    fig_uri = "obj://session/env/fig1"
    ax_uri = "obj://session/env/ax1"
    OBJECT_CACHE[fig_uri] = fig
    OBJECT_CACHE[ax_uri] = ax

    # 2. Mock phasor data
    real = np.random.rand(32, 32).astype(np.float32)
    imag = np.random.rand(32, 32).astype(np.float32)
    from bioio.writers import OmeTiffWriter

    real_path = tmp_path / "real_3.ome.tiff"
    imag_path = tmp_path / "imag_3.ome.tiff"
    OmeTiffWriter.save(real, str(real_path), dim_order="YX")
    OmeTiffWriter.save(imag, str(imag_path), dim_order="YX")

    # 3. Call plot_phasor with ax
    adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[
            ("real", create_mock_artifact("real", real_path)),
            ("imag", create_mock_artifact("imag", imag_path)),
        ],
        params={"ax": {"type": "AxesRef", "uri": ax_uri, "ref_id": "ax1"}},
        work_dir=tmp_path,
    )

    # 4. Save figure (using matplotlib_ops logic)
    # We can just use the adapter to execute a mock 'savefig' if it was registered,
    # but here we'll just save it directly to verify content.
    plot_path = tmp_path / "final_plot.png"
    fig.savefig(str(plot_path))
    plt.close(fig)

    # 5. Verify image content
    assert plot_path.exists()

    from PIL import Image

    img = Image.open(plot_path).convert("L")
    data = np.array(img)

    # A blank matplotlib figure (Agg backend) is usually all white (255)
    # If something was plotted, variance should be > 0
    assert np.var(data) > 0.1, (
        "Saved image appears to be blank (white). The plot was likely drawn on a different axes."
    )
