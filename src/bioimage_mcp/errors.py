from __future__ import annotations


class BioimageMcpError(Exception):
    """A user-facing error with a stable error code."""

    code: str = "BIOIMAGE_MCP_ERROR"

    def __init__(self, message: str, *, details: object | None = None):
        super().__init__(message)
        self.details = details


class DoctorError(BioimageMcpError):
    code = "DOCTOR_FAILED"


class RunError(BioimageMcpError):
    code = "RUN_FAILED"


class ArtifactStoreError(BioimageMcpError):
    code = "ARTIFACT_STORE_FAILED"


class ObjectRefExpiredError(BioimageMcpError):
    code = "OBJECT_REF_EXPIRED"


class InternalBioimageMcpError(Exception):
    """An unexpected error that indicates a bug."""

    code: str = "BIOIMAGE_MCP_INTERNAL_ERROR"
