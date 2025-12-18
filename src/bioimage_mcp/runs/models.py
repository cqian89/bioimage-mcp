from __future__ import annotations

from pydantic import BaseModel, Field


class Run(BaseModel):
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
