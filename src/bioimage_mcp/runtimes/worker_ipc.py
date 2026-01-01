"""Worker IPC protocol models and NDJSON framing utilities.

This module defines the NDJSON-based IPC protocol for communication between
the Core process and Worker subprocesses. It provides:

1. Pydantic models for all request/response message types
2. NDJSON encoding/decoding helpers for message framing
3. WorkerState enum for worker lifecycle management

Transport: stdin/stdout pipes
Format: NDJSON (one JSON object per line, terminated by '\n')
Direction: Core -> Worker (requests), Worker -> Core (responses)

Related spec: 012-persistent-worker
Related contract: specs/012-persistent-worker/contracts/worker-ipc.yaml
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# WorkerState Enum (T013)
# ============================================================================


class WorkerState(str, Enum):
    """Lifecycle states for a persistent worker process.

    State transitions:
    - spawning -> ready (on successful startup)
    - spawning -> terminated (on startup failure)
    - ready -> busy (on request received)
    - busy -> ready (on request completed)
    - busy -> terminated (on crash during processing)
    - ready -> terminated (on shutdown or crash)
    """

    SPAWNING = "spawning"
    READY = "ready"
    BUSY = "busy"
    TERMINATED = "terminated"


# ============================================================================
# Error Model
# ============================================================================


class IPCError(BaseModel):
    """Error information for failed IPC operations.

    Per contract definition in worker-ipc.yaml.
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")


# ============================================================================
# Execute Messages (T009)
# ============================================================================


class ExecuteRequest(BaseModel):
    """Request to execute a tool function within the worker environment.

    Per contract: ExecuteRequest in worker-ipc.yaml.
    """

    command: Literal["execute"] = Field(..., description="Message type discriminator")
    fn_id: str = Field(..., description="Function identifier (e.g., 'base.skimage.gaussian')")
    inputs: dict[str, Any] = Field(
        ..., description="Input artifact references keyed by port name (URI strings)"
    )
    params: dict[str, Any] = Field(..., description="Function parameters (JSON-serializable)")
    work_dir: str = Field(..., description="Working directory for file outputs")
    ordinal: int | None = Field(None, description="Request sequence number for correlation")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'execute'."""
        if v != "execute":
            raise ValueError(f"ExecuteRequest command must be 'execute', got '{v}'")
        return v


class ExecuteResponse(BaseModel):
    """Result of a function execution.

    Per contract: ExecuteResponse in worker-ipc.yaml.
    """

    command: Literal["execute_result"] = Field(..., description="Message type discriminator")
    ok: bool = Field(..., description="True if execution succeeded")
    ordinal: int | None = Field(None, description="Corresponds to the ordinal in the request")
    outputs: dict[str, Any] | None = Field(
        None, description="Output artifact references (when ok=true)"
    )
    log: str | None = Field(None, description="Merged stdout/stderr from the function execution")
    error: dict[str, Any] | None = Field(None, description="Error details (when ok=false)")
    warnings: list[str] | None = Field(None, description="Non-fatal warnings")
    provenance: dict[str, Any] | None = Field(
        None, description="Execution metadata (timing, environment, etc.)"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'execute_result'."""
        if v != "execute_result":
            raise ValueError(f"ExecuteResponse command must be 'execute_result', got '{v}'")
        return v


# ============================================================================
# Materialize Messages (T009)
# ============================================================================


class MaterializeRequest(BaseModel):
    """Request to save an in-memory (mem://) artifact to persistent storage.

    Per contract: MaterializeRequest in worker-ipc.yaml.
    """

    command: Literal["materialize"] = Field(..., description="Message type discriminator")
    ref_id: str = Field(..., description="mem:// artifact to materialize")
    target_format: Literal["OME-TIFF", "OME-Zarr"] = Field(
        ..., description="Output format for materialized artifact"
    )
    dest_path: str | None = Field(
        None, description="Optional destination path (otherwise auto-generated)"
    )
    ordinal: int | None = Field(None, description="Request sequence number for correlation")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'materialize'."""
        if v != "materialize":
            raise ValueError(f"MaterializeRequest command must be 'materialize', got '{v}'")
        return v


class MaterializeResponse(BaseModel):
    """Result of a materialization request.

    Per contract: MaterializeResponse in worker-ipc.yaml.
    """

    command: Literal["materialize_result"] = Field(..., description="Message type discriminator")
    ok: bool = Field(..., description="True if materialization succeeded")
    ordinal: int | None = Field(None, description="Corresponds to the ordinal in the request")
    path: str | None = Field(None, description="File path of materialized artifact (when ok=true)")
    error: dict[str, Any] | None = Field(None, description="Error details (when ok=false)")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'materialize_result'."""
        if v != "materialize_result":
            raise ValueError(f"MaterializeResponse command must be 'materialize_result', got '{v}'")
        return v


# ============================================================================
# Evict Messages (T009)
# ============================================================================


class EvictRequest(BaseModel):
    """Request to remove an artifact from the worker's memory.

    Per contract: EvictRequest in worker-ipc.yaml.
    """

    command: Literal["evict"] = Field(..., description="Message type discriminator")
    ref_id: str = Field(..., description="mem:// artifact to evict from memory")
    ordinal: int | None = Field(None, description="Request sequence number for correlation")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'evict'."""
        if v != "evict":
            raise ValueError(f"EvictRequest command must be 'evict', got '{v}'")
        return v


class EvictResponse(BaseModel):
    """Result of an eviction request.

    Per contract: EvictResponse in worker-ipc.yaml.
    """

    command: Literal["evict_result"] = Field(..., description="Message type discriminator")
    ok: bool = Field(..., description="True if eviction succeeded")
    ordinal: int | None = Field(None, description="Corresponds to the ordinal in the request")
    error: dict[str, Any] | None = Field(None, description="Error details (when ok=false)")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'evict_result'."""
        if v != "evict_result":
            raise ValueError(f"EvictResponse command must be 'evict_result', got '{v}'")
        return v


# ============================================================================
# Shutdown Messages (T009)
# ============================================================================


class ShutdownRequest(BaseModel):
    """Request to terminate the worker process.

    Per contract: ShutdownRequest in worker-ipc.yaml.
    """

    command: Literal["shutdown"] = Field(..., description="Message type discriminator")
    graceful: bool = Field(True, description="If true, complete in-flight operations first")
    ordinal: int | None = Field(None, description="Request sequence number for correlation")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'shutdown'."""
        if v != "shutdown":
            raise ValueError(f"ShutdownRequest command must be 'shutdown', got '{v}'")
        return v


class ShutdownResponse(BaseModel):
    """Acknowledgment of shutdown request.

    Per contract: ShutdownResponse in worker-ipc.yaml.
    """

    command: Literal["shutdown_ack"] = Field(..., description="Message type discriminator")
    ok: bool = Field(..., description="True if shutdown acknowledged")
    ordinal: int | None = Field(None, description="Corresponds to the ordinal in the request")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is exactly 'shutdown_ack'."""
        if v != "shutdown_ack":
            raise ValueError(f"ShutdownResponse command must be 'shutdown_ack', got '{v}'")
        return v


# ============================================================================
# NDJSON Framing Helpers (T010)
# ============================================================================


def encode_message(msg: BaseModel) -> str:
    """Serialize a Pydantic message model to NDJSON format.

    Args:
        msg: Pydantic model instance to encode

    Returns:
        JSON string with trailing newline (NDJSON format)

    Example:
        >>> req = ExecuteRequest(command="execute", fn_id="base.sum", ...)
        >>> line = encode_message(req)
        >>> assert line.endswith("\\n")
    """
    json_str = msg.model_dump_json()
    return json_str + "\n"


def decode_message(line: str) -> dict[str, Any]:
    """Parse a NDJSON line into a Python dictionary.

    Args:
        line: NDJSON string (JSON with optional trailing newline)

    Returns:
        Parsed dictionary

    Raises:
        json.JSONDecodeError: If the line is not valid JSON

    Example:
        >>> line = '{"command": "execute_result", "ok": true}\\n'
        >>> msg = decode_message(line)
        >>> assert msg["ok"] is True
    """
    # Strip trailing newline(s) and parse
    stripped = line.rstrip("\r\n")
    return json.loads(stripped)
