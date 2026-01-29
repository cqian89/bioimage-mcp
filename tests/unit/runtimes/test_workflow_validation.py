"""Unit test for workflow compatibility validation (T016).

Tests the validate_workflow_compatibility function that checks I/O type
matching between workflow steps before execution (FR-006).
"""

from __future__ import annotations

import pytest

from bioimage_mcp.runtimes.protocol import (
    validate_workflow_compatibility,
)


class TestWorkflowValidation:
    """Unit tests for workflow I/O compatibility validation."""

    def test_valid_single_step_workflow(self) -> None:
        """Test that a valid single-step workflow passes validation."""
        workflow_spec = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {
                        "x": {
                            "type": "BioImageRef",
                            "format": "OME-TIFF",
                        }
                    },
                    "params": {"diameter": 30.0},
                }
            ]
        }

        function_ports = {
            "cellpose.models.CellposeModel.eval": {
                "inputs": [{"name": "x", "artifact_type": "BioImageRef", "required": True}],
                "outputs": [
                    {"name": "labels", "artifact_type": "LabelImageRef", "format": "OME-TIFF"}
                ],
            }
        }

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

    def test_mismatched_input_type_fails(self) -> None:
        """Test that mismatched input types are rejected."""
        workflow_spec = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {
                        "x": {
                            "type": "LogRef",  # Wrong type!
                            "format": "text",
                        }
                    },
                    "params": {},
                }
            ]
        }

        function_ports = {
            "cellpose.models.CellposeModel.eval": {
                "inputs": [{"name": "x", "artifact_type": "BioImageRef", "required": True}],
                "outputs": [],
            }
        }

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) > 0, "Should have validation errors"
        assert any(err.port_name == "x" for err in errors), "Error should reference the 'x' port"

    @pytest.mark.xfail(reason="Required input validation not yet implemented in v0.1")
    def test_missing_required_input_fails(self) -> None:
        """Test that missing required inputs are caught."""
        workflow_spec = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {},  # Missing required 'image' input
                    "params": {},
                }
            ]
        }

        function_ports = {
            "cellpose.models.CellposeModel.eval": {
                "inputs": [{"name": "x", "artifact_type": "BioImageRef", "required": True}],
                "outputs": [],
            }
        }

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) > 0, "Should have validation errors for missing input"
        assert any("x" in err.message or err.port_name == "x" for err in errors), (
            "Error should reference the missing 'x' input"
        )

    @pytest.mark.xfail(reason="Unknown fn_id validation not yet implemented in v0.1")
    def test_unknown_fn_id_fails(self) -> None:
        """Test that unknown function IDs are caught."""
        workflow_spec = {
            "steps": [
                {
                    "id": "unknown.function",
                    "inputs": {},
                    "params": {},
                }
            ]
        }

        function_ports = {}  # No known functions

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) > 0, "Should have validation errors for unknown function"

    def test_optional_input_not_required(self) -> None:
        """Test that optional inputs don't cause errors when missing."""
        workflow_spec = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {"x": {"type": "BioImageRef"}},
                    "params": {},
                }
            ]
        }

        function_ports = {
            "cellpose.models.CellposeModel.eval": {
                "inputs": [
                    {"name": "x", "artifact_type": "BioImageRef", "required": True},
                    {"name": "mask", "artifact_type": "LabelImageRef", "required": False},
                ],
                "outputs": [],
            }
        }

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) == 0, "Optional inputs should not cause errors"

    def test_empty_workflow_valid(self) -> None:
        """Test that empty workflow is valid (no steps to validate)."""
        workflow_spec = {"steps": []}
        function_ports = {}

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) == 0, "Empty workflow should be valid"

    def test_compatibility_error_has_details(self) -> None:
        """Test that compatibility errors include helpful details."""
        workflow_spec = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {
                        "x": {"type": "LogRef"}  # Wrong type
                    },
                    "params": {},
                }
            ]
        }

        function_ports = {
            "cellpose.models.CellposeModel.eval": {
                "inputs": [{"name": "x", "artifact_type": "BioImageRef", "required": True}],
                "outputs": [],
            }
        }

        errors = validate_workflow_compatibility(workflow_spec, function_ports)
        assert len(errors) > 0

        error = errors[0]
        assert hasattr(error, "step_index"), "Error should have step_index"
        assert hasattr(error, "port_name"), "Error should have port_name"
        assert hasattr(error, "message"), "Error should have message"
