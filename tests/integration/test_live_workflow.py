from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import connect

FLUTE_DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "FLUTE_FLIM_data_tif"


def _path_to_uri(path: Path) -> str:
    return f"file://{quote(str(path.absolute()), safe='/:')}"


def _env_available(env_name: str) -> bool:
    try:
        import subprocess

        proc = subprocess.run(
            ["conda", "run", "-n", env_name, "python", "-c", "print('ok')"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _manifest_tool_version(tool_id: str) -> str:
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, _ = load_manifests([tools_root])
    for manifest in manifests:
        if manifest.tool_id == tool_id:
            return manifest.tool_version
    return "unknown"


@pytest.mark.integration
def test_live_workflow_project_sum_cellpose(tmp_path: Path) -> None:
    if not _env_available("bioimage-mcp-base") or not _env_available("bioimage-mcp-cellpose"):
        pytest.skip(
            "Required tool environments missing: bioimage-mcp-base or bioimage-mcp-cellpose"
        )

    dataset = FLUTE_DATASET_PATH
    if not dataset.exists():
        pytest.skip(f"Dataset missing at {dataset}")

    tiff_files = list(dataset.glob("*.tif"))
    if not tiff_files:
        pytest.skip("No TIFF files found in dataset")

    image_file = next((f for f in tiff_files if "ZOOM" in f.name), tiff_files[0])

    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[dataset, tools_root, tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    execution = ExecutionService(config, artifact_store=artifact_store)

    workflow1 = {
        "steps": [
            {
                "id": "base.xarray.sum",
                "inputs": {
                    "image": {
                        "type": "BioImageRef",
                        "format": "TIFF",
                        "uri": _path_to_uri(image_file),
                    }
                },
                "params": {"dim": "Z"},
            }
        ]
    }
    run1 = execution.run_workflow(workflow1)
    assert run1["status"] in {"success", "running", "queued"}

    status1 = execution.get_run_status(run1["run_id"])
    assert status1["status"] == "success"
    output_ref = status1["outputs"]["output"]

    # Convert OME-Zarr to OME-TIFF for cellpose compatibility
    workflow1b = {
        "steps": [
            {
                "id": "base.io.bioimage.export",
                "inputs": {"image": output_ref},
                "params": {"format": "OME-TIFF"},
            }
        ]
    }
    run1b = execution.run_workflow(workflow1b)
    assert run1b["status"] in {"success", "running", "queued"}
    status1b = execution.get_run_status(run1b["run_id"])
    assert status1b["status"] == "success"
    tiff_output_ref = status1b["outputs"]["output"]

    workflow2 = {
        "steps": [
            {
                "id": "cellpose.models.CellposeModel.eval",
                "inputs": {"x": tiff_output_ref},
                "params": {"model_type": "cyto3", "diameter": 30.0},
            }
        ]
    }
    run2 = execution.run_workflow(workflow2)
    assert run2["status"] in {"success", "running", "queued"}
    status2 = execution.get_run_status(run2["run_id"])
    assert status2["status"] == "success"
    assert status2["outputs"]["labels"]["type"] == "LabelImageRef"

    # Provenance includes tool manifests for the current workflow run
    run_record = status2["outputs"]["workflow_record"]
    record = artifact_store.parse_native_output(run_record["ref_id"])
    tool_manifests = record.get("tool_manifests", [])
    versions = {tm.get("tool_id"): tm.get("tool_version") for tm in tool_manifests}
    # Note: Only the tools used in this specific run (cellpose.models.CellposeModel.eval) are recorded
    assert versions.get("tools.cellpose") == _manifest_tool_version("tools.cellpose")

    # Output isolation: separate run ids
    assert run1["run_id"] != run2["run_id"]
