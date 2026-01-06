"""Unit tests for worker IPC protocol: WorkerState enum and NDJSON framing.

This module tests the low-level IPC components used for Core-to-Worker communication:
- WorkerState enum and transitions
- NDJSON message encoding/decoding
- IPC message type validation

Related spec: 012-persistent-worker
Related files:
  - src/bioimage_mcp/runtimes/worker_ipc.py (to be created)
"""

from __future__ import annotations

import json

import pytest


class TestWorkerStateEnum:
    """Unit tests for WorkerState enum (T012-T014)."""

    def test_worker_state_enum_values(self):
        """Verify WorkerState enum has all required lifecycle states.

        Related: T012 - WorkerState enum definition

        Expected values:
        - spawning: Process is starting and conda env is activating
        - ready: Worker is idle and awaiting next request
        - busy: Worker is currently processing a request
        - terminated: Process has exited (normally or crashed)
        """
        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        assert hasattr(WorkerState, "SPAWNING")
        assert hasattr(WorkerState, "READY")
        assert hasattr(WorkerState, "BUSY")
        assert hasattr(WorkerState, "TERMINATED")

        # Verify enum values
        assert WorkerState.SPAWNING.value == "spawning"
        assert WorkerState.READY.value == "ready"
        assert WorkerState.BUSY.value == "busy"
        assert WorkerState.TERMINATED.value == "terminated"

    def test_worker_state_string_representation(self):
        """Verify WorkerState enum values have correct string representation."""
        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        assert str(WorkerState.SPAWNING.value) == "spawning"
        assert str(WorkerState.READY.value) == "ready"
        assert str(WorkerState.BUSY.value) == "busy"
        assert str(WorkerState.TERMINATED.value) == "terminated"


class TestNDJSONFraming:
    """Unit tests for NDJSON message encoding/decoding (T010)."""

    def test_encode_message_to_ndjson(self):
        """Verify that encode_message produces valid NDJSON (single line with newline).

        Related: T010 - NDJSON framing helpers

        Expected behavior:
        1. Input: Pydantic model
        2. Output: JSON string ending with '\n'
        3. No embedded newlines in the JSON
        4. Valid JSON when newline is stripped
        """
        from bioimage_mcp.runtimes.worker_ipc import ExecuteRequest, encode_message

        msg = ExecuteRequest(
            command="execute",
            fn_id="base.xarray.sum",
            inputs={},
            params={},
            work_dir="/tmp",
        )
        encoded = encode_message(msg)

        # Must end with newline
        assert encoded.endswith("\n")
        # Should be single line (no embedded newlines before final one)
        assert encoded.count("\n") == 1
        # Must be valid JSON
        decoded = json.loads(encoded.strip())
        assert decoded["command"] == "execute"
        assert decoded["fn_id"] == "base.xarray.sum"

    def test_decode_message_from_ndjson(self):
        """Verify that decode_message parses NDJSON into Python dict.

        Related: T010 - NDJSON framing helpers

        Expected behavior:
        1. Input: NDJSON string (JSON with trailing newline)
        2. Output: Python dict
        3. Handles both '\n' and '\r\n' line endings
        4. Raises error on invalid JSON
        """
        from bioimage_mcp.runtimes.worker_ipc import decode_message

        ndjson = '{"command": "execute_result", "ok": true, "outputs": {"result": 42}}\n'
        decoded = decode_message(ndjson)

        assert decoded["command"] == "execute_result"
        assert decoded["ok"] is True
        assert decoded["outputs"]["result"] == 42

    def test_decode_message_handles_invalid_json(self):
        """Verify that decode_message raises clear error on invalid JSON."""
        from bioimage_mcp.runtimes.worker_ipc import decode_message

        with pytest.raises(json.JSONDecodeError):
            decode_message("not valid json\n")

    def test_round_trip_encoding_decoding(self):
        """Verify that encode -> decode preserves message structure."""
        from bioimage_mcp.runtimes.worker_ipc import (
            MaterializeRequest,
            decode_message,
            encode_message,
        )

        original = MaterializeRequest(
            command="materialize",
            ref_id="abc123",
            target_format="OME-TIFF",
        )

        encoded = encode_message(original)
        decoded_dict = decode_message(encoded)

        # Verify key fields preserved
        assert decoded_dict["command"] == "materialize"
        assert decoded_dict["ref_id"] == "abc123"
        assert decoded_dict["target_format"] == "OME-TIFF"


class TestIPCMessageModels:
    """Unit tests for IPC message Pydantic models (T009)."""

    def test_class_context_model(self):
        """T007: Test ClassContext model with python_class and init_params."""
        from bioimage_mcp.runtimes.worker_ipc import ClassContext

        ctx = ClassContext(
            python_class="cellpose.models.CellposeModel",
            init_params={"model_type": "cyto", "gpu": False},
        )
        assert ctx.python_class == "cellpose.models.CellposeModel"
        assert ctx.init_params["model_type"] == "cyto"

    def test_execute_request_model(self):
        """Verify ExecuteRequest model has required fields.

        Related: T009 - ExecuteRequest Pydantic model
        T007: Added class_context field
        """
        from bioimage_mcp.runtimes.worker_ipc import ClassContext, ExecuteRequest

        msg = ExecuteRequest(
            command="execute",
            fn_id="base.xarray.sum",
            inputs={"image": "file:///tmp/test.tif"},
            params={"dim": "T"},
            work_dir="/tmp/run_123",
            class_context=ClassContext(python_class="MyClass", init_params={"a": 1}),
        )

        assert msg.command == "execute"
        assert msg.fn_id == "base.xarray.sum"
        assert msg.params["dim"] == "T"
        assert msg.work_dir == "/tmp/run_123"
        assert msg.class_context.python_class == "MyClass"

    def test_execute_response_model(self):
        """Verify ExecuteResponse model has required fields.

        Related: T009 - ExecuteResponse Pydantic model

        Required fields:
        - command: Literal["execute_result"]
        - ok: bool
        - outputs: dict[str, Any] | None
        - error: IPCError | None
        """
        from bioimage_mcp.runtimes.worker_ipc import ExecuteResponse

        # Success case
        success = ExecuteResponse(
            command="execute_result",
            ok=True,
            outputs={"output": "mem://xyz"},
        )
        assert success.outputs is not None
        assert success.error is None

        # Error case
        error = ExecuteResponse(
            command="execute_result",
            ok=False,
            error={"code": "EXEC_ERROR", "message": "Division by zero"},
        )
        assert error.outputs is None
        assert error.error is not None

    def test_materialize_request_model(self):
        """Verify MaterializeRequest model has required fields.

        Related: T009 - MaterializeRequest Pydantic model

        Required fields:
        - command: Literal["materialize"]
        - ref_id: str
        - target_format: Literal["OME-TIFF", "OME-Zarr"]
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

    def test_materialize_response_model(self):
        """Verify MaterializeResponse model has required fields.

        Related: T009 - MaterializeResponse Pydantic model

        Required fields:
        - command: Literal["materialize_result"]
        - ok: bool
        - path: str | None
        - error: IPCError | None
        """
        from bioimage_mcp.runtimes.worker_ipc import MaterializeResponse

        msg = MaterializeResponse(
            command="materialize_result",
            ok=True,
            path="/tmp/artifacts/abc.ome.tiff",
        )

        assert msg.command == "materialize_result"
        assert msg.ok is True
        assert msg.path == "/tmp/artifacts/abc.ome.tiff"

    def test_evict_request_model(self):
        """Verify EvictRequest model has required fields.

        Related: T009 - EvictRequest Pydantic model

        Required fields:
        - command: Literal["evict"]
        - ref_id: str
        """
        from bioimage_mcp.runtimes.worker_ipc import EvictRequest

        msg = EvictRequest(
            command="evict",
            ref_id="mem://session/env/artifact",
        )

        assert msg.command == "evict"
        assert msg.ref_id == "mem://session/env/artifact"

    def test_evict_response_model(self):
        """Verify EvictResponse model has required fields.

        Related: T009 - EvictResponse Pydantic model

        Required fields:
        - command: Literal["evict_result"]
        - ok: bool
        """
        from bioimage_mcp.runtimes.worker_ipc import EvictResponse

        success = EvictResponse(
            command="evict_result",
            ok=True,
        )
        assert success.ok is True

    def test_shutdown_request_model(self):
        """Verify ShutdownRequest model has required fields.

        Related: T009 - ShutdownRequest Pydantic model

        Required fields:
        - command: Literal["shutdown"]
        """
        from bioimage_mcp.runtimes.worker_ipc import ShutdownRequest

        msg = ShutdownRequest(command="shutdown")
        assert msg.command == "shutdown"

    def test_shutdown_response_model(self):
        """Verify ShutdownResponse model has required fields.

        Related: T009 - ShutdownResponse Pydantic model

        Required fields:
        - command: Literal["shutdown_ack"]
        - ok: bool
        """
        from bioimage_mcp.runtimes.worker_ipc import ShutdownResponse

        msg = ShutdownResponse(command="shutdown_ack", ok=True)
        assert msg.command == "shutdown_ack"
        assert msg.ok is True
