from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


def should_expand_to_5d(output_format: str, output_hints: DimensionRequirement | None) -> bool:
    """Decide if an output should be expanded to 5D TCZYX based on format and hints.

    OME-TIFF always requires 5D in bioio.writers.
    """
    if output_format.upper() == "OME-TIFF":
        return True
    if output_hints and output_hints.min_ndim == 5:
        return True
    return False


def expand_if_required(
    data: np.ndarray, dims: str, requirement: DimensionRequirement | None
) -> tuple[np.ndarray, str]:
    """Expand to 5D only if tool manifest requires it."""
    if requirement and requirement.min_ndim == 5 and data.ndim < 5:
        missing = "TCZYX"[: 5 - data.ndim]
        for _ in missing:
            data = np.expand_dims(data, axis=0)
        dims = missing + dims
    return data, dims


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
            uri = artifact.get("uri")
            path = artifact.get("path")
            metadata = artifact.get("metadata") or {}
            fmt = artifact.get("format")
        else:
            uri = getattr(artifact, "uri", None)
            path = getattr(artifact, "path", None)
            metadata = getattr(artifact, "metadata", {}) or {}
            fmt = getattr(artifact, "format", None)

        if not uri and not path:
            raise ValueError(f"Artifact missing URI or path. Artifact data: {artifact}")

        if uri and str(uri).startswith("mem://"):
            # Handle mem:// URIs by checking metadata for _simulated_path
            path = metadata.get("_simulated_path")
            if not path:
                raise ValueError(
                    f"Cannot load mem:// URI without _simulated_path in metadata: {uri}"
                )
        elif uri:
            parsed = urlparse(str(uri))
            path = unquote(parsed.path)
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
        else:
            # Only path is present
            path = str(Path(path).absolute())

        from bioio import BioImage

        reader = None
        if fmt == "OME-TIFF":
            try:
                from bioio_ome_tiff import Reader as OmeTiffReader

                reader = OmeTiffReader
            except ImportError:
                pass
        elif fmt == "TIFF":
            try:
                from bioio_tifffile import Reader as TiffReader

                reader = TiffReader
            except ImportError:
                pass
        elif fmt == "OME-Zarr":
            try:
                from bioio_ome_zarr import Reader as OmeZarrReader

                reader = OmeZarrReader
            except ImportError:
                pass

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
        # Filter out metadata entries
        normalized_inputs = [
            (name, art)
            for name, art in normalized_inputs
            if not (isinstance(art, str) and (" " in art or len(art) > 64))
        ]
        if not normalized_inputs:
            raise ValueError(f"No valid artifact inputs provided for {fn_id}")

        _, primary_artifact = normalized_inputs[0]
        img = self._load_image(primary_artifact)

        # Get xarray data (native dimensions - T017)
        da = img.reader.xarray_data

        # Execute via core adapter
        result_da = self.core.execute(method_name, da, **params)

        # Save result (T018)
        return self._save_output(result_da, method_name, work_dir)

    def _save_output(
        self, result_da: Any, method_name: str, work_dir: Path | None = None
    ) -> list[dict]:
        """Save output DataArray with native dimensions (T018).

        Uses OME-TIFF if dimensions are compatible (ends in YX),
        otherwise falls back to OME-Zarr for native dimension support.
        """
        if work_dir is None:
            work_dir = Path(tempfile.gettempdir())

        work_dir.mkdir(parents=True, exist_ok=True)

        # Native dimensions (T018)
        data = result_da.values
        dim_order = "".join(result_da.dims)

        if data.dtype == np.uint64 or data.dtype == np.int64:
            data = data.astype(np.float32)

        # Determine if OME-TIFF is compatible
        # OmeTiffWriter requires 2-5D and must end in YX (or YXS)
        is_ome_tiff_compatible = dim_order.endswith("YX") and 2 <= data.ndim <= 5

        if is_ome_tiff_compatible:
            ext = ".ome.tiff"
            fmt = "OME-TIFF"
            out_path = work_dir / f"output_{method_name}{ext}"
            try:
                from bioio.writers import OmeTiffWriter

                OmeTiffWriter.save(data, str(out_path), dim_order=dim_order)
            except Exception:
                # Fallback to OME-Zarr if OME-TIFF save fails
                is_ome_tiff_compatible = False

        if not is_ome_tiff_compatible:
            ext = ".ome.zarr"
            fmt = "OME-Zarr"
            out_path = work_dir / f"output_{method_name}{ext}"
            save_native_ome_zarr(data, out_path, dim_order)

        # Populate native dimension metadata
        metadata = {
            "axes": dim_order,
            "shape": list(data.shape),
            "ndim": data.ndim,
            "dims": list(dim_order),
            "dtype": str(data.dtype),
        }

        # Return artifact reference
        return [
            {
                "type": "BioImageRef",
                "format": fmt,
                "uri": out_path.absolute().as_uri(),
                "path": str(out_path.absolute()),
                "metadata": metadata,
            }
        ]

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        return None


def save_native_ome_zarr(data: np.ndarray, path: Path | str, dims: str) -> None:
    """Save array to OME-Zarr with native dimensions (T019)."""
    from bioio_ome_zarr.writers import OMEZarrWriter

    axis_type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
    axes_names = [d.lower() for d in dims]
    axes_types = [axis_type_map.get(d.lower(), "space") for d in dims]

    writer = OMEZarrWriter(
        store=str(path),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
        zarr_format=2,
    )
    writer.write_full_volume(data)
