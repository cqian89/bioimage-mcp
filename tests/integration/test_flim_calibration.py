"""Integration test for FLIM calibration workflow using PhasorPy (T013a).

Tests end-to-end FLIM calibration workflow:
1. Discovery: Verify phasorpy.phasor.phasor_from_signal and phasor_transform are discoverable
2. Execution: Load reference/sample FLIM datasets, compute phasors, apply calibration

This test is expected to FAIL until the base tool entrypoint is updated to support
dynamic function dispatch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect

FLUTE_DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "FLUTE_FLIM_data_tif"


def _path_to_uri(path: Path) -> str:
    """Convert a file path to a file:// URI."""
    return f"file://{quote(str(path.absolute()), safe='/:')}"


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a Path."""
    if uri.startswith("file://"):
        path_str = uri[7:]
        # Handle Windows absolute paths like /C:/...
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]
        return Path(path_str)
    return Path(uri)


def _env_available(env_name: str) -> bool:
    """Check if a conda environment is available."""
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
@pytest.mark.xfail(reason="entrypoint.py does not yet support dynamic dispatch")
def test_flim_calibration_workflow(tmp_path: Path) -> None:
    """Test FLIM calibration workflow using reference and sample datasets.

    Workflow:
    1. Load reference dataset (Fluorescein_Embryo.tif)
    2. Compute phasor from reference using phasorpy.phasor.phasor_from_signal
    3. Load sample dataset (Embryo.tif)
    4. Compute phasor from sample using phasorpy.phasor.phasor_from_signal
    5. Apply calibration using phasorpy.phasor.phasor_transform

    Expected to FAIL: entrypoint.py does not yet support dynamic dispatch.
    """
    # Check prerequisites
    if not _env_available("bioimage-mcp-base"):
        pytest.skip("Required tool environment missing: bioimage-mcp-base")

    if not FLUTE_DATASET_PATH.exists():
        pytest.skip(f"Dataset missing at {FLUTE_DATASET_PATH}")

    reference_file = FLUTE_DATASET_PATH / "Fluorescein_Embryo.tif"
    sample_file = FLUTE_DATASET_PATH / "Embryo.tif"

    if not reference_file.exists() or not sample_file.exists():
        pytest.skip(f"Required FLIM dataset files not found: {reference_file}, {sample_file}")

    # Setup test configuration
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

    # Step 1: Compute phasor from reference dataset
    workflow_reference = {
        "steps": [
            {
                "id": "phasorpy.phasor.phasor_from_signal",
                "inputs": {
                    "signal": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": _path_to_uri(reference_file),
                    }
                },
                "params": {
                    "axis": -1,  # Time axis (last dimension for FLIM data)
                    "harmonic": 1,  # First harmonic
                },
            }
        ]
    }

    run_ref = execution.run_workflow(workflow_reference)
    status_ref = execution.get_run_status(run_ref["run_id"])

    # Assert reference phasor computation success
    assert status_ref["status"] == "success", (
        f"Reference phasor failed: {status_ref.get('error', 'unknown')}"
    )

    # Verify outputs (real, imag, dc from phasor_from_signal)
    outputs_ref = status_ref["outputs"]
    assert "real" in outputs_ref, "Missing 'real' output from phasor_from_signal"
    assert "imag" in outputs_ref, "Missing 'imag' output from phasor_from_signal"

    # Extract reference phasor coordinates
    real_ref_uri = outputs_ref["real"]["uri"]
    imag_ref_uri = outputs_ref["imag"]["uri"]

    real_ref_path = _uri_to_path(real_ref_uri)
    imag_ref_path = _uri_to_path(imag_ref_uri)

    assert real_ref_path.exists(), f"Reference real phasor file missing: {real_ref_path}"
    assert imag_ref_path.exists(), f"Reference imag phasor file missing: {imag_ref_path}"

    # Step 2: Compute phasor from sample dataset
    workflow_sample = {
        "steps": [
            {
                "id": "phasorpy.phasor.phasor_from_signal",
                "inputs": {
                    "signal": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": _path_to_uri(sample_file),
                    }
                },
                "params": {
                    "axis": -1,
                    "harmonic": 1,
                },
            }
        ]
    }

    run_sample = execution.run_workflow(workflow_sample)
    status_sample = execution.get_run_status(run_sample["run_id"])

    assert status_sample["status"] == "success", (
        f"Sample phasor failed: {status_sample.get('error', 'unknown')}"
    )

    outputs_sample = status_sample["outputs"]
    assert "real" in outputs_sample
    assert "imag" in outputs_sample

    real_sample_uri = outputs_sample["real"]["uri"]
    imag_sample_uri = outputs_sample["imag"]["uri"]

    # Step 3: Apply phasor calibration/transformation
    # Using phasorpy.phasor.phasor_transform to calibrate sample phasor with reference
    workflow_calibration = {
        "steps": [
            {
                "id": "phasorpy.phasor.phasor_transform",
                "inputs": {
                    "real": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": real_sample_uri,
                    },
                    "imag": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": imag_sample_uri,
                    },
                    "real_zero": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": real_ref_uri,
                    },
                    "imag_zero": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "uri": imag_ref_uri,
                    },
                },
                "params": {},
            }
        ]
    }

    run_calibration = execution.run_workflow(workflow_calibration)
    status_calibration = execution.get_run_status(run_calibration["run_id"])

    assert status_calibration["status"] == "success", (
        f"Calibration failed: {status_calibration.get('error', 'unknown')}"
    )

    # Verify calibrated outputs
    outputs_calibrated = status_calibration["outputs"]
    assert "real" in outputs_calibrated, "Missing calibrated 'real' output"
    assert "imag" in outputs_calibrated, "Missing calibrated 'imag' output"

    calibrated_real_path = _uri_to_path(outputs_calibrated["real"]["uri"])
    calibrated_imag_path = _uri_to_path(outputs_calibrated["imag"]["uri"])

    assert calibrated_real_path.exists(), f"Calibrated real phasor missing: {calibrated_real_path}"
    assert calibrated_imag_path.exists(), f"Calibrated imag phasor missing: {calibrated_imag_path}"


@pytest.mark.integration
def test_phasorpy_functions_discoverable(tmp_path: Path) -> None:
    """Test that phasorpy functions are discoverable via dynamic sources.

    Expected to FAIL until discovery service supports dynamic_sources.
    """
    # This test will be added in a later task when discovery is implemented
    pytest.skip("Discovery of dynamic functions not yet implemented")
