from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import xarray as xr
from bioio.writers import OmeTiffWriter

from bioimage_mcp.artifacts.models import ArtifactRef


class ExportHandler:
    """Handler for exporting artifacts to file-backed formats."""

    def __init__(self, artifact_store_path: Path | None = None):
        self.artifact_store_path = artifact_store_path or Path.cwd() / ".bioimage-mcp" / "artifacts"

    def export_to_ome_tiff(
        self,
        data: xr.DataArray,
        session_id: str,
        source_ref_id: str,
        output_path: Path | str | None = None,
    ) -> ArtifactRef:
        """Export xarray data to OME-TIFF and return an artifact reference."""
        # Generate output path if not provided
        if output_path is None:
            self.artifact_store_path.mkdir(parents=True, exist_ok=True)
            output_path = self.artifact_store_path / session_id / f"{uuid.uuid4().hex}.ome.tiff"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get dimension order from xarray
        dim_order = "".join(data.dims)

        # Export using bioio
        OmeTiffWriter.save(data.values, output_path, dim_order=dim_order)

        # Create artifact reference
        return ArtifactRef(
            ref_id=f"export-{uuid.uuid4().hex[:8]}",
            type="BioImageRef",
            uri=f"file://{output_path.absolute()}",
            format="OME-TIFF",
            storage_type="file",
            mime_type="image/tiff",
            size_bytes=output_path.stat().st_size,
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "dims": list(data.dims),
                "shape": list(data.shape),
                "source_ref_id": source_ref_id,
            },
        )
