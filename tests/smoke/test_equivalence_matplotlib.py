from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


@pytest.mark.smoke_extended
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_matplotlib_equivalence(live_server, helper, native_executor, tmp_path):
    """Test that MCP generates valid plot files equivalent to native matplotlib."""

    # 1. MCP Execution
    # Step 1: Create figure and axes
    subplots_result = await live_server.call_tool(
        "run",
        {"id": "base.matplotlib.pyplot.subplots", "inputs": {}, "params": {"figsize": [6, 4]}},
    )
    assert "outputs" in subplots_result, f"Expected 'outputs' in result, got {subplots_result}"
    fig_ref = subplots_result["outputs"]["figure"]
    axes_ref = subplots_result["outputs"]["axes"]

    # Step 2: Plot data
    x = np.linspace(0, 10, 100).tolist()
    y = np.sin(x).tolist()

    await live_server.call_tool(
        "run",
        {
            "id": "base.matplotlib.Axes.plot",
            "inputs": {"axes": axes_ref},
            "params": {"x": x, "y": y, "label": "Sine Wave"},
        },
    )

    # Step 3: Add title and legend (to match native baseline)
    await live_server.call_tool(
        "run",
        {
            "id": "base.matplotlib.Axes.set_title",
            "inputs": {"axes": axes_ref},
            "params": {"label": "Matplotlib Baseline"},
        },
    )
    await live_server.call_tool(
        "run",
        {
            "id": "base.matplotlib.Axes.legend",
            "inputs": {"axes": axes_ref},
            "params": {},
        },
    )

    # Step 4: Save figure
    # We omit 'fname' to avoid allowlist issues with tmp_path.
    # The MCP server will auto-generate a path in its artifacts directory.
    save_result = await live_server.call_tool(
        "run",
        {
            "id": "base.matplotlib.Figure.savefig",
            "inputs": {"figure": fig_ref},
            "params": {"dpi": 150},
        },
    )
    assert save_result["status"] == "success", f"savefig failed: {save_result}"

    plot_ref = save_result["outputs"]["plot"]
    assert "uri" in plot_ref, f"Missing URI in plot ref: {plot_ref}"

    # Resolve URI to local path
    uri = plot_ref["uri"]
    if uri.startswith("file://"):
        mcp_plot_path = Path(uri[7:])
    else:
        # If it's not a file URI, we might need a different way to access it,
        # but for smoke tests, it's usually file://
        pytest.fail(f"Expected file:// URI, got {uri}")

    assert mcp_plot_path.exists(), (
        f"MCP Plot file not found at {mcp_plot_path}. Result: {save_result}"
    )

    # 2. Native Execution
    baseline_script = Path("tests/smoke/reference_scripts/matplotlib_baseline.py")
    native_result = native_executor.run_script(
        "bioimage-mcp-base", baseline_script, [str(tmp_path.absolute())]
    )
    native_plot_path = Path(native_result["plot_path"])
    assert native_plot_path.exists(), f"Native Plot file not found at {native_plot_path}"

    # 3. Semantic Validation
    # Use helper.assert_plot_valid() on both
    # 6x4 inches at 150 dpi = 900x600 pixels
    # We allow a small tolerance as different backends might have slight pixel differences
    helper.assert_plot_valid(
        mcp_plot_path,
        expected_width=900,
        expected_height=600,
        dimension_tolerance=2,
        min_variance=10.0,
    )
    helper.assert_plot_valid(
        native_plot_path,
        expected_width=900,
        expected_height=600,
        dimension_tolerance=2,
        min_variance=10.0,
    )

    # 4. Equivalence Assertions
    # Compare file sizes (should be similar for similar plots)
    # PNG compression can vary, but for this simple plot it should be within 2x
    helper.assert_files_similar_size(mcp_plot_path, native_plot_path, max_ratio=2.0)
