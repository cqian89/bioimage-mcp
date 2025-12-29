"""Integration test for legacy function redirects (T028)."""

import pytest
from pathlib import Path
import numpy as np
import tifffile
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.mark.integration
def test_legacy_redirect_denoise(tmp_path: Path):
    """Test redirection from legacy ID to new wrapper ID (T028)."""
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
    execution = ExecutionService(config, artifact_store=artifact_store)

    # Define workflow with legacy ID
    # This ID was renamed to base.wrapper.denoise.denoise_image in Phase 4
    legacy_fn_id = "base.bioimage_mcp_base.preprocess.denoise_image"
    workflow = {
        "steps": [
            {
                "fn_id": legacy_fn_id,
                "inputs": {
                    "image": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": f"file://{input_path.absolute()}",
                    }
                },
                "params": {
                    "filter_type": "gaussian",
                    "sigma": 1.0,
                },
            }
        ]
    }

    # Run workflow - should succeed via redirect (SC-001)
    # Validation should pass because IDs are redirected before validation.
    result = execution.run_workflow(workflow)

    if result["status"] != "succeeded":
        pytest.fail(f"Legacy redirect failed: {result.get('error')}")

    # Get status and check log for deprecation warning
    status = execution.get_run_status(result["run_id"])
    assert status["status"] == "succeeded"

    # Assert log contains deprecation warning (T030)
    # The warning should mention the NEW ID: base.wrapper.denoise.denoise_image
    log_content = ""
    if "log_ref" in status:
        log_ref = status["log_ref"]
        log_path = Path(log_ref["uri"].replace("file://", ""))
        log_content = log_path.read_text()

    assert "DEPRECATED" in log_content
    assert "base.wrapper.denoise.denoise_image" in log_content
