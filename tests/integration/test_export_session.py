"""Integration test for session export (US4).

Tests that sessions can be exported to reproducible workflow artifacts,
filtering only canonical steps and preserving execution history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


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
    # Create a fake output file
    output_path = work_dir / "output.txt"
    output_path.write_text("result")

    return (
        {
            "ok": True,
            "outputs": {
                "result": {
                    "type": "BioImageRef",
                    "format": "text",
                    "path": str(output_path),
                }
            },
        },
        "Execution successful",
        0,
    )


def _mock_execute_step_failure(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates failure."""
    return (
        {
            "ok": False,
            "error": {"message": "Simulated failure", "code": "TEST_ERROR"},
        },
        "Execution failed",
        1,
    )


class TestExportSession:
    """Integration tests for session export functionality."""

    @pytest.fixture
    def services(self, tmp_path, monkeypatch):
        """Setup services with temporary stores and mocked execution."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        # Setup stores
        artifact_store = ArtifactStore(config)
        session_store = SessionStore()

        # Setup services
        session_manager = SessionManager(session_store, config)
        execution_service = ExecutionService(config, artifact_store=artifact_store)
        interactive_service = InteractiveExecutionService(session_manager, execution_service)

        return interactive_service, execution_service, artifact_store

    def test_export_session_canonical_steps(self, services, monkeypatch):
        """Test that export includes only canonical (successful) steps."""
        interactive, execution, artifact_store = services

        # 1. Setup session
        session_id = "test-session-001"

        # 2. Step 1: Attempt 1 (Failure)
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_failure,
        )
        result1 = interactive.call_tool(
            session_id=session_id,
            fn_id="test.tool",
            inputs={},
            params={"attempt": 1},
        )
        assert result1["status"] == "failed"

        # 3. Step 1: Attempt 2 (Success) - This should become canonical
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_success,
        )
        result2 = interactive.call_tool(
            session_id=session_id,
            fn_id="test.tool",
            inputs={},
            params={"attempt": 2},
            ordinal=0,  # Retry same ordinal
        )
        assert result2["status"] == "success"

        # 4. Step 2: Success
        result3 = interactive.call_tool(
            session_id=session_id,
            fn_id="test.tool",
            inputs={"prev": {"ref_id": "some-ref", "type": "BioImageRef"}},  # Dummy input
            params={"step": 2},
        )
        assert result3["status"] == "success"

        # 5. Export Session
        if not hasattr(interactive, "export_session"):
            pytest.skip("export_session not implemented yet")

        export_result = interactive.export_session(session_id)

        # 6. Verify Export Result
        assert export_result["session_id"] == session_id
        workflow_ref = export_result["workflow_ref"]
        assert workflow_ref["type"] == "NativeOutputRef"
        assert workflow_ref["format"] == "workflow-record-json"

        # 7. Verify Content
        record_content = artifact_store.get_raw_content(workflow_ref["ref_id"])
        if isinstance(record_content, bytes):
            record = json.loads(record_content.decode())
        else:
            record = json.loads(record_content)

        assert record["session_id"] == session_id
        steps = record["steps"]
        assert len(steps) == 2

        # Verify Step 1 is the successful attempt
        assert steps[0]["params"]["attempt"] == 2

        # Verify Step 2 is present
        assert steps[1]["params"]["step"] == 2

        # Verify Session Status
        session = interactive.session_manager.get_session(session_id)
        assert session.status == "exported"

    def test_export_empty_session_fails(self, services):
        """Test that exporting an empty session raises an error."""
        interactive, _, _ = services
        session_id = "empty-session"
        interactive.session_manager.ensure_session(session_id)

        if not hasattr(interactive, "export_session"):
            pytest.skip("export_session not implemented yet")

        with pytest.raises(ValueError, match="Cannot export empty session"):
            interactive.export_session(session_id)


class TestExportSessionObjectRef:
    """T043: Integration tests for session_export with ObjectRef."""

    @pytest.fixture
    def services(self, tmp_path, monkeypatch):
        """Setup services with temporary stores and mocked execution."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        # Setup stores
        artifact_store = ArtifactStore(config)
        session_store = SessionStore()

        # Setup services
        session_manager = SessionManager(session_store, config)
        execution_service = ExecutionService(config, artifact_store=artifact_store)
        interactive_service = InteractiveExecutionService(session_manager, execution_service)

        return interactive_service, execution_service, artifact_store

    def test_export_workflow_contains_objectref_outputs(self, services, monkeypatch):
        """Assert ObjectRef outputs are recorded in workflow-record-json."""
        interactive, execution, artifact_store = services
        session_id = "objref-session-001"

        # 1. Mock execute_step to return an ObjectRef output
        def _mock_execute_step_objref(**kwargs):
            return (
                {
                    "ok": True,
                    "outputs": {
                        "model": {
                            "type": "ObjectRef",
                            "ref_id": "obj-123",
                            "uri": "obj://test-session/env/obj-123",
                            "python_class": "cellpose.models.CellposeModel",
                            "metadata": {
                                "init_params": {"model_type": "cyto"},
                                "device": "cpu",
                            },
                            "format": "pickle",
                            "mime_type": "application/x-python-pickle",
                            "size_bytes": 1024,
                        }
                    },
                },
                "Execution successful",
                0,
            )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_objref,
        )

        # 2. Call tool that returns an ObjectRef
        result = interactive.call_tool(
            session_id=session_id,
            fn_id="cellpose.CellposeModel",
            inputs={},
            params={"model_type": "cyto"},
        )
        assert result["status"] == "success"
        assert result["outputs"]["model"]["type"] == "ObjectRef"

        # 3. Export the session
        export_result = interactive.export_session(session_id)
        workflow_ref = export_result["workflow_ref"]

        # 4. Verify the workflow record contains the ObjectRef with python_class
        record_content = artifact_store.get_raw_content(workflow_ref["ref_id"])
        if isinstance(record_content, bytes):
            record = json.loads(record_content.decode())
        else:
            record = json.loads(record_content)

        step = record["steps"][0]
        model_output = step["outputs"]["model"]

        assert model_output["type"] == "ObjectRef"
        # These are the key assertions for T043
        assert model_output["python_class"] == "cellpose.models.CellposeModel"
        assert model_output["metadata"]["init_params"] == {"model_type": "cyto"}

    def test_export_workflow_preserves_objectref_init_params(self, services, monkeypatch):
        """Assert init_params are captured in workflow record for replay (FR-004)."""
        interactive, execution, artifact_store = services
        session_id = "objref-session-002"

        # Mock for multiple steps
        mock_returns = [
            # Step 1: create model
            (
                {
                    "ok": True,
                    "outputs": {
                        "model": {
                            "type": "ObjectRef",
                            "ref_id": "obj-123",
                            "uri": "obj://test-session/env/obj-123",
                            "python_class": "cellpose.models.CellposeModel",
                            "metadata": {"init_params": {"pretrained_model": "cyto3"}},
                            "format": "pickle",
                            "mime_type": "application/x-python-pickle",
                            "size_bytes": 1024,
                        }
                    },
                },
                "Success",
                0,
            ),
            # Step 2: use model
            (
                {
                    "ok": True,
                    "outputs": {
                        "mask": {
                            "type": "LabelImageRef",
                            "ref_id": "mask-123",
                            "uri": "file:///tmp/mask.tif",
                            "format": "OME-TIFF",
                        }
                    },
                },
                "Success",
                0,
            ),
        ]

        def _mock_dispatcher(**kwargs):
            return mock_returns.pop(0)

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_dispatcher,
        )

        # Step 1
        res1 = interactive.call_tool(
            session_id, "cellpose.CellposeModel", {}, {"pretrained_model": "cyto3"}
        )
        model_ref = res1["outputs"]["model"]

        # Step 2
        interactive.call_tool(session_id, "cellpose.CellposeModel.eval", {"model": model_ref}, {})

        # Export
        export_result = interactive.export_session(session_id)
        record_content = artifact_store.get_raw_content(export_result["workflow_ref"]["ref_id"])
        record = json.loads(
            record_content if isinstance(record_content, str) else record_content.decode()
        )

        # Check step 0 (model creation)
        assert record["steps"][0]["outputs"]["model"]["metadata"]["init_params"] == {
            "pretrained_model": "cyto3"
        }
        assert (
            record["steps"][0]["outputs"]["model"]["python_class"]
            == "cellpose.models.CellposeModel"
        )

    def test_export_workflow_with_external_objectref(self, services, monkeypatch):
        """Assert external ObjectRef inputs are tracked in workflow record."""
        interactive, execution, artifact_store = services
        session_id = "external-objref-session"

        # 1. Mock artifact_store.get to return an ObjectRef-like object
        from unittest.mock import MagicMock

        mock_obj = MagicMock()
        mock_obj.type = "ObjectRef"
        original_get = artifact_store.get
        monkeypatch.setattr(
            artifact_store,
            "get",
            lambda ref_id: mock_obj if ref_id == "external-obj-123" else original_get(ref_id),
        )

        # 2. Mock execute_step
        def _mock_execute_step_success(**kwargs):
            return (
                {
                    "ok": True,
                    "outputs": {
                        "res": {
                            "type": "ScalarRef",
                            "ref_id": "scalar-1",
                            "uri": "mem://scalar-1",
                        }
                    },
                },
                "OK",
                0,
            )

        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _mock_execute_step_success)

        # 3. Call tool with external ObjectRef
        interactive.call_tool(
            session_id=session_id,
            fn_id="test.use_model",
            inputs={"model": {"ref_id": "external-obj-123", "type": "ObjectRef"}},
            params={},
        )

        # 4. Export
        export_result = interactive.export_session(session_id)
        record_content = artifact_store.get_raw_content(export_result["workflow_ref"]["ref_id"])
        record = json.loads(
            record_content if isinstance(record_content, str) else record_content.decode()
        )

        # 5. Verify external input
        assert "external-obj-123" in record["external_inputs"]
        assert record["external_inputs"]["external-obj-123"]["type"] == "ObjectRef"
