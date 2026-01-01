"""Integration test for run_workflow with Cellpose (T015).

Tests end-to-end workflow execution from image input through
Cellpose segmentation to LabelImageRef + LogRef + NativeOutputRef outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _create_test_image(path: Path) -> None:
    """Create a minimal valid TIFF-like file for testing."""
    # Minimal TIFF header (not a real image, but enough for path validation)
    path.write_bytes(b"II*\x00" + b"\x00" * 100)


def _mock_execute_step(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful Cellpose segmentation."""
    # Create mock output files
    labels_path = work_dir / "labels.ome.tiff"
    labels_path.write_bytes(b"FAKE_LABEL_IMAGE")

    bundle_path = work_dir / "cellpose_seg.npy"
    bundle_path.write_bytes(b"FAKE_NPY_BUNDLE")

    return (
        {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                    "path": str(labels_path),
                },
                "cellpose_bundle": {
                    "type": "NativeOutputRef",
                    "format": "cellpose-seg-npy",
                    "path": str(bundle_path),
                },
            },
            "log": "Segmentation completed successfully",
        },
        "Cellpose segmentation log: processed 1 image, found 42 cells",
        0,
    )


class TestCellposeE2E:
    """End-to-end integration tests for Cellpose segmentation workflow."""

    def test_run_workflow_produces_label_ref(self, tmp_path: Path, monkeypatch) -> None:
        """Test that run_workflow with Cellpose produces LabelImageRef output."""
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

        # Create sample input image
        sample_image = tmp_path / "sample.tiff"
        _create_test_image(sample_image)

        # Mock the execute_step to avoid actual Cellpose execution
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step,
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
                                    "uri": f"file://{sample_image}",
                                }
                            },
                            "params": {
                                "model_type": "cyto3",
                                "diameter": 30.0,
                            },
                        }
                    ]
                },
                skip_validation=True,  # Skip validation as we're using mock
            )

        assert result["status"] == "succeeded"
        assert "run_id" in result
        assert "workflow_record_ref_id" in result

    def test_run_workflow_produces_native_output_ref(self, tmp_path: Path, monkeypatch) -> None:
        """Test that run_workflow produces NativeOutputRef (cellpose bundle)."""
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
            _mock_execute_step,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {},
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

            # Verify run status includes outputs
            status = svc.get_run_status(result["run_id"])

        assert status["status"] == "succeeded"
        outputs = status["outputs"]

        # Verify LabelImageRef is present
        assert "labels" in outputs
        assert outputs["labels"]["type"] == "LabelImageRef"

        # Verify NativeOutputRef for cellpose bundle is present
        assert "cellpose_bundle" in outputs
        assert outputs["cellpose_bundle"]["type"] == "NativeOutputRef"
        assert outputs["cellpose_bundle"]["format"] == "cellpose-seg-npy"

        # Verify workflow record is present
        assert "workflow_record" in outputs
        assert outputs["workflow_record"]["type"] == "NativeOutputRef"
        assert outputs["workflow_record"]["format"] == "workflow-record-json"

    def test_run_workflow_returns_workflow_record_ref(self, tmp_path: Path, monkeypatch) -> None:
        """Test that run_workflow returns workflow_record_ref_id for replay."""
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
            _mock_execute_step,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

        # Verify workflow record ref is returned for replay capability
        assert "workflow_record_ref_id" in result
        assert isinstance(result["workflow_record_ref_id"], str)
        assert len(result["workflow_record_ref_id"]) > 0

    def test_run_workflow_creates_log_ref(self, tmp_path: Path, monkeypatch) -> None:
        """Test that run_workflow creates LogRef artifact."""
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
            _mock_execute_step,
        )

        store = ArtifactStore(config)
        with ExecutionService(config, artifact_store=store) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )
            status = svc.get_run_status(result["run_id"])

        # Verify log_ref is present
        assert "log_ref" in status
        log_ref = status["log_ref"]
        assert log_ref["type"] == "LogRef"
        assert "ref_id" in log_ref
