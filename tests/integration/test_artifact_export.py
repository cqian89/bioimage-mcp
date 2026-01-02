from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_export_enforces_write_allowlist(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    allowed_write_root = tmp_path / "allowed_write"
    denied_write_root = tmp_path / "denied_write"
    allowed_write_root.mkdir()
    denied_write_root.mkdir()

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[allowed_write_root],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    src = tmp_path / "in.txt"
    src.write_text("hello")
    ref = store.import_file(src, artifact_type="LogRef", format="text")

    with pytest.raises(PermissionError):
        store.export(ref.ref_id, denied_write_root / "out.txt")

    exported = store.export(ref.ref_id, allowed_write_root / "out.txt")
    assert exported.exists()
    assert exported.read_text() == "hello"


@pytest.mark.integration
def test_base_bioio_export_materializes_mem_to_file(mcp_services):
    """T020: base.bioio.export materializes mem:// to file-backed artifact."""
    execution_service = mcp_services["execution"]
    tmp_path = mcp_services["tmp_path"]

    # 1. Create a memory artifact
    # First create a file to import
    import numpy as np
    from bioio import BioImage
    from bioio.writers import OmeTiffWriter

    shape = (1, 1, 1, 64, 64)
    data = np.random.rand(*shape).astype(np.float32)
    image_path = tmp_path / "input.ome.tiff"
    OmeTiffWriter.save(data, str(image_path), dim_order="TCZYX")

    ref = execution_service.artifact_store.import_file(
        image_path, artifact_type="BioImageRef", format="OME-TIFF"
    )

    # Use base.xarray.rename to produce a memory artifact
    workflow = {
        "steps": [
            {
                "fn_id": "base.xarray.rename",
                "params": {"mapping": {"Z": "T", "T": "Z"}},
                "inputs": {"image": {"ref_id": ref.ref_id}},
            }
        ],
        "run_opts": {"output_mode": "memory"},
    }

    result = execution_service.run_workflow(workflow)
    assert result["status"] == "succeeded", f"Workflow failed: {result.get('error')}"

    run_id = result["run_id"]
    status = execution_service.get_run_status(run_id)
    mem_ref = status["outputs"]["output"]

    assert mem_ref["uri"].startswith("mem://"), f"Expected mem:// URI, got {mem_ref['uri']}"
    assert mem_ref["storage_type"] == "memory"

    # 2. Call base.bioio.export to materialize it
    export_workflow = {
        "steps": [
            {
                "fn_id": "base.bioio.export",
                "params": {"format": "OME-TIFF"},
                "inputs": {"image": {"ref_id": mem_ref["ref_id"]}},
            }
        ],
        "run_opts": {"output_mode": "file"},
    }

    export_result = execution_service.run_workflow(export_workflow)
    assert export_result["status"] == "succeeded", f"Export failed: {export_result.get('error')}"

    export_run_id = export_result["run_id"]
    export_status = execution_service.get_run_status(export_run_id)
    file_ref = export_status["outputs"]["output"]

    # 3. Verify it is a file:// artifact
    assert file_ref["uri"].startswith("file://")
    assert file_ref["storage_type"] == "file"
    assert file_ref["format"] == "OME-TIFF"

    # 4. Verify file exists and is valid OME-TIFF
    # Use ArtifactStore.export to get a path with extension for BioImage validation
    verify_path = tmp_path / "verify_export.ome.tiff"
    execution_service.artifact_store.export(file_ref["ref_id"], verify_path)
    assert verify_path.exists()

    img = BioImage(str(verify_path))
    assert img.dims.shape == shape
    # Use np.allclose as small differences can occur during save/load
    data_out = img.data
    if hasattr(data_out, "compute"):
        data_out = data_out.compute()
    assert np.allclose(data_out, data)

    # 5. Verify provenance
    # The run should record that it used a source artifact as input
    # Note: when exporting a mem:// artifact, it may be materialized to an intermediate file
    # so we just verify that provenance is tracked.
    assert "source_ref_id" in export_status["outputs"]["output"].get("metadata", {})
