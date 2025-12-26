"""Contract test for WorkflowRecord JSON schema (T025).

Validates that the WorkflowRecord schema follows the expected structure
for workflow replay per FR-004/FR-005.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, Field, model_validator


class WorkflowRecordSchema(BaseModel):
    """Expected schema for workflow record JSON artifact."""

    schema_version: str
    run_id: str
    created_at: str
    workflow_spec: dict[str, Any]
    inputs: dict[str, Any]
    params: dict[str, Any]
    outputs: dict[str, Any]
    provenance: dict[str, Any] = Field(default_factory=dict)

    # Optional fields for enhanced replay
    tool_manifests: list[dict[str, Any]] | None = None
    env_fingerprint: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_schema(self) -> WorkflowRecordSchema:
        if not self.schema_version:
            raise ValueError("schema_version is required")
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.workflow_spec:
            raise ValueError("workflow_spec is required")
        return self


class TestWorkflowRecordContract:
    """Contract tests for WorkflowRecord JSON schema."""

    def test_valid_workflow_record_accepted(self) -> None:
        """Test that a valid workflow record passes validation."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {
                "steps": [
                    {
                        "fn_id": "cellpose.segment",
                        "inputs": {"image": {"type": "BioImageRef"}},
                        "params": {"diameter": 30.0},
                    }
                ]
            },
            "inputs": {"image": {"ref_id": "img-001", "type": "BioImageRef"}},
            "params": {"diameter": 30.0},
            "outputs": {"labels": {"ref_id": "lbl-001", "type": "LabelImageRef"}},
            "provenance": {"fn_id": "cellpose.segment"},
        }

        validated = WorkflowRecordSchema(**record)
        assert validated.schema_version == "0.1"
        assert validated.run_id == "run-abc123"

    def test_requires_schema_version(self) -> None:
        """Test that schema_version is required."""
        record = {
            "schema_version": "",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": []},
            "inputs": {},
            "params": {},
            "outputs": {},
        }

        with pytest.raises(ValueError, match="schema_version is required"):
            WorkflowRecordSchema(**record)

    def test_requires_run_id(self) -> None:
        """Test that run_id is required."""
        record = {
            "schema_version": "0.1",
            "run_id": "",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": []},
            "inputs": {},
            "params": {},
            "outputs": {},
        }

        with pytest.raises(ValueError, match="run_id is required"):
            WorkflowRecordSchema(**record)

    def test_requires_workflow_spec(self) -> None:
        """Test that workflow_spec is required."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {},
            "inputs": {},
            "params": {},
            "outputs": {},
        }

        with pytest.raises(ValueError, match="workflow_spec is required"):
            WorkflowRecordSchema(**record)

    def test_optional_tool_manifests(self) -> None:
        """Test that tool_manifests is optional but validated when present."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": []},
            "inputs": {},
            "params": {},
            "outputs": {},
            "tool_manifests": [{"tool_id": "tools.cellpose", "tool_version": "4.0.1"}],
        }

        validated = WorkflowRecordSchema(**record)
        assert validated.tool_manifests is not None
        assert len(validated.tool_manifests) == 1

    def test_optional_env_fingerprint(self) -> None:
        """Test that env_fingerprint is optional but validated when present."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": []},
            "inputs": {},
            "params": {},
            "outputs": {},
            "env_fingerprint": {
                "python_version": "3.13",
                "env_id": "bioimage-mcp-cellpose",
                "platform": "linux-64",
            },
        }

        validated = WorkflowRecordSchema(**record)
        assert validated.env_fingerprint is not None
        assert validated.env_fingerprint["python_version"] == "3.13"

    def test_workflow_spec_contains_steps(self) -> None:
        """Test that workflow_spec should contain steps array."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
            "inputs": {},
            "params": {},
            "outputs": {},
        }

        validated = WorkflowRecordSchema(**record)
        assert "steps" in validated.workflow_spec
        assert len(validated.workflow_spec["steps"]) == 1

    def test_outputs_contain_artifact_refs(self) -> None:
        """Test that outputs contain valid artifact reference structures."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": [{"fn_id": "test", "inputs": {}, "params": {}}]},
            "inputs": {},
            "params": {},
            "outputs": {
                "labels": {
                    "ref_id": "lbl-001",
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                    "uri": "file:///artifacts/objects/lbl-001",
                },
                "workflow_record": {
                    "ref_id": "wr-001",
                    "type": "NativeOutputRef",
                    "format": "workflow-record-json",
                },
            },
        }

        validated = WorkflowRecordSchema(**record)
        assert "labels" in validated.outputs
        assert validated.outputs["labels"]["type"] == "LabelImageRef"

    def test_provenance_has_fn_id(self) -> None:
        """Test that provenance tracks function used."""
        record = {
            "schema_version": "0.1",
            "run_id": "run-abc123",
            "created_at": "2024-01-01T00:00:00Z",
            "workflow_spec": {"steps": [{"fn_id": "cellpose.segment"}]},
            "inputs": {},
            "params": {},
            "outputs": {},
            "provenance": {
                "fn_id": "cellpose.segment",
                "tool_version": "4.0.1",
            },
        }

        validated = WorkflowRecordSchema(**record)
        assert validated.provenance["fn_id"] == "cellpose.segment"
