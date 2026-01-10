from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

# In-memory object cache for xarray DataArrays
OBJECT_CACHE: dict[str, Any] = {}


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
        from bioimage_mcp.registry.dynamic.xarray_allowlists import XARRAY_DATAARRAY_ALLOWLIST

        self.core = XarrayAdapter(allowlist=XARRAY_DATAARRAY_ALLOWLIST)

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Dynamically discover xarray functions from the new allowlists."""
        from bioimage_mcp.registry.dynamic.xarray_allowlists import (
            XARRAY_DATAARRAY_ALLOWLIST,
            XARRAY_DATAARRAY_CLASS,
            XARRAY_TOPLEVEL_ALLOWLIST,
            XARRAY_UFUNC_ALLOWLIST,
        )

        discovery: list[FunctionMetadata] = []

        # 1. Constructor: base.xarray.DataArray
        for name, info in XARRAY_DATAARRAY_CLASS.items():
            tags = set(info.get("tags", []))
            if "category" in info:
                tags.add(info["category"])

            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="xarray",
                    qualified_name=f"xarray.{name}",
                    fn_id=f"base.xarray.{name}",
                    source_adapter="xarray",
                    description=info.get("summary", ""),
                    tags=list(tags),
                    io_pattern=IOPattern.GENERIC,
                )
            )

        # 2. Top-level functions: base.xarray.<name>
        for name, info in XARRAY_TOPLEVEL_ALLOWLIST.items():
            tags = set(info.get("tags", []))
            if "category" in info:
                tags.add(info["category"])

            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="xarray",
                    qualified_name=f"xarray.{name}",
                    fn_id=f"base.xarray.{name}",
                    source_adapter="xarray",
                    description=info.get("summary", ""),
                    tags=list(tags),
                    io_pattern=IOPattern.IMAGE_TO_IMAGE,
                )
            )

        # 3. Ufuncs: base.xarray.ufuncs.<name>
        for name, info in XARRAY_UFUNC_ALLOWLIST.items():
            tags = set(info.get("tags", []))
            if "category" in info:
                tags.add(info["category"])

            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="xarray",
                    qualified_name=f"xarray.{name}",
                    fn_id=f"base.xarray.ufuncs.{name}",
                    source_adapter="xarray",
                    description=info.get("summary", ""),
                    tags=list(tags),
                    io_pattern=IOPattern.IMAGE_TO_IMAGE,
                )
            )

        # 4. DataArray methods: base.xarray.DataArray.<name>
        for name, info in XARRAY_DATAARRAY_ALLOWLIST.items():
            tags = set(info.get("tags", []))
            if "category" in info:
                tags.add(info["category"])

            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="xarray.DataArray",
                    qualified_name=f"xarray.DataArray.{name}",
                    fn_id=f"base.xarray.DataArray.{name}",
                    source_adapter="xarray",
                    description=info.get("summary", ""),
                    tags=list(tags),
                    io_pattern=IOPattern.IMAGE_TO_IMAGE,
                )
            )

        return discovery

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

    def _load_da(self, artifact: Artifact):
        """Load DataArray from artifact (BioImageRef or ObjectRef)."""
        # Handle ObjectRef input
        uri = artifact.get("uri") if isinstance(artifact, dict) else getattr(artifact, "uri", None)
        if uri and uri.startswith("obj://"):
            if uri not in OBJECT_CACHE:
                raise ValueError(f"Object with URI {uri} not found in memory cache")
            return OBJECT_CACHE[uri]
        else:
            img = self._load_image(artifact)
            # Get xarray data (native dimensions - T017)
            return img.reader.xarray_data

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute xarray function."""
        if fn_id in ["base.xarray.DataArray", "xarray.DataArray"]:
            return self._execute_dataarray_constructor(inputs, params, work_dir)

        if fn_id in ["base.xarray.DataArray.to_bioimage", "xarray.DataArray.to_bioimage"]:
            return self._execute_to_bioimage(inputs, params, work_dir)

        if fn_id.startswith("base.xarray.ufuncs.") or fn_id.startswith("xarray.ufuncs."):
            return self._execute_ufunc(fn_id, inputs, params, work_dir)

        # Check if it's a top-level function
        from bioimage_mcp.registry.dynamic.xarray_allowlists import XARRAY_TOPLEVEL_ALLOWLIST

        method_name = fn_id.split(".")[-1]
        if method_name in XARRAY_TOPLEVEL_ALLOWLIST:
            return self._execute_toplevel_function(fn_id, inputs, params, work_dir)

        # fn_id is like "base.xarray.isel" or "base.xarray.DataArray.mean"
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
        da = self._load_da(primary_artifact)

        # Handle ObjectRef input URI for return type determination
        uri = (
            primary_artifact.get("uri")
            if isinstance(primary_artifact, dict)
            else getattr(primary_artifact, "uri", None)
        )

        # Execute via core adapter
        result_da = self.core.execute(method_name, da, **params)

        # Determine if we should return an ObjectRef or BioImageRef.
        # We return ObjectRef if:
        # 1. The input was already an ObjectRef (implicit chaining)
        # 2. OR the function ID specifically belongs to the DataArray chaining API
        #    and the method is marked as returning ObjectRef.
        from bioimage_mcp.registry.dynamic.xarray_allowlists import XARRAY_DATAARRAY_ALLOWLIST

        method_info = XARRAY_DATAARRAY_ALLOWLIST.get(method_name)
        input_is_object = uri and uri.startswith("obj://")
        is_chaining_api = fn_id.startswith("base.xarray.DataArray.")

        if (
            (input_is_object or is_chaining_api)
            and method_info
            and method_info.get("returns") == "ObjectRef"
        ):
            artifact_id = str(uuid.uuid4())
            new_uri = f"obj://default/xarray/{artifact_id}"
            OBJECT_CACHE[new_uri] = result_da
            return [
                {
                    "ref_id": artifact_id,
                    "type": "ObjectRef",
                    "python_class": "xarray.DataArray",
                    "uri": new_uri,
                    "storage_type": "memory",
                    "metadata": {
                        "shape": list(result_da.shape),
                        "dims": list(result_da.dims),
                        "dtype": str(result_da.dtype),
                    },
                }
            ]

        # Save result (T018)
        return self._save_output(result_da, method_name, work_dir)

    def _execute_toplevel_function(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute top-level xarray functions (concat, merge, etc.)."""
        import xarray as xr

        method_name = fn_id.split(".")[-1]

        normalized = self._normalize_inputs(inputs)

        # Collect all DataArrays
        das = []
        for _name, art in normalized:
            if isinstance(art, list):
                # Handle inputs=[("images", [img1, img2])]
                for item in art:
                    das.append(self._load_da(item))
            else:
                # Handle inputs=[("image_0", img1), ("image_1", img2)]
                das.append(self._load_da(art))

        if not das:
            raise ValueError(f"No input DataArrays found for {fn_id}")

        func = getattr(xr, method_name)

        # Most top-level combining functions take the list of objects as the first argument
        if method_name == "merge":
            # Fix: rename to unique names and convert back to DataArray
            result_dataset = xr.merge(
                [arr.rename(f"var_{i}") for i, arr in enumerate(das)], **params
            )
            result_da = result_dataset.to_array(dim="variable")
        elif method_name in ["concat", "combine_by_coords", "combine_nested"]:
            result_da = func(das, **params)
        else:
            # For other top-level functions, we might need different dispatch
            # but for now we follow the pattern of passing all das
            result_da = func(*das, **params)

        return self._save_output(result_da, method_name, work_dir)

    def _execute_ufunc(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute universal functions (add, subtract, etc.)."""
        import xarray as xr

        method_name = fn_id.split(".")[-1]

        normalized = self._normalize_inputs(inputs)
        das = []
        for _name, art in normalized:
            # ufuncs usually don't take lists of images in one argument
            if isinstance(art, list):
                for item in art:
                    das.append(self._load_da(item))
            else:
                das.append(self._load_da(art))

        if not das:
            raise ValueError(f"No input DataArrays found for {fn_id}")

        # Use xr.apply_ufunc with the corresponding numpy function
        try:
            # Try to find it in xarray first (some are there like xr.where)
            if hasattr(xr, method_name):
                func = getattr(xr, method_name)
                result_da = func(*das, **params)
            else:
                # Fallback to numpy + apply_ufunc
                # apply_ufunc handles xarray-specific logic like coordinates
                func = getattr(np, method_name)
                result_da = xr.apply_ufunc(func, *das, kwargs=params)
        except AttributeError as err:
            raise ValueError(f"Ufunc '{method_name}' not found in xarray or numpy") from err

        # Determine if we should return an ObjectRef or BioImageRef.
        # We return ObjectRef if ANY input was an ObjectRef
        any_input_is_object = False
        for _name, art in normalized:
            if isinstance(art, list):
                for item in art:
                    uri = item.get("uri") if isinstance(item, dict) else getattr(item, "uri", None)
                    if uri and uri.startswith("obj://"):
                        any_input_is_object = True
                        break
            else:
                uri = art.get("uri") if isinstance(art, dict) else getattr(art, "uri", None)
                if uri and uri.startswith("obj://"):
                    any_input_is_object = True
            if any_input_is_object:
                break

        if any_input_is_object:
            artifact_id = str(uuid.uuid4())
            new_uri = f"obj://default/xarray/{artifact_id}"
            OBJECT_CACHE[new_uri] = result_da
            return [
                {
                    "ref_id": artifact_id,
                    "type": "ObjectRef",
                    "python_class": "xarray.DataArray",
                    "uri": new_uri,
                    "storage_type": "memory",
                    "metadata": {
                        "shape": list(result_da.shape),
                        "dims": list(result_da.dims),
                        "dtype": str(result_da.dtype),
                    },
                }
            ]

        return self._save_output(result_da, method_name, work_dir)

    def _execute_dataarray_constructor(
        self,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute base.xarray.DataArray constructor."""
        normalized = self._normalize_inputs(inputs)
        if not normalized:
            raise ValueError("No input artifact provided for DataArray constructor")

        _, artifact = normalized[0]
        img = self._load_image(artifact)
        da = img.reader.xarray_data

        artifact_id = str(uuid.uuid4())
        uri = f"obj://default/xarray/{artifact_id}"

        OBJECT_CACHE[uri] = da

        return [
            {
                "ref_id": artifact_id,
                "type": "ObjectRef",
                "python_class": "xarray.DataArray",
                "uri": uri,
                "storage_type": "memory",
                "metadata": {
                    "shape": list(da.shape),
                    "dims": list(da.dims),
                    "dtype": str(da.dtype),
                    "output_name": "da",
                },
            }
        ]

    def _execute_to_bioimage(
        self,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute base.xarray.DataArray.to_bioimage serializer."""
        normalized = self._normalize_inputs(inputs)
        if not normalized:
            raise ValueError("No input artifact provided for to_bioimage")

        _, artifact = normalized[0]

        # Handle both dict and object-like artifacts
        if isinstance(artifact, dict):
            uri = artifact.get("uri")
        else:
            uri = getattr(artifact, "uri", None)

        if not uri or not uri.startswith("obj://"):
            raise ValueError(f"Expected ObjectRef with obj:// URI, got {artifact}")

        if uri not in OBJECT_CACHE:
            raise ValueError(f"Object with URI {uri} not found in memory cache")

        da = OBJECT_CACHE[uri]
        return self._save_output(da, "to_bioimage", work_dir)

    def _save_output(
        self, result_da: Any, method_name: str, work_dir: Path | None = None
    ) -> list[dict]:
        """Save output DataArray with native dimensions (T018).

        Prefers OME-TIFF for maximum downstream compatibility (e.g., with Cellpose).
        Falls back to OME-Zarr only if OME-TIFF save fails.
        """
        if work_dir is None:
            work_dir = Path(tempfile.gettempdir())

        work_dir.mkdir(parents=True, exist_ok=True)

        # Native dimensions (T018)
        data = result_da.values
        dims = list(result_da.dims)

        # Ensure we can always persist BioImageRef outputs.
        # Some reductions can yield scalar/1D results (e.g., sum over X on a YX image),
        # but our image artifact writers require at least 2D.
        if data.ndim == 0:
            data = np.array([[data]])
            dims = ["Y", "X"]
        elif data.ndim == 1:
            if dims == ["Y"]:
                data = data[:, np.newaxis]
                dims = ["Y", "X"]
            elif dims == ["X"]:
                data = data[np.newaxis, :]
                dims = ["Y", "X"]
            else:
                data = data[..., np.newaxis]
                dims = dims + ["X"]

        if data.dtype == np.uint64 or data.dtype == np.int64:
            data = data.astype(np.float32)

        # Prefer OME-TIFF for maximum downstream compatibility
        # Expand to 5D if needed for OmeTiffWriter
        ome_tiff_success = False
        ext = ".ome.tiff"
        fmt = "OME-TIFF"
        out_path = work_dir / f"output_{method_name}{ext}"

        try:
            from bioio.writers import OmeTiffWriter

            # OME-TIFF only supports up to 5 dimensions and specific names
            # If any dimension name is multi-character, it's definitely not OME-TIFF compatible
            if len(dims) > 5 or any(len(d) > 1 for d in dims):
                raise ValueError("Incompatible with OME-TIFF")

            # OmeTiffWriter requires 5D TCZYX
            save_data = data
            save_dim_order = "".join(dims)

            # Expand to 5D for OmeTiffWriter
            while save_data.ndim < 5:
                save_data = np.expand_dims(save_data, axis=0)

            # Build 5D dim order: prepend missing dimensions from TCZYX
            missing_dims = "TCZYX"[: 5 - len(dims)]
            save_dim_order = missing_dims + save_dim_order

            OmeTiffWriter.save(save_data, str(out_path), dim_order=save_dim_order)
            ome_tiff_success = True
        except Exception:
            # Fallback to OME-Zarr if OME-TIFF save fails
            ome_tiff_success = False

        if not ome_tiff_success:
            ext = ".ome.zarr"
            fmt = "OME-Zarr"
            out_path = work_dir / f"output_{method_name}{ext}"
            save_native_ome_zarr(data, out_path, dims)

        # Populate native dimension metadata
        metadata = {
            "axes": "".join(dims) if all(len(d) == 1 for d in dims) else dims,
            "shape": list(data.shape),
            "ndim": data.ndim,
            "dims": list(dims),
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
        axes_units=[None] * data.ndim,
        physical_pixel_size=[1.0] * data.ndim,
        zarr_format=2,
    )
    writer.write_full_volume(data)
