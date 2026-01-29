"""
Integration test for R3: Align imshow output type to AxesImageRef.
"""

from pathlib import Path

import numpy as np
import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def execution_service(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

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


@pytest.mark.integration
def test_imshow_returns_axes_image_ref(execution_service):
    """Verify that imshow() returns an AxesImageRef with proper metadata."""

    # Step 1: Create subplots
    result1 = execution_service.run_workflow(
        {"steps": [{"id": "base.matplotlib.pyplot.subplots", "params": {"nrows": 1, "ncols": 1}}]}
    )
    assert result1["status"] == "success"
    outputs1 = execution_service.get_run_status(result1["run_id"])["outputs"]
    ax_ref = outputs1["axes"]
    ax_ref_id = ax_ref["ref_id"]

    # Step 2: Run imshow
    data = np.random.rand(10, 10).tolist()
    result2 = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.imshow",
                    "inputs": {"axes": ax_ref},
                    "params": {
                        "X": data,
                        "cmap": "magma",
                        "vmin": 0.0,
                        "vmax": 1.0,
                        "origin": "lower",
                        "interpolation": "nearest",
                    },
                }
            ]
        }
    )
    assert result2["status"] == "success", f"imshow failed: {result2.get('error')}"

    outputs2 = execution_service.get_run_status(result2["run_id"])["outputs"]
    # The output name in matplotlib_ops.py is now "axes_image"
    img_ref = outputs2.get("axes_image") or outputs2.get("return")

    assert img_ref is not None
    assert img_ref["type"] == "AxesImageRef"
    assert img_ref["python_class"] == "matplotlib.image.AxesImage"

    metadata = img_ref["metadata"]
    assert metadata["parent_axes_ref_id"] == ax_ref_id
    assert metadata["cmap"] == "magma"
    assert metadata["vmin"] == 0.0
    assert metadata["vmax"] == 1.0
    assert metadata["origin"] == "lower"
    assert metadata["interpolation"] == "nearest"


@pytest.mark.integration
def test_imshow_with_gca_ref_id(execution_service):
    """Verify that imshow() works with axes from gca() and finds the ref_id."""

    # Step 1: Create figure (gca() will work on this)
    execution_service.run_workflow(
        {"steps": [{"id": "base.matplotlib.pyplot.figure", "params": {}}]}
    )

    # Step 2: Get current axes
    result_gca = execution_service.run_workflow(
        {"steps": [{"id": "base.matplotlib.pyplot.gca", "params": {}}]}
    )
    assert result_gca["status"] == "success"
    outputs_gca = execution_service.get_run_status(result_gca["run_id"])["outputs"]
    ax_ref = outputs_gca["return"]  # gca returns "return" as ObjectRef
    ax_ref_id = ax_ref["ref_id"]

    # Step 3: Run imshow with this axes
    data = np.random.rand(5, 5).tolist()
    result_im = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.imshow",
                    "inputs": {"axes": ax_ref},
                    "params": {"X": data},
                }
            ]
        }
    )
    assert result_im["status"] == "success", f"imshow failed: {result_im.get('error')}"

    outputs_im = execution_service.get_run_status(result_im["run_id"])["outputs"]
    img_ref = outputs_im["axes_image"]

    assert img_ref["metadata"]["parent_axes_ref_id"] == ax_ref_id
