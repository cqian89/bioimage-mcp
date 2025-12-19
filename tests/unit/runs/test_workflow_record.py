"""Unit test for WorkflowRecord model serialization (T041).

Validates that WorkflowRecord can be serialized to JSON and
deserialized back correctly for persistence and replay.
"""

from __future__ import annotations

import json

from bioimage_mcp.runs.models import WorkflowRecord


class TestWorkflowRecordSerialization:
    """Unit tests for WorkflowRecord serialization."""

    def test_serialize_to_json(self) -> None:
        """Test that WorkflowRecord serializes to valid JSON."""
        record = WorkflowRecord(
            schema_version="0.1",
            run_id="run-123",
            created_at="2024-01-01T00:00:00Z",
            workflow_spec={"steps": [{"fn_id": "test.fn", "inputs": {}, "params": {}}]},
            inputs={"image": {"ref_id": "img-001"}},
            params={"diameter": 30.0},
            outputs={"labels": {"ref_id": "lbl-001"}},
            provenance={"fn_id": "test.fn"},
        )

        # Serialize to JSON
        json_str = record.model_dump_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "0.1"
        assert parsed["run_id"] == "run-123"

    def test_deserialize_from_json(self) -> None:
        """Test that WorkflowRecord deserializes from JSON."""
        json_data = {
            "schema_version": "0.1",
            "run_id": "run-456",
            "created_at": "2024-01-02T00:00:00Z",
            "workflow_spec": {"steps": []},
            "inputs": {},
            "params": {},
            "outputs": {},
            "provenance": {},
        }

        record = WorkflowRecord(**json_data)
        assert record.run_id == "run-456"
        assert record.schema_version == "0.1"

    def test_roundtrip_serialization(self) -> None:
        """Test that serialize->deserialize produces equivalent object."""
        original = WorkflowRecord(
            schema_version="0.1",
            run_id="run-roundtrip",
            created_at="2024-01-01T12:00:00Z",
            workflow_spec={
                "steps": [
                    {
                        "fn_id": "cellpose.segment",
                        "inputs": {"image": {"type": "BioImageRef"}},
                        "params": {"diameter": 30.0, "flow_threshold": 0.4},
                    }
                ]
            },
            inputs={"image": {"ref_id": "img-001", "type": "BioImageRef"}},
            params={"diameter": 30.0},
            outputs={
                "labels": {"ref_id": "lbl-001", "type": "LabelImageRef"},
                "workflow_record": {"ref_id": "wr-001", "type": "NativeOutputRef"},
            },
            provenance={"fn_id": "cellpose.segment", "tool_version": "4.0.1"},
            tool_manifests=[{"tool_id": "tools.cellpose", "tool_version": "4.0.1"}],
            env_fingerprint={"python_version": "3.13", "platform": "linux-64"},
        )

        # Roundtrip
        json_str = original.model_dump_json()
        restored = WorkflowRecord.model_validate_json(json_str)

        # Verify all fields match
        assert restored.run_id == original.run_id
        assert restored.schema_version == original.schema_version
        assert restored.workflow_spec == original.workflow_spec
        assert restored.inputs == original.inputs
        assert restored.params == original.params
        assert restored.outputs == original.outputs
        assert restored.provenance == original.provenance
        assert restored.tool_manifests == original.tool_manifests
        assert restored.env_fingerprint == original.env_fingerprint

    def test_optional_fields_default(self) -> None:
        """Test that optional fields have correct defaults."""
        record = WorkflowRecord(
            run_id="run-minimal",
            created_at="2024-01-01T00:00:00Z",
            workflow_spec={"steps": []},
            inputs={},
            params={},
        )

        assert record.schema_version == "0.1"  # default
        assert record.outputs == {}
        assert record.provenance == {}
        assert record.tool_manifests is None
        assert record.env_fingerprint is None
        assert record.replayed_from_run_id is None

    def test_replay_fields_serialization(self) -> None:
        """Test serialization of replay-related fields."""
        record = WorkflowRecord(
            run_id="run-replay",
            created_at="2024-01-01T00:00:00Z",
            workflow_spec={"steps": []},
            inputs={},
            params={},
            replayed_from_run_id="run-original",
        )

        json_data = json.loads(record.model_dump_json())
        assert json_data["replayed_from_run_id"] == "run-original"

        restored = WorkflowRecord.model_validate_json(record.model_dump_json())
        assert restored.replayed_from_run_id == "run-original"

    def test_model_dump_dict(self) -> None:
        """Test that model_dump returns a dict."""
        record = WorkflowRecord(
            run_id="run-dict",
            created_at="2024-01-01T00:00:00Z",
            workflow_spec={"steps": []},
            inputs={},
            params={},
        )

        dump = record.model_dump()
        assert isinstance(dump, dict)
        assert dump["run_id"] == "run-dict"
