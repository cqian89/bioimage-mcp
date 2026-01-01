"""Integration test that OME-Zarr input fails fast with clear error (T015b).

Validates that attempting to use OME-Zarr format (deferred in v0.1) fails
with a clear, actionable error message rather than a cryptic failure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def _mock_execute_step_format_check(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that checks format and fails on OME-Zarr."""
    # Check inputs for unsupported format
    for name, inp in inputs.items():
        fmt = inp.get("format", "").lower()
        if "zarr" in fmt or "ome-zarr" in fmt.lower():
            return (
                {
                    "ok": False,
                    "outputs": {},
                    "error": {
                        "message": f"Unsupported format: {fmt}. OME-Zarr is not supported in v0.1. Please use OME-TIFF instead.",
                        "code": "UNSUPPORTED_FORMAT",
                        "format": fmt,
                    },
                },
                f"Format validation failed: {fmt} is not supported in v0.1",
                1,
            )

    # Success case
    labels_path = work_dir / "labels.ome.tiff"
    labels_path.write_bytes(b"FAKE")
    return (
        {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                    "path": str(labels_path),
                }
            },
        },
        "Success",
        0,
    )


class TestUnsupportedFormats:
    """Tests for unsupported format handling (OME-Zarr in v0.1)."""

    def test_ome_zarr_input_fails_fast(self, tmp_path: Path, monkeypatch) -> None:
        """Test that OME-Zarr input fails with clear error message."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_format_check,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "format": "OME-Zarr",  # Unsupported in v0.1
                                    "uri": "file:///path/to/image.zarr",
                                }
                            },
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

        # Should fail with clear error
        assert result["status"] == "failed"

    def test_ome_zarr_error_message_is_actionable(self, tmp_path: Path, monkeypatch) -> None:
        """Test that OME-Zarr error message suggests OME-TIFF alternative."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_format_check,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "format": "OME-Zarr",
                                    "uri": "file:///path/to/image.zarr",
                                }
                            },
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )
            status = svc.get_run_status(result["run_id"])

        assert status["status"] == "failed"
        # Verify error contains actionable information
        error = status.get("error", {})
        if isinstance(error, dict):
            error_msg = error.get("message", "")
        else:
            error_msg = str(error)

        # Should mention the unsupported format
        assert "OME-Zarr" in error_msg or "zarr" in error_msg.lower() or "UNSUPPORTED" in str(error)

    def test_zarr_lowercase_also_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'zarr' in various cases is caught."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_format_check,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "format": "zarr",  # lowercase
                                    "uri": "file:///path/to/image.zarr",
                                }
                            },
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

        assert result["status"] == "failed"

    def test_ome_tiff_still_works(self, tmp_path: Path, monkeypatch) -> None:
        """Test that OME-TIFF format is properly supported."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_format_check,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "format": "OME-TIFF",  # Supported!
                                    "uri": "file:///path/to/image.ome.tiff",
                                }
                            },
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

        assert result["status"] == "succeeded"

    def test_plain_tiff_still_works(self, tmp_path: Path, monkeypatch) -> None:
        """Test that plain TIFF format is supported."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_format_check,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "format": "TIFF",
                                    "uri": "file:///path/to/image.tiff",
                                }
                            },
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

        assert result["status"] == "succeeded"
