from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pytest
import tifffile

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


def _path_to_uri(path: Path) -> str:
    return f"file://{quote(str(path.absolute()), safe='/:')}"


def _env_available(env_name: str, probe: str = "print('ok')") -> bool:
    try:
        proc = subprocess.run(
            ["conda", "run", "-n", env_name, "python", "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def test_phasor_workflow_record_contains_log_ref(tmp_path: Path) -> None:
    if not _env_available("bioimage-mcp-base", "import phasorpy; print('ok')"):
        pytest.skip("Required tool environment missing: bioimage-mcp-base with phasorpy")

    tiff_path = tmp_path / "flim.ome.tiff"
    data = np.arange(4 * 4 * 4, dtype="float32").reshape(4, 4, 4)
    tifffile.imwrite(
        str(tiff_path),
        data,
        compression="zlib",
        photometric="minisblack",
        metadata={"axes": "TYX"},
    )

    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)

    with ExecutionService(config, artifact_store=artifact_store) as svc:
        result = svc.run_workflow(
            {
                "steps": [
                    {
                        "fn_id": "base.phasor_from_flim",
                        "inputs": {
                            "dataset": {
                                "type": "BioImageRef",
                                "format": "OME-TIFF",
                                "uri": _path_to_uri(tiff_path),
                            }
                        },
                        "params": {},
                    }
                ]
            }
        )
        status = svc.get_run_status(result["run_id"])

    record_ref = status["outputs"]["workflow_record"]
    record = artifact_store.parse_native_output(record_ref["ref_id"])

    log_ref = record.get("log_ref")
    assert log_ref, "workflow record should include log_ref"
    assert log_ref["type"] == "LogRef"
    conn.close()
