from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


class XarrayAdapterForRegistry(BaseAdapter):
    """Adapter for xarray operations that satisfies the BaseAdapter protocol."""

    def __init__(self) -> None:
        from bioimage_mcp.registry.dynamic.xarray_adapter import XarrayAdapter

        self.core = XarrayAdapter()

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Xarray functions are currently defined statically in manifest."""
        return []

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Most xarray operations we expose are image-to-image."""
        return IOPattern.IMAGE_TO_IMAGE

    def _normalize_inputs(self, inputs: list[Artifact]) -> list[tuple[str, Artifact]]:
        normalized: list[tuple[str, Artifact]] = []
        for idx, item in enumerate(inputs):
            if isinstance(item, tuple) and len(item) == 2:
                name, artifact = item
            else:
                name = "image" if idx == 0 else f"input_{idx}"
                artifact = item
            normalized.append((str(name), artifact))
        return normalized

    def _load_image(self, artifact: Artifact):
        """Load image data from artifact reference using BioImage."""
        if isinstance(artifact, dict):
            uri = artifact.get("uri") or artifact.get("path")
            metadata = artifact.get("metadata") or {}
            fmt = artifact.get("format")
        else:
            uri = getattr(artifact, "uri", None) or getattr(artifact, "path", None)
            metadata = getattr(artifact, "metadata", {}) or {}
            fmt = getattr(artifact, "format", None)

        if not uri:
            raise ValueError("Artifact missing URI or path")

        # Handle mem:// URIs by checking metadata for _simulated_path
        if str(uri).startswith("mem://"):
            path = metadata.get("_simulated_path")
            if not path:
                raise ValueError(
                    f"Cannot load mem:// URI without _simulated_path in metadata: {uri}"
                )
        else:
            parsed = urlparse(str(uri))
            path = parsed.path
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]

        from bioio import BioImage

        reader = None
        if fmt == "OME-TIFF":
            from bioio_ome_tiff import Reader as OmeTiffReader

            reader = OmeTiffReader
        elif fmt == "OME-Zarr":
            from bioio_ome_zarr import Reader as OmeZarrReader

            reader = OmeZarrReader

        return BioImage(str(path), reader=reader)

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute xarray function."""
        # fn_id is like "xarray.rename"
        parts = fn_id.split(".")
        method_name = parts[-1]

        # Normalize inputs and get the first one as primary image
        normalized_inputs = self._normalize_inputs(inputs)
        if not normalized_inputs:
            raise ValueError(f"No inputs provided for {fn_id}")

        _, primary_artifact = normalized_inputs[0]
        img = self._load_image(primary_artifact)

        # Get xarray data
        da = img.xarray_data

        # Execute via core adapter
        result_da = self.core.execute(method_name, da, **params)

        # Save result
        if work_dir is None:
            work_dir = Path(tempfile.gettempdir())

        work_dir.mkdir(parents=True, exist_ok=True)
        out_path = work_dir / f"output_{method_name}.ome.tiff"

        # Ensure result is 5D for OmeTiffWriter
        data = result_da.values
        if data.dtype == np.uint64 or data.dtype == np.int64:
            data = data.astype(np.float32)

        while data.ndim < 5:
            data = data[np.newaxis, ...]

        # Determine output dim order from result_da.dims
        dim_order = "".join(result_da.dims)
        # Pad dim_order to 5D if needed (standard is TCZYX)
        if len(dim_order) < 5:
            # Calculate how many dimensions are missing
            missing_count = 5 - len(dim_order)
            # Add missing dimensions from standard order (T, C, Z, Y, X)
            # Only the first three (T, C, Z) can be missing since Y and X are always present
            standard_prefix = "TCZ"
            existing = set(dim_order)
            missing = [d for d in standard_prefix if d not in existing][:missing_count]
            # Prepend missing dimensions in standard order
            dim_order = "".join(missing) + dim_order

        # Save using OmeTiffWriter (Constitution III requirement)
        try:
            from bioio.writers import OmeTiffWriter

            OmeTiffWriter.save(data, str(out_path), dim_order=dim_order)
        except Exception as e:
            raise RuntimeError(
                f"Failed to save OME-TIFF with bioio.writers.OmeTiffWriter: {e}. "
                "Ensure data is 5D (TCZYX) with valid dim_order."
            ) from e

        # Return artifact reference
        return [
            {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path.absolute()),
                "metadata": {
                    "axes": dim_order,
                    "shape": list(data.shape),
                    "dtype": str(data.dtype),
                },
            }
        ]

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        return None
