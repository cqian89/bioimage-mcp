import pytest
import numpy as np
import tifffile
from pathlib import Path
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.mark.integration
def test_new_wrapper_execution_denoise(tmp_path: Path):
    """Test execution of new base.wrapper.denoise.denoise_image."""
    # Setup directories
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    # Create input image (OME-TIFF as required by denoise_image)
    input_path = tmp_path / "input.ome.tiff"
    data = np.random.rand(1, 1, 1, 100, 100).astype(np.float32)
    tifffile.imwrite(input_path, data, metadata={"axes": "TCZYX"})

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
    execution = ExecutionService(config, artifact_store=artifact_store)

    # Define workflow
    workflow = {
        "steps": [
            {
                "fn_id": "base.wrapper.denoise.denoise_image",
                "inputs": {
                    "image": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": f"file://{input_path.absolute()}",
                        "metadata": {"axes": "TCZYX"},
                    }
                },
                "params": {
                    "filter_type": "gaussian",
                    "sigma": 1.0,
                },
            }
        ]
    }

    # Run workflow
    result = execution.run_workflow(workflow)

    # Check status
    status = execution.get_run_status(result["run_id"])
    if status["status"] != "succeeded":
        print(f"Workflow failed: {status.get('error')}")
        if "log" in status:
            print(f"Log: {status['log']}")

    assert status["status"] == "succeeded"
    assert "output" in status["outputs"]
    print(f"Outputs: {status['outputs']}")
    out_ref = status["outputs"]["output"]
    output_uri = out_ref.get("uri") or out_ref.get("path")
    assert output_uri is not None
    if output_uri.startswith("file://"):
        output_path = Path(output_uri[7:])
    else:
        output_path = Path(output_uri)
    assert output_path.exists()
