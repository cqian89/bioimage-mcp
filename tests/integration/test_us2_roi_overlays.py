"""
Integration tests for User Story 2: ROI Overlays on Microscopy Images.
"""

import os
from pathlib import Path

import numpy as np
import pytest
from bioio.writers import OmeTiffWriter

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
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path, artifacts_root],
        fs_denylist=[],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    service = ExecutionService(config, artifact_store=artifact_store)
    yield service
    service.close()


@pytest.fixture
def sample_image(tmp_path: Path):
    path = tmp_path / "test_image.tif"
    # Create a 100x100 image with a central square
    data = np.zeros((1, 1, 1, 100, 100), dtype=np.uint8)
    data[0, 0, 0, 40:60, 40:60] = 255
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")
    return {
        "type": "BioImageRef",
        "uri": path.as_uri(),
        "path": str(path),
        "format": "OME-TIFF",
    }


@pytest.mark.integration
def test_roi_overlay_workflow(execution_service, sample_image):
    """T015: Test full workflow: subplots → imshow → Circle → Rectangle → add_patch → savefig."""

    # Step 1: subplots
    res1 = execution_service.run_workflow(
        {"steps": [{"id": "base.matplotlib.pyplot.subplots", "params": {"figsize": [5, 5]}}]}
    )
    assert res1["status"] == "success"
    out1 = execution_service.get_run_status(res1["run_id"])["outputs"]
    fig_ref = out1["figure"]
    ax_ref = out1["axes"]

    # Step 2: imshow
    res2 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.imshow",
                    "inputs": {"axes": ax_ref},
                    "params": {"X": sample_image, "cmap": "gray", "origin": "upper"},
                }
            ]
        }
    )
    assert res2["status"] == "success"

    # Step 3: Create Circle
    res3 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.patches.Circle",
                    "params": {"xy": [50, 50], "radius": 10, "color": "red", "fill": False},
                }
            ]
        }
    )
    assert res3["status"] == "success"
    out3 = execution_service.get_run_status(res3["run_id"])["outputs"]
    circle_ref = out3.get("output") or out3.get("return")
    assert circle_ref is not None

    # Step 4: Create Rectangle
    res4 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.patches.Rectangle",
                    "params": {
                        "xy": [30, 30],
                        "width": 40,
                        "height": 40,
                        "color": "blue",
                        "fill": False,
                    },
                }
            ]
        }
    )
    assert res4["status"] == "success"
    out4 = execution_service.get_run_status(res4["run_id"])["outputs"]
    rect_ref = out4.get("output") or out4.get("return")
    assert rect_ref is not None

    # Step 5: add_patch (Circle)
    res5 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.add_patch",
                    "inputs": {"axes": ax_ref},
                    "params": {"p": circle_ref},
                }
            ]
        }
    )
    assert res5["status"] == "success"

    # Step 6: add_patch (Rectangle)
    res6 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.add_patch",
                    "inputs": {"axes": ax_ref},
                    "params": {"p": rect_ref},
                }
            ]
        }
    )
    assert res6["status"] == "success"

    # Step 7: savefig
    res7 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Figure.savefig",
                    "inputs": {"figure": fig_ref},
                    "params": {"format": "png"},
                }
            ]
        }
    )
    assert res7["status"] == "success"
    out7 = execution_service.get_run_status(res7["run_id"])["outputs"]
    assert "plot" in out7
    plot_uri = out7["plot"]["uri"]
    assert plot_uri.startswith("file://")
    # Verify file exists (extract path from file:// URI)
    import urllib.parse

    plot_path = urllib.parse.unquote(urllib.parse.urlparse(plot_uri).path)
    if plot_path.startswith("/") and os.name == "nt" and plot_path[2] == ":":
        plot_path = plot_path[1:]
    assert Path(plot_path).exists()


@pytest.mark.integration
def test_roi_clipping_and_origin(execution_service, sample_image):
    """T015: Test out-of-bounds clipping (FR-018) and coordinate conventions (FR-020)."""

    # Step 1: subplots
    res1 = execution_service.run_workflow({"steps": [{"id": "base.matplotlib.pyplot.subplots"}]})
    out1 = execution_service.get_run_status(res1["run_id"])["outputs"]
    fig_ref = out1["figure"]
    ax_ref = out1["axes"]

    # Step 2: imshow with top-left origin (default)
    res2 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.imshow",
                    "inputs": {"axes": ax_ref},
                    "params": {"X": sample_image},
                }
            ]
        }
    )
    assert res2["status"] == "success"

    # Step 3: Create Circle
    res3a = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.patches.Circle",
                    "params": {"xy": [150, 150], "radius": 20, "color": "yellow"},
                }
            ]
        }
    )
    assert res3a["status"] == "success"
    out3a = execution_service.get_run_status(res3a["run_id"])["outputs"]
    circle_ref = out3a.get("output") or out3a.get("return")

    # Step 3b: add_patch
    res3b = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.add_patch",
                    "inputs": {"axes": ax_ref},
                    "params": {"p": circle_ref},
                }
            ]
        }
    )
    assert res3b["status"] == "success"

    # Step 4: savefig
    res4 = execution_service.run_workflow(
        {"steps": [{"id": "base.matplotlib.Figure.savefig", "inputs": {"figure": fig_ref}}]}
    )
    assert res4["status"] == "success"
