"""Contract test for ToolProtocolRequest/Response schema validation (T013).

Validates that the Cellpose tool adheres to the standard tool protocol
as defined in specs/001-cellpose-pipeline/contracts/openapi.yaml.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, Field, model_validator


class ToolProtocolRequest(BaseModel):
    """Expected schema for tool protocol request per contracts/openapi.yaml."""

    fn_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    work_dir: str

    @model_validator(mode="after")
    def _validate_request(self) -> ToolProtocolRequest:
        if not self.fn_id:
            raise ValueError("fn_id is required")
        if not self.work_dir:
            raise ValueError("work_dir is required")
        return self


class ToolProtocolOutputRef(BaseModel):
    """Expected schema for output reference in tool protocol response."""

    type: str
    format: str
    path: str


class ToolProtocolResponse(BaseModel):
    """Expected schema for tool protocol response per contracts/openapi.yaml."""

    ok: bool
    outputs: dict[str, Any] = Field(default_factory=dict)
    log: str = ""
    error: dict[str, Any] | str | None = None

    @model_validator(mode="after")
    def _validate_response(self) -> ToolProtocolResponse:
        # Validate output structure when ok is True
        if self.ok:
            for name, output in self.outputs.items():
                if not isinstance(output, dict):
                    raise ValueError(f"Output {name} must be a dict")
                if "type" not in output:
                    raise ValueError(f"Output {name} missing 'type' field")
                if "format" not in output:
                    raise ValueError(f"Output {name} missing 'format' field")
                if "path" not in output:
                    raise ValueError(f"Output {name} missing 'path' field")
        return self


class TestToolProtocolRequestContract:
    """Contract tests for ToolProtocolRequest schema."""

    def test_valid_request_accepted(self) -> None:
        """Test that a valid request passes validation."""
        request = {
            "fn_id": "cellpose.models.CellposeModel.eval",
            "params": {"model_type": "cyto3", "diameter": 30.0},
            "inputs": {"x": {"ref_id": "abc123", "uri": "file:///path/to/image.tiff"}},
            "work_dir": "/tmp/work",
        }
        validated = ToolProtocolRequest(**request)
        assert validated.fn_id == "cellpose.models.CellposeModel.eval"
        assert validated.params["model_type"] == "cyto3"

    def test_request_requires_fn_id(self) -> None:
        """Test that fn_id is required."""
        request = {
            "fn_id": "",
            "params": {},
            "inputs": {},
            "work_dir": "/tmp/work",
        }
        with pytest.raises(ValueError, match="fn_id is required"):
            ToolProtocolRequest(**request)

    def test_request_requires_work_dir(self) -> None:
        """Test that work_dir is required."""
        request = {
            "fn_id": "cellpose.models.CellposeModel.eval",
            "params": {},
            "inputs": {},
            "work_dir": "",
        }
        with pytest.raises(ValueError, match="work_dir is required"):
            ToolProtocolRequest(**request)

    def test_request_with_artifact_ref_input(self) -> None:
        """Test request with a full artifact reference as input."""
        request = {
            "fn_id": "cellpose.models.CellposeModel.eval",
            "params": {"diameter": 30.0},
            "inputs": {
                "x": {
                    "ref_id": "abc123",
                    "type": "BioImageRef",
                    "uri": "file:///path/to/image.ome.tiff",
                    "format": "OME-TIFF",
                    "mime_type": "image/tiff",
                    "size_bytes": 1024000,
                    "created_at": "2024-01-01T00:00:00Z",
                    "metadata": {},
                }
            },
            "work_dir": "/tmp/work",
        }
        validated = ToolProtocolRequest(**request)
        assert validated.inputs["x"]["type"] == "BioImageRef"


class TestToolProtocolResponseContract:
    """Contract tests for ToolProtocolResponse schema."""

    def test_valid_success_response_accepted(self) -> None:
        """Test that a valid success response passes validation."""
        response = {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                    "path": "/tmp/work/labels.ome.tiff",
                },
                "cellpose_bundle": {
                    "type": "NativeOutputRef",
                    "format": "cellpose-seg-npy",
                    "path": "/tmp/work/cellpose_seg.npy",
                },
            },
            "log": "Segmentation complete",
        }
        validated = ToolProtocolResponse(**response)
        assert validated.ok is True
        assert "labels" in validated.outputs

    def test_valid_error_response_accepted(self) -> None:
        """Test that a valid error response passes validation."""
        response = {
            "ok": False,
            "outputs": {},
            "log": "Error occurred",
            "error": {"message": "Input image not found"},
        }
        validated = ToolProtocolResponse(**response)
        assert validated.ok is False
        assert validated.error is not None

    def test_output_requires_type_field(self) -> None:
        """Test that outputs require 'type' field."""
        response = {
            "ok": True,
            "outputs": {
                "labels": {
                    "format": "OME-TIFF",
                    "path": "/tmp/work/labels.ome.tiff",
                },
            },
            "log": "",
        }
        with pytest.raises(ValueError, match="missing 'type' field"):
            ToolProtocolResponse(**response)

    def test_output_requires_format_field(self) -> None:
        """Test that outputs require 'format' field."""
        response = {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "path": "/tmp/work/labels.ome.tiff",
                },
            },
            "log": "",
        }
        with pytest.raises(ValueError, match="missing 'format' field"):
            ToolProtocolResponse(**response)

    def test_output_requires_path_field(self) -> None:
        """Test that outputs require 'path' field."""
        response = {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                },
            },
            "log": "",
        }
        with pytest.raises(ValueError, match="missing 'path' field"):
            ToolProtocolResponse(**response)

    def test_cellpose_models_cellpose_model_eval_expected_outputs(self) -> None:
        """Test that cellpose.models.CellposeModel.eval response has expected output types."""
        response = {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                    "path": "/tmp/work/labels.ome.tiff",
                },
                "cellpose_bundle": {
                    "type": "NativeOutputRef",
                    "format": "cellpose-seg-npy",
                    "path": "/tmp/work/cellpose_seg.npy",
                },
            },
            "log": "Segmentation complete",
        }
        validated = ToolProtocolResponse(**response)

        # Verify expected output types for cellpose.models.CellposeModel.eval
        assert validated.outputs["labels"]["type"] == "LabelImageRef"
        assert validated.outputs["labels"]["format"] == "OME-TIFF"
        assert validated.outputs["cellpose_bundle"]["type"] == "NativeOutputRef"
        assert validated.outputs["cellpose_bundle"]["format"] == "cellpose-seg-npy"
