"""Contract tests for Worker IPC protocol message schemas.

This module validates that all IPC message types conform to the schema
defined in specs/012-persistent-worker/contracts/worker-ipc.yaml.

Related spec: 012-persistent-worker
Related contract: specs/012-persistent-worker/contracts/worker-ipc.yaml
Related implementation: src/bioimage_mcp/runtimes/worker_ipc.py
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestExecuteMessages:
    """Contract tests for execute/execute_result messages (T008)."""

    def test_execute_request_required_fields(self):
        """Verify ExecuteRequest has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "execute"
        - id: str
        - inputs: object
        - params: object
        - work_dir: str
        """
        from bioimage_mcp.runtimes.worker_ipc import ExecuteRequest

        msg = ExecuteRequest(
            command="execute",
            id="base.skimage.gaussian",
            inputs={"image": "file:///tmp/input.ome.tif"},
            params={"sigma": 1.5},
            work_dir="/tmp/run_123",
        )

        assert msg.command == "execute"
        assert msg.id == "base.skimage.gaussian"
        assert msg.inputs == {"image": "file:///tmp/input.ome.tif"}
        assert msg.params == {"sigma": 1.5}
        assert msg.work_dir == "/tmp/run_123"

    def test_execute_request_optional_ordinal(self):
        """Verify ExecuteRequest accepts optional ordinal field."""
        from bioimage_mcp.runtimes.worker_ipc import ExecuteRequest

        msg = ExecuteRequest(
            command="execute",
            id="base.test",
            inputs={},
            params={},
            work_dir="/tmp",
            ordinal=42,
        )

        assert msg.ordinal == 42

    def test_execute_request_validates_command(self):
        """Verify ExecuteRequest rejects invalid command value."""
        from bioimage_mcp.runtimes.worker_ipc import ExecuteRequest

        with pytest.raises(ValidationError):
            ExecuteRequest(
                command="invalid",  # Must be "execute"
                id="base.test",
                inputs={},
                params={},
                work_dir="/tmp",
            )

    def test_execute_response_required_fields(self):
        """Verify ExecuteResponse has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "execute_result"
        - ok: bool
        """
        from bioimage_mcp.runtimes.worker_ipc import ExecuteResponse

        # Success case
        success = ExecuteResponse(
            command="execute_result",
            ok=True,
            outputs={"result": "mem://session/env/artifact"},
        )

        assert success.command == "execute_result"
        assert success.ok is True
        assert success.outputs is not None

    def test_execute_response_with_error(self):
        """Verify ExecuteResponse can include error field."""
        from bioimage_mcp.runtimes.worker_ipc import ExecuteResponse

        error_msg = ExecuteResponse(
            command="execute_result",
            ok=False,
            error={"code": "EXECUTION_ERROR", "message": "Division by zero"},
        )

        assert error_msg.ok is False
        assert error_msg.error is not None
        assert error_msg.error["code"] == "EXECUTION_ERROR"
        assert error_msg.error["message"] == "Division by zero"

    def test_execute_response_optional_fields(self):
        """Verify ExecuteResponse accepts optional log, warnings, provenance."""
        from bioimage_mcp.runtimes.worker_ipc import ExecuteResponse

        msg = ExecuteResponse(
            command="execute_result",
            ok=True,
            ordinal=1,
            outputs={"result": "mem://xyz"},
            log="Applied gaussian filter with sigma=1.5\n",
            warnings=["Warning: Large sigma value"],
            provenance={"duration_ms": 123, "env": "bioimage-mcp-base"},
        )

        assert msg.log == "Applied gaussian filter with sigma=1.5\n"
        assert len(msg.warnings) == 1
        assert msg.provenance["duration_ms"] == 123


class TestMaterializeMessages:
    """Contract tests for materialize/materialize_result messages (T008)."""

    def test_materialize_request_required_fields(self):
        """Verify MaterializeRequest has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "materialize"
        - ref_id: str
        - target_format: str (enum: OME-TIFF, OME-Zarr)
        """
        from bioimage_mcp.runtimes.worker_ipc import MaterializeRequest

        msg = MaterializeRequest(
            command="materialize",
            ref_id="mem://session/env/artifact",
            target_format="OME-TIFF",
        )

        assert msg.command == "materialize"
        assert msg.ref_id == "mem://session/env/artifact"
        assert msg.target_format == "OME-TIFF"

    def test_materialize_request_target_format_enum(self):
        """Verify MaterializeRequest enforces target_format enum."""
        from bioimage_mcp.runtimes.worker_ipc import MaterializeRequest

        # Valid formats
        for fmt in ["OME-TIFF", "OME-Zarr"]:
            msg = MaterializeRequest(
                command="materialize",
                ref_id="mem://xyz",
                target_format=fmt,
            )
            assert msg.target_format == fmt

        # Invalid format should raise
        with pytest.raises(ValidationError):
            MaterializeRequest(
                command="materialize",
                ref_id="mem://xyz",
                target_format="invalid-format",
            )

    def test_materialize_request_optional_dest_path(self):
        """Verify MaterializeRequest accepts optional dest_path."""
        from bioimage_mcp.runtimes.worker_ipc import MaterializeRequest

        msg = MaterializeRequest(
            command="materialize",
            ref_id="mem://xyz",
            target_format="OME-TIFF",
            dest_path="/tmp/custom_output.ome.tif",
            ordinal=2,
        )

        assert msg.dest_path == "/tmp/custom_output.ome.tif"
        assert msg.ordinal == 2

    def test_materialize_response_required_fields(self):
        """Verify MaterializeResponse has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "materialize_result"
        - ok: bool
        """
        from bioimage_mcp.runtimes.worker_ipc import MaterializeResponse

        msg = MaterializeResponse(
            command="materialize_result",
            ok=True,
            path="/tmp/run_123/result.ome.tif",
        )

        assert msg.command == "materialize_result"
        assert msg.ok is True
        assert msg.path == "/tmp/run_123/result.ome.tif"

    def test_materialize_response_with_error(self):
        """Verify MaterializeResponse can include error field."""
        from bioimage_mcp.runtimes.worker_ipc import MaterializeResponse

        msg = MaterializeResponse(
            command="materialize_result",
            ok=False,
            error={"code": "WRITE_ERROR", "message": "Permission denied"},
        )

        assert msg.ok is False
        assert msg.error is not None


class TestEvictMessages:
    """Contract tests for evict/evict_result messages (T008)."""

    def test_evict_request_required_fields(self):
        """Verify EvictRequest has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "evict"
        - ref_id: str
        """
        from bioimage_mcp.runtimes.worker_ipc import EvictRequest

        msg = EvictRequest(
            command="evict",
            ref_id="mem://session/env/artifact",
        )

        assert msg.command == "evict"
        assert msg.ref_id == "mem://session/env/artifact"

    def test_evict_request_optional_ordinal(self):
        """Verify EvictRequest accepts optional ordinal field."""
        from bioimage_mcp.runtimes.worker_ipc import EvictRequest

        msg = EvictRequest(
            command="evict",
            ref_id="mem://xyz",
            ordinal=5,
        )

        assert msg.ordinal == 5

    def test_evict_response_required_fields(self):
        """Verify EvictResponse has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "evict_result"
        - ok: bool
        """
        from bioimage_mcp.runtimes.worker_ipc import EvictResponse

        msg = EvictResponse(
            command="evict_result",
            ok=True,
        )

        assert msg.command == "evict_result"
        assert msg.ok is True

    def test_evict_response_with_error(self):
        """Verify EvictResponse can include error field."""
        from bioimage_mcp.runtimes.worker_ipc import EvictResponse

        msg = EvictResponse(
            command="evict_result",
            ok=False,
            error={"code": "NOT_FOUND", "message": "Artifact not in memory"},
        )

        assert msg.ok is False
        assert msg.error is not None


class TestShutdownMessages:
    """Contract tests for shutdown/shutdown_ack messages (T008)."""

    def test_shutdown_request_required_fields(self):
        """Verify ShutdownRequest has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "shutdown"
        """
        from bioimage_mcp.runtimes.worker_ipc import ShutdownRequest

        msg = ShutdownRequest(
            command="shutdown",
        )

        assert msg.command == "shutdown"

    def test_shutdown_request_optional_graceful(self):
        """Verify ShutdownRequest accepts optional graceful field with default."""
        from bioimage_mcp.runtimes.worker_ipc import ShutdownRequest

        # Default graceful=True
        default_msg = ShutdownRequest(command="shutdown")
        assert default_msg.graceful is True

        # Explicit graceful=False
        force_msg = ShutdownRequest(command="shutdown", graceful=False)
        assert force_msg.graceful is False

    def test_shutdown_response_required_fields(self):
        """Verify ShutdownResponse has all required fields per contract.

        Required per worker-ipc.yaml:
        - command: "shutdown_ack"
        - ok: bool
        """
        from bioimage_mcp.runtimes.worker_ipc import ShutdownResponse

        msg = ShutdownResponse(
            command="shutdown_ack",
            ok=True,
        )

        assert msg.command == "shutdown_ack"
        assert msg.ok is True


class TestIPCErrorModel:
    """Contract tests for IPCError definition (T008)."""

    def test_ipc_error_required_fields(self):
        """Verify IPCError has all required fields per contract.

        Required per worker-ipc.yaml definitions:
        - code: str
        - message: str
        """
        from bioimage_mcp.runtimes.worker_ipc import IPCError

        error = IPCError(
            code="EXECUTION_ERROR",
            message="Tool execution failed",
        )

        assert error.code == "EXECUTION_ERROR"
        assert error.message == "Tool execution failed"

    def test_ipc_error_missing_fields_rejected(self):
        """Verify IPCError rejects missing required fields."""
        from bioimage_mcp.runtimes.worker_ipc import IPCError

        # Missing code
        with pytest.raises(ValidationError):
            IPCError(message="Error message")

        # Missing message
        with pytest.raises(ValidationError):
            IPCError(code="ERROR_CODE")
