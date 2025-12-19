from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Run(BaseModel):
    """Represents a single workflow execution instance.

    Provides user-retrievable status, outputs, logs, and links to
    workflow record artifacts for replay.
    """

    run_id: str
    status: str

    created_at: str
    started_at: str | None = None
    ended_at: str | None = None

    workflow_spec: dict
    inputs: dict
    params: dict
    outputs: dict | None = None

    log_ref_id: str
    error: dict | None = None
    provenance: dict = Field(default_factory=dict)

    # Link to workflow record artifact (NativeOutputRef with format workflow-record-json)
    # Enables workflow replay per FR-004/FR-005
    native_output_ref_id: str | None = None


class WorkflowRecord(BaseModel):
    """Persisted workflow record for replay capability (FR-004/FR-005).

    This model defines the JSON schema for workflow-record-json artifacts
    that enable replay_workflow() functionality.

    Attributes:
        schema_version: Version of the workflow record schema
        run_id: Original run identifier
        created_at: ISO 8601 timestamp of original run creation
        workflow_spec: Complete workflow specification from original run
        inputs: Input artifact references used in original run
        params: Parameters passed to the workflow
        outputs: Output artifact references produced by the run
        provenance: Execution provenance metadata (fn_id, tool versions, etc.)
        tool_manifests: Optional list of tool manifest snapshots for version locking
        env_fingerprint: Optional environment fingerprint for reproducibility
        replayed_from_run_id: If this is a replay, the original run_id
    """

    schema_version: str = "0.1"
    run_id: str
    created_at: str

    workflow_spec: dict[str, Any]
    inputs: dict[str, Any]
    params: dict[str, Any]
    outputs: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

    # Optional fields for enhanced replay
    tool_manifests: list[dict[str, Any]] | None = None
    env_fingerprint: dict[str, Any] | None = None

    # For replayed runs, tracks lineage
    replayed_from_run_id: str | None = None

