from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for direct script execution/testing
REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

FIXTURE_CZI = REPO_ROOT / "datasets" / "sample_czi" / "Plate1-Blue-A-02-Scene-1-P2-E1-01.czi"


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
@pytest.mark.integration
def test_czi_import_converts_to_ome_tiff_raw():
    """T015: CZI ingest converts to OME-TIFF artifact (direct library call)."""
    try:
        from bioio import BioImage
        from bioio.writers import OmeTiffWriter
    except ImportError:
        pytest.skip("bioio or bioio-ome-tiff not installed")

    # Load CZI file
    try:
        img = BioImage(FIXTURE_CZI)
        data = img.data
    except Exception as e:
        pytest.skip(f"Could not load CZI (missing bioio-bioformats?): {e}")

    # Export to OME-TIFF
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.ome.tiff"
        OmeTiffWriter.save(
            data,
            output_path,
            dim_order=img.dims.order,
            physical_pixel_sizes=img.physical_pixel_sizes,
            channel_names=img.channel_names,
        )

        # Verify the output exists and is readable
        assert output_path.exists()

        # Re-load and verify dimensions preserved
        out_img = BioImage(output_path)
        assert out_img.dims.order == "TCZYX"
        assert out_img.data.shape == data.shape


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
@pytest.mark.integration
def test_czi_import_workflow(tmp_path: Path, monkeypatch) -> None:
    """T015: CZI ingest via bioimage-mcp workflow functions."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[REPO_ROOT / "tools" / "base"],
        fs_allowlist_read=[REPO_ROOT],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    # Mock environment manager to use current python executable
    # This ensures tools run in the same environment as the test
    monkeypatch.setattr("bioimage_mcp.runtimes.executor.detect_env_manager", lambda: None)

    with ExecutionService(config) as svc:
        workflow = {
            "steps": [
                {
                    "id": "base.io.bioimage.export",
                    "inputs": {
                        "image": {
                            "type": "BioImageRef",
                            "format": "CZI",
                            "uri": FIXTURE_CZI.as_uri(),
                        }
                    },
                    "params": {"format": "OME-TIFF"},
                }
            ]
        }

        result = svc.run_workflow(workflow, skip_validation=True)

        # If it failed due to missing dependencies, skip rather than fail
        if result["status"] == "failed":
            error = result.get("error", {})
            error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            if "Missing dependencies" in error_msg or "not available" in error_msg:
                pytest.skip(f"Workflow failed due to missing dependencies: {error_msg}")
            assert result["status"] == "success", f"Workflow failed: {error_msg}"

        assert result["status"] == "success"

        # Verify output
        status = svc.get_run_status(result["run_id"])
        outputs = status.get("outputs", {})
        assert "output" in outputs
        output_ref = outputs["output"]
        assert output_ref["format"] == "OME-TIFF"

        # The uri in output_ref is what we want
        uri = output_ref["uri"]
        path_str = uri[7:] if uri.startswith("file://") else uri
        # Handle potential leading slash on Windows
        if sys.platform == "win32" and path_str.startswith("/") and path_str[2:3] == ":":
            path_str = path_str[1:]
        path = Path(path_str)
        assert path.exists()

        # Verify content
        try:
            from bioio import BioImage
            from bioio_ome_tiff import Reader as OmeTiffReader

            # We use OmeTiffReader explicitly because the artifact store
            # renames files to UUIDs without extensions, which breaks bioio auto-detection.
            img = BioImage(path, reader=OmeTiffReader)
            assert img.dims.order == "TCZYX"
            # CZI is usually multi-channel or multi-scene, but we check if we got data
            assert img.data.size > 0
        except ImportError:
            pass
