from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest
import tifffile

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect

FLUTE_DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "FLUTE_FLIM_data_tif"


def _path_to_uri(path: Path) -> str:
    return f"file://{quote(str(path.absolute()), safe='/:')}"


def _uri_to_path(uri: str) -> Path:
    if uri.startswith("file://"):
        path_str = uri[7:]
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]
        return Path(path_str)
    return Path(uri)


def _env_available(env_name: str) -> bool:
    try:
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


@pytest.mark.integration
def test_flim_phasor_e2e(tmp_path: Path) -> None:
    if not _env_available("bioimage-mcp-base") or not _env_available("bioimage-mcp-cellpose"):
        pytest.skip(
            "Required tool environments missing: bioimage-mcp-base or bioimage-mcp-cellpose"
        )

    if not FLUTE_DATASET_PATH.exists():
        pytest.skip(f"Dataset missing at {FLUTE_DATASET_PATH}")

    tiff_files = list(FLUTE_DATASET_PATH.glob("*.tif"))
    if not tiff_files:
        pytest.skip("No TIFF files found in dataset")

    preferred = FLUTE_DATASET_PATH / "Fluorescein_Embryo.tif"
    dataset_file = preferred if preferred.exists() else tiff_files[0]

    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[FLUTE_DATASET_PATH, tools_root, tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)

    execution = ExecutionService(config, artifact_store=artifact_store)

    workflow1 = {
        "steps": [
            {
                "fn_id": "base.wrapper.phasor.phasor_from_flim",
                "inputs": {
                    "dataset": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": _path_to_uri(dataset_file),
                    }
                },
                "params": {"time_axis": "Z"},
            }
        ]
    }
    run1 = execution.run_workflow(workflow1)
    status1 = execution.get_run_status(run1["run_id"])
    assert status1["status"] == "succeeded"

    outputs1 = status1["outputs"]
    for key in ("g_image", "s_image", "intensity_image"):
        out_ref = outputs1[key]
        out_path = _uri_to_path(out_ref["uri"])
        assert out_path.exists()

    intensity_ref = outputs1["intensity_image"]
    seg_input = intensity_ref
    axes = (intensity_ref.get("metadata") or {}).get("axes", "")
    shape = (intensity_ref.get("metadata") or {}).get("shape", [])

    if axes and "C" in axes:
        c_index = axes.index("C")
        if shape and shape[c_index] > 1:
            intensity_path = _uri_to_path(intensity_ref["uri"])
            data = tifffile.imread(str(intensity_path))
            slicer: list[slice | int] = [slice(None)] * data.ndim
            slicer[c_index] = 0
            single = data[tuple(slicer)]
            out_axes = axes.replace("C", "")
            out_path = tmp_path / "intensity_channel0.ome.tiff"
            tifffile.imwrite(
                str(out_path),
                single,
                compression="zlib",
                metadata={"axes": out_axes},
            )
            seg_input = {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "uri": _path_to_uri(out_path),
            }

    workflow2 = {
        "steps": [
            {
                "fn_id": "cellpose.segment",
                "inputs": {"image": seg_input},
                "params": {"model_type": "cyto3", "diameter": 30.0},
            }
        ]
    }
    run2 = execution.run_workflow(workflow2)
    status2 = execution.get_run_status(run2["run_id"])
    assert status2["status"] == "succeeded"
    assert status2["outputs"]["labels"]["type"] == "LabelImageRef"

    mask_path = _uri_to_path(status2["outputs"]["labels"]["uri"])
    assert mask_path.exists()
