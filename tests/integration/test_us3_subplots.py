"""
Integration tests for User Story 3: Multi-panel comparison figures.
"""

import numpy as np
from pathlib import Path
import pytest
import tifffile

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def execution_service(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    # Use real tools directory
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[str(tmp_path), str(tools_root)],
        fs_allowlist_write=[str(tmp_path), str(artifacts_root)],
        fs_denylist=[],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    service = ExecutionService(config, artifact_store=artifact_store)
    yield service
    service.close()


@pytest.mark.integration
def test_1x2_subplots_workflow(execution_service, tmp_path):
    """T019: Test creating a 1x2 grid layout and displaying different images."""

    # Create dummy images
    img1_path = tmp_path / "img1.tif"
    img2_path = tmp_path / "img2.tif"
    tifffile.imwrite(img1_path, np.random.rand(10, 10).astype(np.float32))
    tifffile.imwrite(img2_path, np.random.rand(10, 10).astype(np.float32))

    # Step 1: subplots(nrows=1, ncols=2)
    workflow_fig = {
        "steps": [
            {
                "fn_id": "base.matplotlib.pyplot.subplots",
                "params": {"nrows": 1, "ncols": 2, "figsize": [10, 5]},
            }
        ]
    }
    result_fig = execution_service.run_workflow(workflow_fig)
    assert result_fig["status"] == "success"
    outputs_fig = execution_service.get_run_status(result_fig["run_id"])["outputs"]

    assert "figure" in outputs_fig
    assert "axes_0" in outputs_fig
    assert "axes_1" in outputs_fig

    fig_ref = outputs_fig["figure"]
    ax0_ref = outputs_fig["axes_0"]
    ax1_ref = outputs_fig["axes_1"]

    assert fig_ref["type"] == "FigureRef"
    assert ax0_ref["type"] == "AxesRef"
    assert ax1_ref["type"] == "AxesRef"

    # Step 2: imshow on ax0
    workflow_imshow0 = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.imshow",
                "inputs": {"axes": ax0_ref, "X": {"type": "BioImageRef", "path": str(img1_path)}},
                "params": {"cmap": "gray"},
            }
        ]
    }
    result_imshow0 = execution_service.run_workflow(workflow_imshow0)
    if result_imshow0["status"] != "success":
        print(f"DEBUG: imshow0 failed: {result_imshow0.get('error')}")
    assert result_imshow0["status"] == "success"

    # Step 3: imshow on ax1
    workflow_imshow1 = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.imshow",
                "inputs": {"axes": ax1_ref, "X": {"type": "BioImageRef", "path": str(img2_path)}},
                "params": {"cmap": "viridis"},
            }
        ]
    }
    result_imshow1 = execution_service.run_workflow(workflow_imshow1)
    assert result_imshow1["status"] == "success"

    # Step 3.5: scatter on ax0 (overlay)
    workflow_scatter = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.scatter",
                "inputs": {"axes": ax0_ref},
                "params": {"x": [2, 5, 8], "y": [3, 6, 9], "c": "red", "s": 100},
            }
        ]
    }
    result_scatter = execution_service.run_workflow(workflow_scatter)
    assert result_scatter["status"] == "success"

    # Step 4: savefig
    workflow_save = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Figure.savefig",
                "inputs": {"figure": fig_ref},
                "params": {"format": "png"},
            }
        ]
    }
    result_save = execution_service.run_workflow(workflow_save)
    assert result_save["status"] == "success"

    status_save = execution_service.get_run_status(result_save["run_id"])
    plot_ref = status_save["outputs"]["plot"]
    assert plot_ref["type"] == "PlotRef"
    # PlotRef might not have 'path' field in model, use URI
    from urllib.parse import unquote, urlparse

    parsed = urlparse(plot_ref["uri"])
    plot_path = Path(unquote(parsed.path))
    if (
        plot_path.as_posix().startswith("/")
        and len(plot_path.parts) > 1
        and plot_path.parts[1].endswith(":")
    ):
        # Handle Windows path in URI
        plot_path = Path(*plot_path.parts[1:])

    assert plot_path.exists()
