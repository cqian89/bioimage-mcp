"""Integration tests for tttrlib TTTR core operations (Phase 2).

Tests verify:
- tttrlib.TTTR constructor opens TTTR files and returns TTTRRef
- tttrlib.TTTR.header extracts metadata as NativeOutputRef (JSON)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

# Mark all tests in this module as requiring tttrlib environment
pytestmark = pytest.mark.requires_env("bioimage-mcp-tttrlib")

# Dataset paths
TTTR_DATA_ROOT = Path(__file__).parents[2] / "datasets" / "tttr-data"
SPC_FILE = TTTR_DATA_ROOT / "bh" / "bh_spc132.spc"
PTU_FILE = TTTR_DATA_ROOT / "imaging" / "leica" / "sp5" / "LSM_1.ptu"


def _mock_execute_step_tttr(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful TTTR operations."""
    if fn_id == "tttrlib.TTTR":
        container_type = params.get("container_type", "SPC-130")
        filename = params.get("filename")

        if not filename or not Path(filename).exists():
            return (
                {
                    "ok": False,
                    "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {filename}"},
                },
                "Error: File not found",
                1,
            )

        return (
            {
                "ok": True,
                "outputs": {
                    "tttr": {
                        "type": "TTTRRef",
                        "format": container_type,
                        "path": str(filename),
                    }
                },
                "log": "TTTR file opened successfully",
            },
            f"Loaded TTTR file: {filename}",
            0,
        )

    elif fn_id == "tttrlib.TTTR.header":
        header_path = work_dir / "header.json"
        header_path.write_text('{"format": "SPC-130", "version": "1.0", "channels": 4}')

        return (
            {
                "ok": True,
                "outputs": {
                    "header": {
                        "type": "NativeOutputRef",
                        "format": "json",
                        "path": str(header_path),
                    }
                },
                "log": "Header extracted",
            },
            "Extracted header metadata",
            0,
        )

    return (
        {"ok": False, "error": {"code": "UNKNOWN_FUNCTION", "message": f"Unknown fn_id: {fn_id}"}},
        "",
        1,
    )


class TestTTTRCore:
    """Integration tests for TTTR file loading and metadata extraction."""

    def test_tttr_open_spc_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening an SPC format TTTR file."""
        if not SPC_FILE.exists():
            pytest.skip(f"SPC file not found: {SPC_FILE}")

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
            _mock_execute_step_tttr,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR",
                            "inputs": {},
                            "params": {
                                "filename": str(SPC_FILE),
                                "container_type": "SPC-130",
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "tttr" in outputs
            assert outputs["tttr"]["type"] == "TTTRRef"
            assert outputs["tttr"]["format"] == "SPC-130"
            assert outputs["tttr"]["uri"].endswith(str(SPC_FILE.name))

    def test_tttr_open_ptu_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening a PTU format TTTR file."""
        if not PTU_FILE.exists():
            pytest.skip(f"PTU file not found: {PTU_FILE}")

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

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_tttr,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR",
                            "inputs": {},
                            "params": {
                                "filename": str(PTU_FILE),
                                "container_type": "PTU",
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "tttr" in outputs
            assert outputs["tttr"]["type"] == "TTTRRef"
            assert outputs["tttr"]["format"] == "PTU"

    def test_tttr_header_extraction(self, tmp_path: Path, monkeypatch) -> None:
        """Test extracting header metadata from TTTR file."""
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
            _mock_execute_step_tttr,
        )

        # Mock input TTTRRef
        mock_tttr = {
            "type": "TTTRRef",
            "format": "SPC-130",
            "uri": "file:///fake/path.spc",
            "ref_id": "mock-tttr-id",
        }

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR.header",
                            "inputs": {"tttr": mock_tttr},
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "header" in outputs
            assert outputs["header"]["type"] == "NativeOutputRef"
            assert outputs["header"]["format"] == "json"

            # Verify header content (mocked)
            header_uri = outputs["header"]["uri"]
            header_path = Path(header_uri.replace("file://", ""))
            assert header_path.exists()
            with open(header_path) as f:
                header_data = json.load(f)
            assert header_data["format"] == "SPC-130"
            assert "channels" in header_data

    def test_tttr_invalid_file_error(self, tmp_path: Path, monkeypatch) -> None:
        """Test error handling for invalid TTTR file."""
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
            _mock_execute_step_tttr,
        )

        non_existent_file = tmp_path / "non_existent.spc"

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR",
                            "inputs": {},
                            "params": {
                                "filename": str(non_existent_file),
                                "container_type": "SPC-130",
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            # The workflow should fail because the mock returns ok=False for missing file
            assert result["status"] == "failed"
            assert "FILE_NOT_FOUND" in str(result)
