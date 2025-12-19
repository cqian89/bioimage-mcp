from __future__ import annotations

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
