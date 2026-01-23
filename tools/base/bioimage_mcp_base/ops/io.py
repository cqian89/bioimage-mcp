"""Bioimage I/O functions for base toolkit."""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd
from bioimage_mcp_base.utils import load_native_image, uri_to_path

logger = logging.getLogger(__name__)


class PathNotAllowedError(Exception):
    """Raised when path is outside allowed paths."""

    def __init__(self, path: str, allowed_paths: list[str], mode: str = "read"):
        self.path = path
        self.allowed_paths = allowed_paths
        self.mode = mode
        self.code = "PATH_NOT_ALLOWED"
        super().__init__(f"Path '{path}' is not allowed for {mode} (not in allowed {mode} paths)")


class FileNotFoundIOError(Exception):
    """Raised when file does not exist."""

    def __init__(self, path: str):
        self.path = path
        self.code = "FILE_NOT_FOUND"
        super().__init__(f"File not found: {path}")


class UnsupportedFormatError(Exception):
    """Raised when format is not supported."""

    def __init__(self, path: str, format_hint: str | None = None):
        self.path = path
        self.format_hint = format_hint
        self.code = "UNSUPPORTED_FORMAT"
        super().__init__(f"Unsupported format for: {path}")


class ValidationFailedError(Exception):
    """Raised when file validation fails."""

    def __init__(self, path: str, issues: list[str]):
        self.path = path
        self.issues = issues
        self.code = "VALIDATION_FAILED"
        super().__init__(f"Validation failed for: {path}")


class SliceOutOfBoundsError(Exception):
    """Raised when slice indices exceed array dimensions."""

    def __init__(self, dim: str, index: int, size: int):
        self.dim = dim
        self.index = index
        self.size = size
        self.code = "SLICE_OUT_OF_BOUNDS"
        super().__init__(f"Slice index {index} exceeds dimension {dim} size {size}")


def validate_read_path(path: str, allowed_paths: list[str] | None = None) -> Path:
    """Validate that path is within allowed read paths.

    Args:
        path: Path to validate
        allowed_paths: List of allowed path prefixes. If None, reads from environment.

    Returns:
        The resolved Path object.

    Raises:
        PathNotAllowedError: If path is not within any allowed path
    """
    if allowed_paths is None:
        allowed_paths = _get_allowed_read_paths()

    path_obj = Path(path).resolve()
    for allowed in allowed_paths:
        allowed_obj = Path(allowed).resolve()
        try:
            path_obj.relative_to(allowed_obj)
            return path_obj  # Path is within allowed path
        except ValueError:
            continue

    raise PathNotAllowedError(str(path_obj), allowed_paths, mode="read")


def validate_write_path(path: str, allowed_paths: list[str] | None = None) -> Path:
    """Validate that path is within allowed write paths.

    Args:
        path: Path to validate
        allowed_paths: List of allowed path prefixes. If None, reads from environment.

    Returns:
        The resolved Path object.

    Raises:
        PathNotAllowedError: If path is not within any allowed path
    """
    if allowed_paths is None:
        allowed_paths = _get_allowed_write_paths()

    path_obj = Path(path).resolve()
    for allowed in allowed_paths:
        allowed_obj = Path(allowed).resolve()
        try:
            path_obj.relative_to(allowed_obj)
            return path_obj
        except ValueError:
            continue

    raise PathNotAllowedError(str(path_obj), allowed_paths, mode="write")


def _get_allowed_read_paths() -> list[str]:
    """Get allowed read paths from environment."""
    env_val = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_READ", "[]")
    try:
        return json.loads(env_val)
    except json.JSONDecodeError:
        return []


def _get_allowed_write_paths() -> list[str]:
    """Get allowed write paths from environment."""
    env_val = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", "[]")
    try:
        return json.loads(env_val)
    except json.JSONDecodeError:
        return []


def make_error_response(error: Exception) -> dict[str, Any]:
    """Create structured error response from exception.

    Args:
        error: Exception with code attribute

    Returns:
        Dict with error shape matching quickstart.md format
    """
    code = getattr(error, "code", "UNKNOWN_ERROR")
    message = str(error)

    details = {}
    if isinstance(error, PathNotAllowedError):
        details["allowed_paths"] = error.allowed_paths
        details["mode"] = error.mode
    elif isinstance(error, ValidationFailedError):
        details["issues"] = error.issues
        # Test compatibility: tests expect 'reason' in details
        if error.issues:
            details["reason"] = error.issues[0]
    elif isinstance(error, SliceOutOfBoundsError):
        details["dimension"] = error.dim
        details["index"] = error.index
        details["size"] = error.size

    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }


# Test helper functions (imported by tests/unit/api/test_io_functions.py)
def path_not_allowed_error(
    path: str, allowed_paths: list[str], mode: str = "read"
) -> dict[str, Any]:
    return make_error_response(PathNotAllowedError(path, allowed_paths, mode))


def file_not_found_error(path: str) -> dict[str, Any]:
    return make_error_response(FileNotFoundIOError(path))


def unsupported_format_error(path: str, format_hint: str | None = None) -> dict[str, Any]:
    return make_error_response(UnsupportedFormatError(path, format_hint))


def validation_failed_error(path: str, reason: str) -> dict[str, Any]:
    return make_error_response(ValidationFailedError(path, [reason]))


def _detect_format(path: Path) -> str:
    """Detect image format from file extension."""
    # Check for OME-Zarr directories first
    if path.is_dir():
        name_lower = str(path).lower()
        if name_lower.endswith(".ome.zarr") or name_lower.endswith(".zarr"):
            return "OME-Zarr"

    suffix = path.suffix.lower()
    format_map = {
        ".tif": "TIFF",
        ".tiff": "TIFF",
        ".ome.tif": "OME-TIFF",
        ".ome.tiff": "OME-TIFF",
        ".czi": "CZI",
        ".lif": "LIF",
        ".nd2": "ND2",
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
    }
    # Check for .ome.tif special case
    if str(path).lower().endswith(".ome.tif") or str(path).lower().endswith(".ome.tiff"):
        return "OME-TIFF"
    return format_map.get(suffix, "Unknown")


def _get_mime_type(path: Path) -> str:
    """Get MIME type for image file."""
    fmt = _detect_format(path)
    mime_map = {
        "TIFF": "image/tiff",
        "OME-TIFF": "image/tiff",
        "OME-Zarr": "application/zarr+ome",
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "CZI": "application/octet-stream",
        "LIF": "application/octet-stream",
    }
    return mime_map.get(fmt, "application/octet-stream")


def load(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Load an image file into the artifact system.

    Args:
        inputs: Empty dict (no artifact inputs)
        params: {"path": str, "format": str | None}
        work_dir: Working directory for outputs

    Returns:
        {"outputs": {"image": BioImageRef}}

    Raises:
        PathNotAllowedError: If path outside allowed_read
        FileNotFoundIOError: If file doesn't exist
        UnsupportedFormatError: If no reader available
    """
    path = params.get("path")
    if not path:
        raise ValueError("Missing required parameter: path")

    if not isinstance(path, str):
        raise ValueError(f"Parameter 'path' must be a string, got {type(path).__name__}")

    # Validate path
    resolved_path = validate_read_path(path)

    # Check file exists
    if not resolved_path.exists():
        raise FileNotFoundIOError(str(resolved_path))

    # Load with BioImage
    from bioio import BioImage

    try:
        img = BioImage(resolved_path)
        # Access metadata to validate format
        _ = img.dims
    except Exception as e:
        raise UnsupportedFormatError(str(resolved_path)) from e

    # Use img.reader.dims.order for native axes (not forced TCZYX)
    native_dims = img.reader.dims.order
    native_shape = list(img.reader.data.shape)

    # Create BioImageRef
    ref_id = uuid.uuid4().hex
    ref = {
        "ref_id": ref_id,
        "type": "BioImageRef",
        "uri": f"file://{resolved_path}",
        "path": str(resolved_path),
        "format": _detect_format(resolved_path),
        "storage_type": "file",
        "mime_type": _get_mime_type(resolved_path),
        "size_bytes": resolved_path.stat().st_size,
        "created_at": datetime.now(UTC).isoformat(),
        "ndim": len(native_dims),
        "dims": list(native_dims),
        "physical_pixel_sizes": {
            "X": img.physical_pixel_sizes.X,
            "Y": img.physical_pixel_sizes.Y,
            "Z": img.physical_pixel_sizes.Z,
        },
        "metadata": {
            "axes": native_dims,
            "ndim": len(native_dims),
            "dims": list(native_dims),
            "shape": native_shape,
            "dtype": str(img.reader.data.dtype),
            "channel_names": list(img.channel_names) if img.channel_names else None,
        },
    }

    return {"outputs": {"image": ref}}


def table_load(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Load a tabular file (CSV/TSV) into a TableRef artifact.

    Args:
        inputs: Empty dict
        params: {
            "path": str,
            "delimiter": str | None,
            "encoding": str = "utf-8",
            "na_values": list[str] | None
        }
        work_dir: Working directory

    Returns:
        {"outputs": {"table": TableRef}}

    Raises:
        PathNotAllowedError: If path outside allowed_read
        FileNotFoundIOError: If file doesn't exist
        ValidationFailedError: If pandas fails to load the file
    """
    path = params.get("path")
    if not path:
        raise ValueError("Missing required parameter: path")

    if not isinstance(path, str):
        raise ValueError(f"Parameter 'path' must be a string, got {type(path).__name__}")

    # T016: Validate path and log permission decision
    try:
        resolved_path = validate_read_path(path)
        logger.info(f"Permission ALLOWED for READ: {path}")
    except PathNotAllowedError:
        logger.info(f"Permission DENIED for READ: {path} (Reason: Path not in allowed_read list)")
        raise

    # Check file exists
    if not resolved_path.exists():
        raise FileNotFoundIOError(str(resolved_path))

    # T056: Add large file warning (>100MB)
    file_size = resolved_path.stat().st_size
    if file_size > 100 * 1024 * 1024:
        logger.warning(f"Loading large file ({file_size / 1024 / 1024:.1f}MB) - this may take time")

    # T057: Add empty file handling (0-byte files)
    if file_size == 0:
        logger.warning(f"File {resolved_path} is empty (0 bytes)")
        ref_id = uuid.uuid4().hex
        return {
            "outputs": {
                "table": {
                    "ref_id": ref_id,
                    "type": "TableRef",
                    "uri": f"file://{resolved_path}",
                    "path": str(resolved_path),
                    "format": "csv",
                    "columns": [],
                    "row_count": 0,
                    "size_bytes": 0,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            }
        }

    delimiter = params.get("delimiter")

    format_hint = params.get("format")
    encoding = params.get("encoding", "utf-8")
    na_values = params.get("na_values")

    # T014: Auto-detect delimiter if not provided
    if delimiter is None:
        if format_hint and format_hint.upper() == "TSV":
            delimiter = "\t"
        elif format_hint and format_hint.upper() == "CSV":
            delimiter = ","
        else:
            suffix = resolved_path.suffix.lower()
            if suffix == ".csv":
                delimiter = ","
            elif suffix == ".tsv":
                delimiter = "\t"
            else:
                # try comma, tab, semicolon as per T014
                try:
                    with resolved_path.open("r", encoding=encoding) as f:
                        first_line = f.readline()
                        if "\t" in first_line:
                            delimiter = "\t"
                        elif ";" in first_line:
                            delimiter = ";"
                        else:
                            delimiter = ","
                except Exception:
                    delimiter = ","

    # T014/T017/T018: Load with pandas
    try:
        df = pd.read_csv(resolved_path, sep=delimiter, encoding=encoding, na_values=na_values)
    except Exception as e:
        raise ValidationFailedError(str(resolved_path), [f"Failed to load table: {e}"]) from e

    # Create TableRef
    ref_id = uuid.uuid4().hex
    table_format = format_hint.lower() if format_hint else ("tsv" if delimiter == "\t" else "csv")
    table_ref = {
        "ref_id": ref_id,
        "type": "TableRef",
        "uri": f"file://{resolved_path}",
        "path": str(resolved_path),
        "format": table_format,
        "columns": list(df.columns),
        "row_count": len(df),
        "delimiter": delimiter,
        "size_bytes": resolved_path.stat().st_size,
        "created_at": datetime.now(UTC).isoformat(),
    }

    return {"outputs": {"table": table_ref}}


def table_export(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Export a TableRef or ObjectRef to a delimited file (CSV/TSV).

    Args:
        inputs: {"data": TableRef | ObjectRef}
        params: {
            "dest_path": str,
            "sep": str = ","
        }
        work_dir: Working directory

    Returns:
        {"outputs": {"table": TableRef}}
    """
    data_ref = inputs.get("data")
    if not data_ref:
        raise ValueError("Missing input 'data'")

    dest_path_str = params.get("dest_path")
    if not dest_path_str:
        raise ValueError("Missing required parameter: dest_path")

    sep = params.get("sep", ",")

    # T037: Validate path and log permission decision
    try:
        dest_path = validate_write_path(dest_path_str)
        logger.info(f"Permission ALLOWED for WRITE: {dest_path_str}")
    except PathNotAllowedError:
        logger.info(
            f"Permission DENIED for WRITE: {dest_path_str} (Reason: Path not in allowed_write list)"
        )
        raise

    # Load data from TableRef or ObjectRef
    if isinstance(data_ref, str):
        # Handle simple URI string if provided
        uri = data_ref
        artifact_type = "TableRef"  # Assume TableRef if just a string
        delimiter = ","
    else:
        uri = data_ref.get("uri", "")
        artifact_type = data_ref.get("type", "TableRef")
        delimiter = data_ref.get("delimiter", ",")

    if artifact_type == "TableRef":
        # Load from file
        src_path = uri_to_path(uri)
        if not src_path.exists():
            raise FileNotFoundIOError(str(src_path))

        # Load with pandas to preserve precision
        df = pd.read_csv(src_path, sep=delimiter)
    elif artifact_type == "ObjectRef":
        # Load from memory
        if not uri.startswith("obj://"):
            raise ValueError(f"ObjectRef must have obj:// URI, got {uri}")

        parts = uri[6:].split("/")
        artifact_id = parts[-1]

        from bioimage_mcp_base.entrypoint import _MEMORY_ARTIFACTS

        from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

        obj = OBJECT_CACHE.get(artifact_id)
        if obj is None:
            obj = _MEMORY_ARTIFACTS.get(artifact_id)
        if obj is None:
            obj = OBJECT_CACHE.get(uri)
        if obj is None:
            obj = _MEMORY_ARTIFACTS.get(uri)

        if obj is None:
            raise ValueError(f"ObjectRef not found in memory: {uri}")

        if not isinstance(obj, pd.DataFrame):
            # Try to convert to DataFrame if it's a list of dicts or something
            try:
                df = pd.DataFrame(obj)
            except Exception as e:
                raise ValueError(
                    f"Cannot convert object of type {type(obj).__name__} to DataFrame: {e}"
                ) from e
        else:
            df = obj
    else:
        raise ValueError(f"Unsupported artifact type for table export: {artifact_type}")

    # T039: Preserve float precision (15 significant digits)
    # Include index if it's not a default RangeIndex or if it has a name
    include_index = not isinstance(df.index, pd.RangeIndex) or df.index.name is not None

    # Ensure parent directory exists before writing
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(dest_path, sep=sep, index=include_index, float_format="%.15g")

    # Create TableRef output
    ref_id = uuid.uuid4().hex
    table_format = "tsv" if sep == "\t" else "csv"

    table_ref = {
        "ref_id": ref_id,
        "type": "TableRef",
        "uri": f"file://{dest_path}",
        "path": str(dest_path),
        "format": table_format,
        "columns": list(df.columns),
        "row_count": len(df),
        "delimiter": sep,
        "size_bytes": dest_path.stat().st_size,
        "created_at": datetime.now(UTC).isoformat(),
    }

    return {"outputs": {"table": table_ref}}


def inspect(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Extract metadata from an image without loading pixel data.

    Args:
        inputs: Empty dict OR {"image": BioImageRef}
        params: {"path": str} if no artifact input
        work_dir: Working directory

    Returns:
        {"outputs": {"metadata": ImageMetadata dict}}

    Raises:
        PathNotAllowedError: If path outside allowed_read
        FileNotFoundIOError: If file doesn't exist
    """
    # Get path from params or from BioImageRef input
    image_ref = inputs.get("image")
    if image_ref:
        if isinstance(image_ref, str):
            uri = image_ref
        else:
            uri = image_ref.get("uri", "")

        if uri.startswith("file://"):
            path = uri[7:]
        else:
            path = uri
    else:
        path = params.get("path")

    if not path:
        raise ValueError("Missing required parameter: path or image input")

    if not isinstance(path, str):
        raise ValueError(f"Parameter 'path' must be a string, got {type(path).__name__}")

    # Validate path
    resolved_path = validate_read_path(path)

    # Check file exists
    if not resolved_path.exists():
        raise FileNotFoundIOError(str(resolved_path))

    # Load metadata lazily using BioImage
    from bioio import BioImage

    img = BioImage(resolved_path)

    # Use img.reader.dims.order for native axes (not forced TCZYX)
    native_dims = img.reader.dims.order
    native_shape = list(img.reader.data.shape)

    metadata = {
        "path": str(resolved_path),
        "format": _detect_format(resolved_path),
        "reader": img.reader.__class__.__name__,
        "shape": list(native_shape),
        "dims": native_dims,
        "dtype": str(img.reader.data.dtype),
        "ndim": len(native_dims),
        "physical_pixel_sizes": {
            "X": img.physical_pixel_sizes.X,
            "Y": img.physical_pixel_sizes.Y,
            "Z": img.physical_pixel_sizes.Z,
        },
        "channel_names": list(img.channel_names) if img.channel_names else None,
        "scene_count": len(img.scenes) if hasattr(img, "scenes") else 1,
    }

    return {"outputs": {"metadata": metadata}}


def slice_image(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Extract a subset of a multi-dimensional image.

    Args:
        inputs: {"image": BioImageRef}
        params: {"slices": SliceSpec dict}
        work_dir: Working directory

    Returns:
        {"outputs": {"output": BioImageRef}}

    Raises:
        SliceOutOfBoundsError: If indices exceed dimensions
    """
    image_ref = inputs.get("image")
    if not image_ref:
        raise ValueError("Missing required input: image")

    slices = params.get("slices", {})
    if not slices:
        raise ValueError("Missing required parameter: slices")

    # Load image via BioImage
    if isinstance(image_ref, str):
        uri = image_ref
    else:
        uri = image_ref.get("uri", "")

    if uri.startswith("file://"):
        path = uri[7:]
    else:
        path = uri

    from bioio import BioImage

    img = BioImage(path)

    # Get xarray data for dimension-aware slicing
    xarr = img.reader.xarray_data

    # Parse slices and build isel dict
    isel_args = {}
    for dim, spec in slices.items():
        if dim not in xarr.dims:
            raise ValueError(f"Invalid dimension '{dim}'. Available: {list(xarr.dims)}")

        dim_size = xarr.sizes[dim]

        if isinstance(spec, int):
            # Single index
            if spec < 0 or spec >= dim_size:
                raise SliceOutOfBoundsError(dim, spec, dim_size)
            isel_args[dim] = spec
        elif isinstance(spec, dict):
            # Range: {start, stop, step}
            start = spec.get("start", 0)
            stop = spec.get("stop", dim_size)
            step = spec.get("step", 1)

            if start < 0 or stop > dim_size:
                raise SliceOutOfBoundsError(dim, stop - 1, dim_size)

            isel_args[dim] = slice(start, stop, step)
        else:
            raise ValueError(f"Invalid slice spec for {dim}: {spec}")

    # Apply slicing
    sliced = xarr.isel(**isel_args)

    # Preserve metadata attrs
    for key in xarr.attrs:
        sliced.attrs[key] = xarr.attrs[key]

    # Save sliced result as new artifact
    import uuid
    from datetime import UTC, datetime

    out_path = work_dir / f"sliced_{uuid.uuid4().hex[:8]}.ome.zarr"

    # Export using OME-Zarr (native dims)
    from bioio_ome_zarr.writers import OMEZarrWriter

    data = sliced.values
    axes_names = [d.lower() for d in sliced.dims]
    type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
    axes_types = [type_map.get(d, "space") for d in axes_names]

    writer = OMEZarrWriter(
        store=str(out_path),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
    )
    writer.write_full_volume(data)

    # Build output ref
    ref_id = uuid.uuid4().hex
    input_physical = image_ref.get("physical_pixel_sizes", {})
    out_ref = {
        "ref_id": ref_id,
        "type": "BioImageRef",
        "uri": f"file://{out_path}",
        "path": str(out_path),
        "format": "OME-Zarr",
        "storage_type": "file",
        "mime_type": "application/octet-stream",
        "size_bytes": sum(f.stat().st_size for f in out_path.rglob("*") if f.is_file()),
        "created_at": datetime.now(UTC).isoformat(),
        "ndim": len(sliced.dims),
        "dims": list(sliced.dims),
        "physical_pixel_sizes": {
            "X": input_physical.get("X", img.physical_pixel_sizes.X),
            "Y": input_physical.get("Y", img.physical_pixel_sizes.Y),
            "Z": input_physical.get("Z", img.physical_pixel_sizes.Z),
        },
        "metadata": {
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "source_ref_id": None if isinstance(image_ref, str) else image_ref.get("ref_id"),
        },
    }

    return {"outputs": {"output": out_ref}}


def validate(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Validate an image file and report issues.

    Args:
        params: {"path": str, "deep": bool = False}

    Returns:
        {"outputs": {"result": ValidationReport}}
    """
    path = params.get("path")
    if not path:
        raise ValueError("Missing required parameter: path")
    deep = params.get("deep", False)

    # Validate path access
    resolved_path = validate_read_path(path)

    issues = []
    is_valid = True
    reader_selected = None
    format_detected = None
    metadata_summary = None

    # Check file exists
    if not resolved_path.exists():
        issues.append(
            {
                "severity": "error",
                "code": "FILE_NOT_FOUND",
                "message": f"File not found: {path}",
                "field": None,
            }
        )
        is_valid = False
    else:
        # Try to determine reader
        try:
            from bioio import BioImage

            img = BioImage(resolved_path)
            reader_selected = img.reader.__class__.__name__
            format_detected = _detect_format(resolved_path)

            # Metadata validation (fast, no pixel load)
            native_dims = img.reader.dims.order if hasattr(img.reader, "dims") else None
            native_shape = img.reader.data.shape if hasattr(img.reader, "data") else None

            metadata_summary = {
                "shape": list(native_shape) if native_shape else None,
                "dims": native_dims,
                "dtype": str(img.reader.data.dtype) if native_shape else None,
            }

            # Check for minimum requirements
            if native_dims and len(native_dims) < 2:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "INSUFFICIENT_DIMENSIONS",
                        "message": "Image has fewer than 2 dimensions",
                        "field": "dims",
                    }
                )

            # Check physical pixel sizes
            pixel_sizes = img.physical_pixel_sizes
            if pixel_sizes.X is None or pixel_sizes.Y is None:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "MISSING_PIXEL_SIZE",
                        "message": "Physical pixel sizes not defined",
                        "field": "physical_pixel_sizes",
                    }
                )

            # Deep validation (optional)
            if deep:
                # This would load pixels and check for corruption
                # For now, just a placeholder
                pass

        except Exception as e:
            issues.append(
                {
                    "severity": "error",
                    "code": "READER_FAILED",
                    "message": str(e),
                    "field": None,
                }
            )
            is_valid = False

    # Determine overall validity
    has_errors = any(i["severity"] == "error" for i in issues)
    is_valid = not has_errors

    return {
        "outputs": {
            "result": {
                "path": str(resolved_path),
                "is_valid": is_valid,
                "reader_selected": reader_selected,
                "format_detected": format_detected,
                "issues": issues,
                "metadata_summary": metadata_summary,
            }
        }
    }


def get_supported_formats(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Return list of supported image formats.

    Returns:
        {"outputs": {"result": {"formats": FormatList, "readers": ReaderList}}}
    """
    # Query bioio for registered reader plugins
    import importlib.metadata

    from bioio.plugins import get_plugins

    plugins = get_plugins(use_cache=True)

    formats = sorted({ext.lstrip(".") for ext in plugins.keys()})

    readers_dict = {}
    for ext, entries in plugins.items():
        for entry in entries:
            name = entry.entrypoint.name
            if name not in readers_dict:
                version = "unknown"
                try:
                    version = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    pass

                readers_dict[name] = {
                    "name": name,
                    "formats": set(),
                    "version": version,
                }
            readers_dict[name]["formats"].add(ext.lstrip("."))

    readers = []
    for r in readers_dict.values():
        r["formats"] = sorted(list(r["formats"]))
        readers.append(r)

    return {
        "outputs": {
            "result": {
                "formats": formats,
                "readers": sorted(readers, key=lambda x: x["name"]),
            }
        }
    }


def _infer_export_format(artifact: dict[str, Any] | str, requested_path: str | None = None) -> str:
    """Infer export format from artifact type and metadata."""
    if requested_path:
        path_obj = Path(requested_path)
        ext = path_obj.suffix.lower()
        if ext in (".tif", ".tiff"):
            if ".ome.tif" in path_obj.name.lower() or ".ome.tiff" in path_obj.name.lower():
                return "OME-TIFF"
            return "OME-TIFF"
        if ext == ".zarr" or requested_path.lower().endswith(".ome.zarr"):
            return "OME-Zarr"
        if ext == ".png":
            return "PNG"
        if ext == ".npy":
            return "NPY"

    if isinstance(artifact, str):
        return "OME-TIFF"

    metadata = artifact.get("metadata", {})
    # Large images (>4GB) -> OME-Zarr
    size_bytes = artifact.get("size_bytes", 0)
    if size_bytes > 4 * 1024**3:
        return "OME-Zarr"

    # 2D uint8/uint16 without rich metadata -> PNG
    dtype = str(metadata.get("dtype", ""))
    ndim = artifact.get("ndim", metadata.get("ndim", 0))
    shape = metadata.get("shape", [])
    effective_ndim = len([d for d in shape if d > 1]) if shape else ndim

    if (ndim == 2 or effective_ndim <= 2) and dtype in ("uint8", "uint16"):
        # Rich metadata check
        has_rich_metadata = bool(
            artifact.get("physical_pixel_sizes")
            or metadata.get("physical_pixel_sizes")
            or metadata.get("channel_names")
        )
        if not has_rich_metadata:
            return "PNG"

    return "OME-TIFF"


def _export_png(data: np.ndarray, path: Path):
    """Export 2D array to PNG."""
    import imageio

    if data.ndim > 2:
        data = np.squeeze(data)
    if data.ndim != 2:
        raise ValueError(f"PNG export requires 2D data, got {data.ndim}D")
    imageio.v3.imwrite(path, data)


def _export_ome_tiff(data: np.ndarray, path: Path, axes: str | None = None):
    """Export array to OME-TIFF."""
    from bioio.writers import OmeTiffWriter

    if axes is None:
        ndim_map = {2: "YX", 3: "ZYX", 4: "CZYX", 5: "TCZYX"}
        axes = ndim_map.get(data.ndim, "TCZYX"[-data.ndim :] if data.ndim <= 5 else "TCZYX")

    OmeTiffWriter.save(data, str(path), dim_order=axes)


def _export_ome_zarr(data: np.ndarray, path: Path, dims: list[str] | None = None):
    """Export array to OME-Zarr."""
    from bioio_ome_zarr.writers import OMEZarrWriter

    # Reconcile data rank with dims by squeezing singleton dimensions
    if dims is not None and len(dims) < data.ndim:
        while data.ndim > len(dims):
            singleton_axes = [i for i, s in enumerate(data.shape) if s == 1]
            if not singleton_axes:
                break  # No more singletons to squeeze
            data = np.squeeze(data, axis=singleton_axes[0])

    # Ensure at least 2D
    while data.ndim < 2:
        data = data[np.newaxis, ...]

    if dims is None or len(dims) != data.ndim:
        if data.ndim == 5:
            dims = ["T", "C", "Z", "Y", "X"]
        elif data.ndim == 2:
            dims = ["Y", "X"]
        else:
            dims = ["T", "C", "Z", "Y", "X"][-data.ndim :]

    axis_type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
    axes_names = [d.lower() for d in dims]
    axes_types = [axis_type_map.get(d, "space") for d in axes_names]

    writer = OMEZarrWriter(
        store=str(path),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
        zarr_format=2,
    )
    writer.write_full_volume(data)


def export(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Export an artifact to a specific file format.

    Args:
        inputs: {"image": BioImageRef} or {"artifact": Ref}
        params: {"format": str | None, "path": str | None, "dest_path": str | None}
        work_dir: Working directory

    Returns:
        {"outputs": {"output": Ref}}
    """
    artifact = inputs.get("image") or inputs.get("artifact")
    if not artifact:
        raise ValueError("Missing input 'image' or 'artifact'")

    dest_format = params.get("format")
    dest_path_str = params.get("path") or params.get("dest_path")

    # T016: Contract requires at least one of path or format to be specified
    # to avoid ambiguous export calls (though manifest says both are optional).
    if dest_format is None and dest_path_str is None:
        raise ValueError("Either 'format' or 'path' must be provided")

    if dest_path_str:
        dest_path = validate_write_path(dest_path_str)
    else:
        dest_path = None

    # Handle PlotRef as direct file copy
    artifact_type = artifact.get("type", "") if isinstance(artifact, dict) else ""
    if artifact_type == "PlotRef":
        source_path_str = artifact.get("path")
        if not source_path_str:
            # Try to extract from URI
            plot_uri = artifact.get("uri", "")
            try:
                source_path_str = str(uri_to_path(plot_uri))
            except Exception:
                pass

        if not source_path_str:
            raise ValueError("PlotRef missing source path and URI")

        source_path = Path(source_path_str)
        if not source_path.exists():
            raise FileNotFoundIOError(str(source_path))

        if dest_path is None:
            suffix = source_path.suffix if source_path.suffix else ".png"
            dest_path = work_dir / f"exported_plot_{uuid.uuid4().hex[:8]}{suffix}"

        # Copy the file
        shutil.copy2(source_path, dest_path)

        return {
            "outputs": {
                "output": {
                    "type": "PlotRef",
                    "format": artifact.get("format", "PNG"),
                    "uri": dest_path.as_uri(),
                    "path": str(dest_path),
                    "metadata": artifact.get("metadata", {}),
                }
            }
        }

    if dest_format is None:
        dest_format = _infer_export_format(artifact, dest_path_str)

    dest_format = dest_format.upper()

    if dest_path is None:
        ext_map = {
            "OME-TIFF": ".ome.tiff",
            "OME-ZARR": ".ome.zarr",
            "PNG": ".png",
            "NPY": ".npy",
        }
        ext = ext_map.get(dest_format, ".bin")
        dest_path = work_dir / f"exported{ext}"

    # Handle both string (URI/path) and dict inputs
    if isinstance(artifact, str):
        uri = artifact
        source_ref_id = None
        artifact_type = "BioImageRef"
    else:
        uri = artifact.get("uri")
        source_ref_id = artifact.get("ref_id")
        artifact_type = artifact.get("type", "BioImageRef")

    # If exporting an ObjectRef, the result is now a file-backed BioImageRef
    if artifact_type == "ObjectRef":
        artifact_type = "BioImageRef"

    if not uri:
        raise ValueError("Artifact missing URI")

    # Handle ObjectRef inputs (from xarray operations)
    if str(uri).startswith("obj://"):
        # Parse obj:// URI to extract artifact_id
        # Format: obj://session_id/env_id/artifact_id
        parts = str(uri)[6:].split("/")
        if len(parts) >= 3:
            artifact_id = parts[-1]  # Last part is artifact_id

            # Try to load from object cache or memory artifacts
            from bioimage_mcp_base.entrypoint import _MEMORY_ARTIFACTS

            from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

            obj = OBJECT_CACHE.get(artifact_id)
            if obj is None:
                obj = _MEMORY_ARTIFACTS.get(artifact_id)
            if obj is None:
                obj = OBJECT_CACHE.get(str(uri))
            if obj is None:
                obj = _MEMORY_ARTIFACTS.get(str(uri))

            if obj is None:
                raise ValueError(f"ObjectRef not found in memory: {uri}")

            # Convert to numpy array
            if hasattr(obj, "values"):  # xarray.DataArray
                data = obj.values
            elif isinstance(obj, np.ndarray):
                data = obj
            else:
                raise ValueError(f"Cannot export object of type {type(obj).__name__}")
        else:
            raise ValueError(f"Invalid obj:// URI format: {uri}")
    else:
        # Original file-based logic
        src_path = uri_to_path(str(uri))
        data = load_native_image(
            src_path, format_hint=None if isinstance(artifact, str) else artifact.get("format")
        )

    # Handle data types not supported by OME-TIFF (e.g. uint64 from sum)
    if dest_format == "OME-TIFF" and (data.dtype == np.uint64 or data.dtype == np.int64):
        data = data.astype(np.float32)

    # Ensure parent directory exists before writing
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_format == "PNG":
        _export_png(data, dest_path)
    elif dest_format == "OME-TIFF":
        _export_ome_tiff(data, dest_path)
    elif dest_format == "OME-ZARR":
        dims = (
            None
            if isinstance(artifact, str)
            else (artifact.get("metadata", {}).get("dims") or artifact.get("dims"))
        )
        _export_ome_zarr(data, dest_path, dims=dims)
    elif dest_format == "NPY":
        np.save(dest_path, data)
    else:
        raise ValueError(f"Unsupported export format: {dest_format}")

    return {
        "outputs": {
            "output": {
                "type": artifact_type,
                "format": dest_format,
                "path": str(dest_path),
                "uri": f"file://{dest_path}",
                "metadata": {"source_ref_id": source_ref_id},
            },
        }
    }
