"""Integration tests for CLSM and ICS (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

# Mark all tests in this module as requiring tttrlib environment
pytestmark = pytest.mark.requires_env("bioimage-mcp-tttrlib")

# Dataset paths
TTTR_DATA_ROOT = Path(__file__).parents[2] / "datasets" / "tttr-data"
PTU_FILE = TTTR_DATA_ROOT / "imaging" / "leica" / "sp5" / "LSM_1.ptu"


def _mock_execute_step_clsm_ics(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None = None,
    **kwargs: Any,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step for CLSM and ICS operations."""
    if fn_id == "tttrlib.TTTR":
        filename = params.get("filename")
        return (
            {
                "ok": True,
                "outputs": {
                    "tttr": {
                        "type": "TTTRRef",
                        "format": "PTU",
                        "path": str(filename),
                        "metadata": {
                            "n_valid_events": 1000,
                        },
                    }
                },
                "log": "TTTR file opened",
            },
            f"Loaded {filename}",
            0,
        )

    elif fn_id == "tttrlib.CLSMImage":
        return (
            {
                "ok": True,
                "outputs": {
                    "clsm": {
                        "type": "ObjectRef",
                        "ref_id": "clsm-id",
                        "uri": "obj://session/env/clsm_id",
                        "python_class": "tttrlib.CLSMImage",
                    }
                },
                "log": "CLSMImage constructed",
            },
            "Constructed CLSMImage with 1 frames",
            0,
        )

    elif fn_id == "tttrlib.CLSMImage.compute_ics":
        ics_path = work_dir / "ics.ome.tif"
        ics_path.write_bytes(b"FAKE_OME_TIFF")

        outputs = {
            "ics": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(ics_path),
                "metadata": {
                    "axes": "YXC",
                    "shape": [256, 256, 1],
                    "ndim": 3,
                    "dims": ["Y", "X", "C"],
                },
            }
        }

        if params.get("include_summary"):
            summary_path = work_dir / "ics_summary.csv"
            summary_path.write_text("parameter,value\nG(0,0),1.5\nN,0.67")
            outputs["summary"] = {
                "type": "TableRef",
                "format": "csv",
                "path": str(summary_path),
                "metadata": {
                    "columns": [
                        {"name": "parameter", "dtype": "string"},
                        {"name": "value", "dtype": "float64"},
                    ],
                    "row_count": 2,
                },
            }

        return (
            {
                "ok": True,
                "outputs": outputs,
                "log": "ICS computed",
            },
            "Computed ICS map",
            0,
        )

    return (
        {
            "ok": False,
            "error": {"code": "UNKNOWN_FUNCTION", "message": f"Unknown function: {fn_id}"},
        },
        "",
        1,
    )


class TestCLSMImage:
    """Integration tests for tttrlib.CLSMImage construction."""

    def test_clsm_image_construction(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test constructing CLSMImage from TTTR data."""
        artifacts_root = tmp_path / "artifacts"
        tools_root = tmp_path / "tools"
        tools_root.mkdir()

        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[tools_root],
            fs_allowlist_read=[TTTR_DATA_ROOT, tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        # Mock the execute_step to avoid actual tttrlib execution
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_clsm_ics,
        )

        with ExecutionService(config) as svc:
            # Step 1: Open PTU file
            tttr_result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR",
                            "inputs": {},
                            "params": {
                                "filename": str(PTU_FILE)
                                if PTU_FILE.exists()
                                else "/fake/LSM_1.ptu",
                                "container_type": "PTU",
                            },
                        }
                    ]
                },
                skip_validation=True,
            )
            assert tttr_result["status"] == "success"
            tttr_ref = svc.get_run_status(tttr_result["run_id"])["outputs"]["tttr"]

            # Step 2: Construct CLSMImage
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.CLSMImage",
                            "inputs": {"tttr": tttr_ref},
                            "params": {
                                "reading_routine": "SP5",
                                "channels": [0],
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "clsm" in outputs
            assert outputs["clsm"]["type"] == "ObjectRef"
            assert outputs["clsm"]["python_class"] == "tttrlib.CLSMImage"


class TestICS:
    """Integration tests for Image Correlation Spectroscopy."""

    def test_clsm_compute_ics(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test computing ICS on CLSM image."""
        artifacts_root = tmp_path / "artifacts"
        tools_root = tmp_path / "tools"
        tools_root.mkdir()

        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[tools_root],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_clsm_ics,
        )

        # Mock input CLSM ObjectRef
        mock_clsm = {
            "type": "ObjectRef",
            "uri": "obj://session/env/clsm_id",
            "python_class": "tttrlib.CLSMImage",
            "ref_id": "clsm-id",
        }

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.CLSMImage.compute_ics",
                            "inputs": {"clsm": mock_clsm},
                            "params": {
                                "subtract_average": "frame",
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "ics" in outputs
            assert outputs["ics"]["type"] == "BioImageRef"
            assert outputs["ics"]["format"] == "OME-TIFF"
            assert outputs["ics"]["metadata"]["shape"] == [256, 256, 1]

    def test_clsm_ics_with_summary(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test ICS with summary table output."""
        artifacts_root = tmp_path / "artifacts"
        tools_root = tmp_path / "tools"
        tools_root.mkdir()

        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[tools_root],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_clsm_ics,
        )

        # Mock input CLSM ObjectRef
        mock_clsm = {
            "type": "ObjectRef",
            "uri": "obj://session/env/clsm_id",
            "python_class": "tttrlib.CLSMImage",
            "ref_id": "clsm-id",
        }

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.CLSMImage.compute_ics",
                            "inputs": {"clsm": mock_clsm},
                            "params": {
                                "include_summary": True,
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "ics" in outputs
            assert "summary" in outputs
            assert outputs["summary"]["type"] == "TableRef"
            assert outputs["summary"]["format"] == "csv"
