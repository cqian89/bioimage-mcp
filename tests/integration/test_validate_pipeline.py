"""Integration test for validation script success (T032).

Tests that the pipeline validation script runs successfully on sample datasets
and produces expected label outputs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def _mock_execute_step_validation(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step for validation testing."""
    labels_path = work_dir / "labels.ome.tiff"
    labels_path.write_bytes(b"FAKE_LABEL_DATA")

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
        "Validation segmentation successful",
        0,
    )


class TestValidatePipeline:
    """Integration tests for pipeline validation script."""

    def test_validation_script_produces_labels(self, tmp_path: Path, monkeypatch) -> None:
        """Test that validation produces LabelImageRef outputs."""
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
            _mock_execute_step_validation,
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
                                    "format": "OME-TIFF",
                                    "uri": "file:///sample/image.tiff",
                                }
                            },
                            "params": {"model_type": "cyto3"},
                        }
                    ]
                },
                skip_validation=True,
            )

        assert result["status"] == "success"

        # Verify labels output was produced
        with ExecutionService(config) as svc:
            status = svc.get_run_status(result["run_id"])

        assert "labels" in status["outputs"]
        assert status["outputs"]["labels"]["type"] == "LabelImageRef"

    def test_validation_workflow_returns_success(self, tmp_path: Path, monkeypatch) -> None:
        """Test that validation workflow returns success status."""
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
            _mock_execute_step_validation,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

        # Workflow should succeed for validation
        assert result["status"] == "success"
        assert "run_id" in result

    @pytest.mark.skipif(
        not Path("scripts/validate_pipeline.py").exists(),
        reason="Validation script not yet created",
    )
    def test_validation_script_cli_exit_zero(self, tmp_path: Path) -> None:
        """Test that validation script CLI exits with code 0 on success."""
        # This test will be enabled once the validation script is created
        result = subprocess.run(
            [sys.executable, "scripts/validate_pipeline.py", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

    def test_multiple_sample_validation(self, tmp_path: Path, monkeypatch) -> None:
        """Test validation on multiple sample images."""
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
            _mock_execute_step_validation,
        )

        # Simulate running validation on multiple samples
        sample_images = ["sample1.tiff", "sample2.tiff"]
        results = []

        with ExecutionService(config) as svc:
            for sample in sample_images:
                result = svc.run_workflow(
                    {
                        "steps": [
                            {
                                "fn_id": "cellpose.segment",
                                "inputs": {
                                    "image": {
                                        "type": "BioImageRef",
                                        "uri": f"file:///samples/{sample}",
                                    }
                                },
                                "params": {},
                            }
                        ]
                    },
                    skip_validation=True,
                )
                results.append(result)

        # All validations should succeed
        for result in results:
            assert result["status"] == "success"
