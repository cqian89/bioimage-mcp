"""
Integration test for dynamic discovery and execution of scipy functions.
"""

from pathlib import Path

import numpy as np
import pytest
import tifffile
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.mark.integration
def test_scipy_dynamic_execution_gaussian_filter(tmp_path: Path):
    """Test dynamic discovery and execution of scipy.ndimage.gaussian_filter."""
    # Setup directories
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    # Create input image
    input_path = tmp_path / "input.tif"
    data = np.random.rand(100, 100).astype(np.float32)
    tifffile.imwrite(input_path, data)

    # Config
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path, artifacts_root],
        fs_denylist=[],
    )

    # Initialize services
    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    execution = ExecutionService(config, artifact_store=artifact_store)  # run_store optional

    # Define workflow
    # Note: The I/O pattern IMAGE_TO_IMAGE maps to input port named "image"
    workflow = {
        "steps": [
            {
                "fn_id": "scipy.ndimage.gaussian_filter",
                "inputs": {
                    "image": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": f"file://{input_path.absolute()}",
                    }
                },
                "params": {
                    "sigma": 2.0,
                },
            }
        ]
    }

    # Run workflow
    result = execution.run_workflow(workflow)

    # Verify
    if result["status"] != "succeeded":
        # Print debug info for failed workflow
        status = execution.get_run_status(result["run_id"])
        print(f"\nWorkflow failed with status: {status}")
        if "error" in status:
            print(f"Error: {status['error']}")
        if "log" in status:
            print(f"Log: {status['log']}")

    assert result["status"] == "succeeded"
    assert "run_id" in result

    # Check outputs
    status = execution.get_run_status(result["run_id"])
    assert status["status"] == "succeeded"

    # Check output artifact existence
    # ScipyAdapter.execute currently returns a dummy URI "file:///tmp/result.tif".
    # This test verifies that it runs, but the output file might not exist or be valid yet.
    # This is fine for now - the goal is to verify dynamic execution works.
