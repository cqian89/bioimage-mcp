"""Unit tests for Run model native_output_ref_id field (T007a).

Tests that the Run model exposes native_output_ref_id for linking
to workflow record artifacts.
"""

from __future__ import annotations

from bioimage_mcp.runs.models import Run


class TestRunNativeOutputRef:
    """Tests for Run.native_output_ref_id field."""

    def test_run_has_native_output_ref_id_field(self) -> None:
        """Test that Run model has native_output_ref_id field."""
        run = Run(
            run_id="test-run-1",
            status="succeeded",
            created_at="2025-01-01T00:00:00Z",
            workflow_spec={},
            inputs={},
            params={},
            log_ref_id="log-ref-1",
            native_output_ref_id="native-ref-1",
        )
        assert run.native_output_ref_id == "native-ref-1"

    def test_native_output_ref_id_optional(self) -> None:
        """Test that native_output_ref_id is optional."""
        run = Run(
            run_id="test-run-2",
            status="running",
            created_at="2025-01-01T00:00:00Z",
            workflow_spec={},
            inputs={},
            params={},
            log_ref_id="log-ref-2",
        )
        assert run.native_output_ref_id is None

    def test_run_serialization_includes_native_output_ref_id(self) -> None:
        """Test that native_output_ref_id is included in serialization."""
        run = Run(
            run_id="test-run-3",
            status="succeeded",
            created_at="2025-01-01T00:00:00Z",
            workflow_spec={"steps": []},
            inputs={"image": {"ref_id": "img-1"}},
            params={"model": "cyto3"},
            log_ref_id="log-ref-3",
            native_output_ref_id="workflow-record-1",
        )
        data = run.model_dump()
        assert "native_output_ref_id" in data
        assert data["native_output_ref_id"] == "workflow-record-1"
