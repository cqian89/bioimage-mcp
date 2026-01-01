from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from bioimage_mcp.artifacts.models import ArtifactRef


class IOBridgeHandoff(BaseModel):
    """Provenance record of a format conversion or materialization."""

    source_ref_id: str
    target_ref_id: str
    source_env: str
    target_env: str
    negotiated_format: str  # e.g., "OME-TIFF"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IOBridge:
    """Handles cross-environment format negotiation and materialization.

    Current Architecture (Pre-1.0):
        - IOBridge coordinates handoff detection and format negotiation
        - Actual materialization is performed by core execution layer (execution.py)
        - Core uses bioio readers/writers directly for format conversion

    Future Architecture (Constitution III Compliant):
        - IOBridge should dispatch export calls to source environment's worker
        - Source environment performs materialization using its own bioio instance
        - Core receives file-backed artifact reference and dispatches to target environment

    This partial compliance is acceptable for pre-1.0 development but should be
    refactored before 1.0 release to fully satisfy Constitution III.

    See:
        - specs/011-wrapper-consolidation/plan.md Phase 2, Task T022
        - .specify/memory/constitution.md Constitution III (Artifact References Only)
    """

    DEFAULT_INTERCHANGE_FORMAT = "OME-TIFF"
    SUPPORTED_FORMATS = {"OME-TIFF", "OME-Zarr"}

    def __init__(self, artifact_store_path: Path | str | None = None):
        self.artifact_store_path = (
            Path(artifact_store_path)
            if artifact_store_path
            else Path.cwd() / ".bioimage-mcp" / "artifacts"
        )
        self._handoff_history: list[IOBridgeHandoff] = []
        self._lock = threading.Lock()

    def needs_handoff(
        self,
        source_artifact: ArtifactRef,
        source_env: str,
        target_env: str,
        target_required_format: str | None = None,
    ) -> bool:
        """Determine if cross-env handoff is needed."""
        # Handoff needed if:
        # 1. source_env != target_env (cross-env)
        # 2. source is mem:// (must materialize for cross-env)
        # 3. source format doesn't match target required format

        if source_env != target_env:
            return True

        if source_artifact.is_memory_artifact():
            return True

        if target_required_format and source_artifact.format != target_required_format:
            return True

        return False

    def negotiate_format(
        self, source_artifact: ArtifactRef, target_required_format: str | None = None
    ) -> str:
        """Negotiate the interchange format."""
        # Return target_required_format if specified and supported
        # Otherwise return DEFAULT_INTERCHANGE_FORMAT
        if target_required_format in self.SUPPORTED_FORMATS:
            return target_required_format

        return self.DEFAULT_INTERCHANGE_FORMAT

    def create_materialization_path(self, session_id: str, artifact_id: str, format: str) -> Path:
        """Generate a path for materializing an artifact to disk."""
        # Return: artifact_store_path / session_id / f"{artifact_id}.ome.tiff" (or .zarr)
        ext = ".ome.tiff" if format == "OME-TIFF" else ".zarr"
        return self.artifact_store_path / session_id / f"{artifact_id}{ext}"

    def record_handoff(
        self, source_ref_id: str, target_ref_id: str, source_env: str, target_env: str, format: str
    ) -> IOBridgeHandoff:
        """Record a handoff for provenance."""
        handoff = IOBridgeHandoff(
            source_ref_id=source_ref_id,
            target_ref_id=target_ref_id,
            source_env=source_env,
            target_env=target_env,
            negotiated_format=format,
        )
        with self._lock:
            self._handoff_history.append(handoff)
        return handoff

    def get_handoff_history(self) -> list[IOBridgeHandoff]:
        """Get all recorded handoffs."""
        with self._lock:
            return list(self._handoff_history)
