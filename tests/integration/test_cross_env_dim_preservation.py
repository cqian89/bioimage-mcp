from pathlib import Path

import numpy as np
import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config
from tests.integration.mcp_test_client import MCPTestClient


@pytest.mark.integration
def test_cross_env_dim_preservation(tmp_path):
    import logging

    logging.getLogger().setLevel(logging.DEBUG)
    # This test verifies that dimension metadata is preserved across tool boundaries
    # and that adapters correctly expand/squeeze based on manifest requirements.

    # Setup config
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[Path("/mnt/c/Users/meqia/bioimage-mcp/tools")],
        fs_allowlist_read=[str(tmp_path), "/mnt/c/Users/meqia/bioimage-mcp/datasets"],
        fs_allowlist_write=[str(tmp_path)],
    )

    discovery = DiscoveryService(config)
    execution = ExecutionService(config)
    client = MCPTestClient(discovery=discovery, execution=execution)

    # 1. Create a 5D OME-TIFF
    from bioio.writers import OmeTiffWriter

    img_path = tmp_path / "test_5d.ome.tiff"
    data_5d = np.random.randint(0, 255, (1, 1, 1, 128, 128), dtype=np.uint8)
    OmeTiffWriter.save(data_5d, str(img_path), dim_order="TCZYX")

    store = execution.artifact_store
    input_ref = store.import_file(img_path, artifact_type="BioImageRef", format="OME-TIFF")

    # 2. Run base.xarray.DataArray.squeeze to get a 2D memory artifact
    # Note: base.xarray.DataArray.squeeze returns a memory artifact
    client.activate_functions(["base.xarray.DataArray.squeeze", "base.skimage.filters.gaussian"])

    res1 = client.call_tool(
        "base.xarray.DataArray.squeeze", inputs={"image": {"ref_id": input_ref.ref_id}}, params={}
    )
    if res1["status"] != "success":
        log_id = res1.get("log_ref_id")
        if log_id:
            log_content = store.get_raw_content(log_id).decode()
            print(f"DEBUG: res1 log: {log_content}")
        print(f"DEBUG: res1 failed: {res1}")
    assert res1["status"] == "success"
    squeezed_ref_id = res1["outputs"]["output"]["ref_id"]
    squeezed_ref = store.get(squeezed_ref_id)

    # Verify it is 2D
    assert squeezed_ref.ndim == 2

    # 3. Run base.skimage.filters.gaussian on the 2D memory artifact
    # The SkimageAdapter should see that gaussian (if configured with requirements)
    # handles 2D or 3D.
    res2 = client.call_tool(
        "base.skimage.filters.gaussian",
        inputs={"image": {"ref_id": squeezed_ref_id}},
        params={"sigma": 1.0},
    )

    assert res2["status"] == "success"

    output_ref_id = res2["outputs"]["output"]["ref_id"]
    output_ref = store.get(output_ref_id)
    print(f"DEBUG: output_ref metadata: {output_ref.metadata}")
    print(f"DEBUG: output_ref ndim={output_ref.ndim}, dims={output_ref.dims}")

    # Verify dimensions are preserved (should still be 2D if the tool didn't expand it)
    assert output_ref.ndim == 2
    assert output_ref.dims == ["Y", "X"]
