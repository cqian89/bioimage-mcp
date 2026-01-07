from __future__ import annotations

import pytest
from bioimage_mcp.api.schemas import StructuredError, ErrorDetail
from bioimage_mcp.api.errors import (
    EXECUTION_FAILED,
    NOT_FOUND,
    # ARTIFACT_NOT_FOUND,  # This will fail if not defined
    execution_error,
    not_found_error,
    # artifact_not_found_error,  # This will fail if not defined
)

# For now, we'll try to import them and if it fails, we know the implementation is missing
try:
    from bioimage_mcp.api.errors import ARTIFACT_NOT_FOUND, artifact_not_found_error
except ImportError:
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"

    def artifact_not_found_error(*args, **kwargs):
        raise NotImplementedError("artifact_not_found_error not implemented")


class TestStructuredErrors:
    """T050: Unit tests validating structured error shape."""

    def test_structured_error_shape(self):
        """Verify that StructuredError has required fields and details."""
        error = StructuredError(
            code="SOME_CODE",
            message="Some message",
            details=[ErrorDetail(path="inputs.model", hint="Try re-instantiating")],
        )

        data = error.model_dump()
        assert "code" in data
        assert "message" in data
        assert "details" in data
        assert isinstance(data["details"], list)
        assert data["details"][0]["path"] == "inputs.model"
        assert data["details"][0]["hint"] == "Try re-instantiating"

    def test_incompatible_device_error(self):
        """T050: Test structured error for incompatible device (GPU->CPU)."""
        # This simulates the error we want when a GPU model is loaded on CPU without map_location
        err = execution_error(
            message="Cannot load GPU model on CPU-only environment",
            path="inputs.model",
            hint="Set gpu=False in params or use a worker with GPU support",
        )

        assert err.code == EXECUTION_FAILED
        assert err.details[0].path == "inputs.model"
        assert "gpu=False" in err.details[0].hint


class TestArtifactErrors:
    """T054: Tests for missing ObjectRef artifacts."""

    def test_missing_object_ref_error(self):
        """T054: Test that missing ObjectRef returns ArtifactNotFoundError code."""
        # Use the expected helper function
        error = artifact_not_found_error(
            message="ObjectRef not found in cache",
            path="inputs.model",
            hint="Object may have been evicted or session expired",
        )

        assert error.code == ARTIFACT_NOT_FOUND
        assert error.details[0].path == "inputs.model"
        assert "evicted" in error.details[0].hint
