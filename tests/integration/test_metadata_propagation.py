from pathlib import Path

import numpy as np
import pytest
import tifffile

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.mark.integration
def test_skimage_metadata_propagation(tmp_path: Path):
    """Verify that dynamic skimage functions propagate OME metadata (axes, shape)."""
    # Setup
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    input_path = tmp_path / "input.ome.tif"

    # Create OME-TIFF with axes metadata
    data = np.random.rand(10, 100, 100).astype(np.float32)  # CYX
    tifffile.imwrite(input_path, data, metadata={"axes": "CYX"})

    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path, artifacts_root],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    execution = ExecutionService(config, artifact_store=artifact_store)

    workflow = {
        "steps": [
            {
                "fn_id": "base.skimage.filters.gaussian",
                "inputs": {
                    "image": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": f"file://{input_path.absolute()}",
                        "metadata": {"axes": "CYX", "shape": [10, 100, 100]},
                    }
                },
                "params": {"sigma": 1.0},
            }
        ]
    }

    result = execution.run_workflow(workflow)
    assert result["status"] == "success"

    status = execution.get_run_status(result["run_id"])
    # The output name in dynamic adapter is usually 'output' or 'result'
    # SkimageAdapter currently returns 'output'
    output_ref = status["outputs"].get("output") or status["outputs"].get("result")
    assert output_ref is not None, (
        f"Workflow outputs should contain 'output' or 'result', got {status['outputs'].keys()}"
    )

    # Assert metadata propagation
    assert "metadata" in output_ref, "Output artifact should have metadata"
    assert output_ref["metadata"].get("axes") == "CYX", (
        f"Axes should be native dims, got {output_ref['metadata'].get('axes')}"
    )
    assert output_ref["metadata"].get("shape") == [10, 100, 100], "Shape should be native dims"
