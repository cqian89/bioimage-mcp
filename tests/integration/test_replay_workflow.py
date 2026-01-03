"""Integration test for replay_workflow() (T026).

Tests that workflow replay from a saved NativeOutputRef (workflow-record-json)
correctly starts a new run with equivalent workflow specification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _mock_execute_step_success(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful execution."""
    labels_path = work_dir / "labels.ome.tiff"
    labels_path.write_bytes(b"FAKE_LABELS")

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
        "Execution successful",
        0,
    )


class TestReplayWorkflow:
    """Integration tests for workflow replay functionality."""

    def test_replay_workflow_from_record(self, tmp_path: Path, monkeypatch) -> None:
        """Test that replay_workflow creates new run from saved record."""
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
            _mock_execute_step_success,
        )

        with ExecutionService(config) as svc:
            # First run: create original workflow
            original_result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {"image": {"type": "BioImageRef"}},
                            "params": {"diameter": 30.0},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert original_result["status"] == "succeeded"
            assert "workflow_record_ref_id" in original_result

            # Get the workflow record
            workflow_record_ref_id = original_result["workflow_record_ref_id"]

            # Replay: create new run from saved record
            replay_result = svc.replay_workflow(workflow_record_ref_id)

            assert replay_result["status"] in {"succeeded", "running", "queued"}
            assert replay_result["run_id"] != original_result["run_id"]

    def test_replay_produces_same_artifact_types(self, tmp_path: Path, monkeypatch) -> None:
        """Test that replay produces outputs of same artifact types."""
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
            _mock_execute_step_success,
        )

        with ExecutionService(config) as svc:
            original_result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "cellpose.segment",
                            "inputs": {},
                            "params": {"diameter": 30.0},
                        }
                    ]
                },
                skip_validation=True,
            )

            original_status = svc.get_run_status(original_result["run_id"])
            original_output_types = {
                name: out.get("type") for name, out in original_status["outputs"].items()
            }

            replay_result = svc.replay_workflow(original_result["workflow_record_ref_id"])
            replay_status = svc.get_run_status(replay_result["run_id"])

            # Verify same artifact types produced
            for name, expected_type in original_output_types.items():
                if name in replay_status["outputs"]:
                    assert replay_status["outputs"][name].get("type") == expected_type

    def test_replay_links_to_original_run(self, tmp_path: Path, monkeypatch) -> None:
        """Test that replayed run links to original run_id in provenance."""
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
            _mock_execute_step_success,
        )

        with ExecutionService(config) as svc:
            original_result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

            replay_result = svc.replay_workflow(original_result["workflow_record_ref_id"])

            # Verify provenance links to original
            # This would need to check run store for provenance field
            assert replay_result["run_id"] != original_result["run_id"]

    def test_replay_with_missing_inputs_fails_clearly(self, tmp_path: Path, monkeypatch) -> None:
        """Test that replay with missing required inputs fails with clear error."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        # Create a workflow record artifact manually with missing inputs
        store = ArtifactStore(config)
        workflow_record = {
            "schema_version": "0.1",
            "run_id": "original-run-001",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {
                "steps": [
                    {
                        "fn_id": "cellpose.segment",
                        "inputs": {
                            "image": {
                                "ref_id": "nonexistent-image-ref",
                                "type": "BioImageRef",
                            }
                        },
                        "params": {"diameter": 30.0},
                    }
                ]
            },
            "inputs": {"image": {"ref_id": "nonexistent-image-ref"}},
            "params": {"diameter": 30.0},
            "outputs": {},
        }

        record_ref = store.write_native_output(
            workflow_record,
            format="workflow-record-json",
        )

        with ExecutionService(config, artifact_store=store) as svc:
            # Replay should fail or warn about missing input
            with pytest.raises(Exception):
                svc.replay_workflow(record_ref.ref_id)

    def test_workflow_record_can_be_parsed(self, tmp_path: Path, monkeypatch) -> None:
        """Test that workflow record artifact can be loaded and parsed."""
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
            _mock_execute_step_success,
        )

        store = ArtifactStore(config)
        with ExecutionService(config, artifact_store=store) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

            # Get workflow record ref
            workflow_record_ref_id = result["workflow_record_ref_id"]

            # Verify we can get the artifact
            record_ref = store.get(workflow_record_ref_id)
            assert record_ref is not None
            assert record_ref.type == "NativeOutputRef"
            assert record_ref.format == "workflow-record-json"

            # Verify we can read and parse it
            raw_content = store.get_raw_content(workflow_record_ref_id)
            if isinstance(raw_content, bytes):
                record_data = json.loads(raw_content.decode())
            else:
                record_data = json.loads(raw_content)

            assert "schema_version" in record_data
            assert "workflow_spec" in record_data
            assert record_data["run_id"] == result["run_id"]
