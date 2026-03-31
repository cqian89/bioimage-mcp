#!/usr/bin/env python3
"""Tttrlib tool pack entrypoint for bioimage-mcp.

Implements the JSON stdin/stdout protocol for tool execution.
Supports persistent worker mode (NDJSON).
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Global caches
_TTTR_CACHE: dict[str, Any] = {}  # Stores tttrlib.TTTR objects
_OBJECT_CACHE: dict[str, Any] = {}  # Stores CLSMImage, Correlator, etc. objects

# Worker identity
_SESSION_ID: str | None = None
_ENV_ID: str | None = None

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-tttrlib"
UNSUPPORTED_STATUSES = {"denied", "deferred"}
SWIG_TRANSPORT_ATTRS = {"this", "thisown"}

_COVERAGE_CACHE: dict[str, Any] | None = None


def _load_coverage_registry() -> dict[str, dict[str, Any]]:
    """Load coverage registry keyed by strict upstream function IDs."""
    global _COVERAGE_CACHE
    if _COVERAGE_CACHE is not None:
        return _COVERAGE_CACHE

    coverage_path = Path(__file__).resolve().parent.parent / "schema" / "tttrlib_coverage.json"
    try:
        with open(coverage_path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        _COVERAGE_CACHE = {}
        return _COVERAGE_CACHE

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        _COVERAGE_CACHE = {}
        return _COVERAGE_CACHE

    _COVERAGE_CACHE = coverage
    return _COVERAGE_CACHE


def _get_coverage_entry(fn_id: str) -> dict[str, Any] | None:
    """Return coverage entry for a function id if available."""
    registry = _load_coverage_registry()
    entry = registry.get(fn_id)
    return entry if isinstance(entry, dict) else None


def _unsupported_method_error(fn_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Build stable unsupported-method error payload."""
    status = str(entry.get("status") or "deferred")
    remediation = str(entry.get("revisit_trigger") or "Use a supported tttrlib method.").strip()
    return {
        "code": "TTTRLIB_UNSUPPORTED_METHOD",
        "message": f"Unsupported tttrlib method: {fn_id} ({status})",
        "status": status,
        "method_id": fn_id,
        "remediation": remediation,
    }


def _unsupported_argument_pattern_error(method_id: str, detail: str) -> dict[str, Any]:
    """Build deterministic unsupported-argument error payload."""
    return {
        "code": "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN",
        "message": f"Unsupported argument pattern for {method_id}: {detail}",
        "method_id": method_id,
        "remediation": "Use only the documented supported subset for this method.",
    }


def _resolve_output_path(filename: str, work_dir: Path) -> Path:
    """Resolve output path relative to work_dir with traversal guardrails."""
    root = work_dir.resolve()
    output_path = Path(filename)
    if not output_path.is_absolute():
        output_path = (root / output_path).resolve()
    else:
        output_path = output_path.resolve()

    if output_path != root and root not in output_path.parents:
        raise ValueError("TTTRLIB_UNSAFE_OUTPUT_PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _export_path_error(filename: str) -> dict[str, Any]:
    """Build stable unsafe output path error payload."""
    return {
        "code": "TTTRLIB_UNSAFE_OUTPUT_PATH",
        "message": f"Output path escapes work_dir: {filename}",
        "remediation": "Use a relative path under work_dir or an absolute child of work_dir.",
    }


def _validate_export_extension(
    method_id: str,
    filepath: Path,
    allowed_extensions: set[str],
) -> dict[str, Any] | None:
    """Validate extension whitelist for export variants."""
    suffix = filepath.suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        return _unsupported_argument_pattern_error(
            method_id,
            f"expected extension in {{{allowed}}}, got '{suffix or '<none>'}'",
        )
    return None


def _tttr_write_subset_error(detail: str) -> dict[str, Any]:
    """Build deterministic generic-write subset failure payload."""
    return {
        "code": "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN",
        "message": f"Unsupported argument pattern for tttrlib.TTTR.write: {detail}",
        "method_id": "tttrlib.TTTR.write",
        "remediation": (
            "The requested TTTR/container combination is unsupported for file export by the "
            "installed tttrlib runtime."
        ),
    }


def _write_native_output(payload: Any, stem: str, work_dir: Path) -> dict[str, Any]:
    """Persist JSON payload and return a NativeOutputRef."""
    output_path = work_dir / f"{stem}_{uuid.uuid4().hex[:8]}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, default=str)

    return {
        "ref_id": uuid.uuid4().hex,
        "type": "NativeOutputRef",
        "uri": f"file://{output_path.absolute()}",
        "path": str(output_path.absolute()),
        "format": "json",
        "mime_type": "application/json",
        "created_at": datetime.now(UTC).isoformat(),
    }


def _normalize_json_safe_value(
    value: Any,
    *,
    _seen: set[int] | None = None,
) -> Any:
    """Normalize nested SWIG-like values into JSON-safe Python data."""
    if _seen is None:
        _seen = set()

    if value is None or isinstance(value, str | int | float | bool):
        return value

    obj_id = id(value)
    if obj_id in _seen:
        return str(value)

    if hasattr(value, "item") and callable(value.item):
        try:
            return _normalize_json_safe_value(value.item(), _seen=_seen)
        except (TypeError, ValueError):
            pass

    if isinstance(value, Mapping):
        _seen.add(obj_id)
        return {
            str(key): _normalize_json_safe_value(item, _seen=_seen) for key, item in value.items()
        }

    if isinstance(value, tuple | list | set):
        _seen.add(obj_id)
        return [_normalize_json_safe_value(item, _seen=_seen) for item in value]

    if isinstance(value, Iterable):
        _seen.add(obj_id)
        try:
            return [_normalize_json_safe_value(item, _seen=_seen) for item in value]
        except TypeError:
            pass

    public_attrs: dict[str, Any] = {}
    for attr_name in sorted(name for name in dir(value) if not name.startswith("_")):
        if attr_name in SWIG_TRANSPORT_ATTRS:
            continue
        try:
            attr_value = getattr(value, attr_name)
        except Exception:
            continue
        if callable(attr_value):
            continue
        public_attrs[attr_name] = _normalize_json_safe_value(attr_value, _seen=_seen | {obj_id})

    if public_attrs:
        return public_attrs

    return str(value)


def _serialize_clsm_settings(settings: Any) -> dict[str, Any]:
    """Serialize tttrlib CLSMSettings objects to JSON-safe metadata."""
    payload = _normalize_json_safe_value(settings)
    if not isinstance(payload, dict):
        raise TypeError("CLSM settings payload is not JSON-object serializable")
    return payload


def _write_table_output(
    columns: list[str],
    rows: Any,
    stem: str,
    work_dir: Path,
) -> dict[str, Any]:
    """Persist tabular data with consistent TableRef metadata."""
    import numpy as np

    table = np.asarray(rows, dtype=float)
    if table.ndim == 1:
        table = table.reshape(-1, 1)

    csv_path = work_dir / f"{stem}_{uuid.uuid4().hex[:8]}.csv"
    np.savetxt(csv_path, table, delimiter=",", header=",".join(columns), comments="")

    return {
        "ref_id": uuid.uuid4().hex,
        "type": "TableRef",
        "uri": f"file://{csv_path.absolute()}",
        "path": str(csv_path.absolute()),
        "format": "csv",
        "created_at": datetime.now(UTC).isoformat(),
        "columns": columns,
        "row_count": int(table.shape[0]),
        "metadata": {
            "columns": [{"name": name, "dtype": "float64"} for name in columns],
            "row_count": int(table.shape[0]),
        },
    }


def _extract_correlator_curve_columns(curve: Any) -> tuple[Any, Any]:
    """Extract tau/correlation arrays from a live CorrelatorCurve-like object."""
    tau = getattr(curve, "x", None)
    corr = getattr(curve, "y", None)

    if tau is None and hasattr(curve, "get_x_axis"):
        tau = curve.get_x_axis()
    if corr is None and hasattr(curve, "get_corr"):
        corr = curve.get_corr()

    if (tau is None or corr is None) and isinstance(curve, tuple | list) and len(curve) == 2:
        tau, corr = curve

    if tau is None or corr is None:
        raise TypeError("CorrelatorCurve does not expose x/y or getter data")

    return tau, corr


def _selection_to_indices(selection: Any) -> Any:
    """Normalize tttrlib selection outputs to integer event indices."""
    import numpy as np

    indices = np.asarray(selection)
    if indices.dtype == bool:
        indices = np.flatnonzero(indices)
    return indices.astype(int).reshape(-1)


def _write_selection_table(indices: Any, stem: str, work_dir: Path) -> dict[str, Any]:
    """Persist a selection index list as a one-column TableRef CSV."""
    import numpy as np

    selection_indices = np.asarray(indices, dtype=int).reshape(-1)
    csv_path = work_dir / f"{stem}_{uuid.uuid4().hex[:8]}.csv"
    np.savetxt(
        csv_path,
        selection_indices.reshape(-1, 1),
        delimiter=",",
        header="index",
        comments="",
        fmt="%d",
    )
    return {
        "ref_id": uuid.uuid4().hex,
        "type": "TableRef",
        "uri": f"file://{csv_path.absolute()}",
        "path": str(csv_path.absolute()),
        "format": "csv",
        "created_at": datetime.now(UTC).isoformat(),
        "columns": ["index"],
        "row_count": int(selection_indices.size),
        "metadata": {
            "columns": [{"name": "index", "dtype": "int64"}],
            "row_count": int(selection_indices.size),
        },
    }


def _infer_tttr_format_and_suffix(tttr_ref: dict[str, Any]) -> tuple[str, str]:
    """Infer a concrete TTTR file format and suffix for exported subsets."""
    format_to_suffix = {
        "PTU": ".ptu",
        "HT3": ".ht3",
        "SPC-130": ".spc",
        "SPC-630_256": ".spc",
        "SPC-630_4096": ".spc",
        "PHOTON-HDF5": ".h5",
        "HDF": ".h5",
        "CZ-RAW": ".raw",
        "SM": ".sm",
    }
    suffix_to_format = {suffix: fmt for fmt, suffix in format_to_suffix.items()}

    fmt = tttr_ref.get("format")
    if fmt in format_to_suffix:
        return fmt, format_to_suffix[fmt]

    uri = str(tttr_ref.get("uri") or "")
    suffix = Path(uri[7:] if uri.startswith("file://") else uri).suffix.lower()
    if suffix in suffix_to_format:
        resolved = suffix_to_format[suffix]
        return resolved, suffix

    return "PTU", ".ptu"


def _build_tttr_file_output(filepath: Path, fmt: str, ref_id: str | None = None) -> dict[str, Any]:
    """Build a file-backed TTTRRef payload."""
    return {
        "ref_id": ref_id or uuid.uuid4().hex,
        "type": "TTTRRef",
        "uri": f"file://{filepath.absolute()}",
        "path": str(filepath.absolute()),
        "format": fmt,
        "storage_type": "file",
        "created_at": datetime.now(UTC).isoformat(),
    }


def _canonical_tttr_write_format(filepath: Path) -> str | None:
    """Map output suffixes to canonical TTTRRef formats."""
    suffix = filepath.suffix.lower()
    suffix_to_format = {
        ".ptu": "PTU",
        ".ht3": "HT3",
        ".spc": "SPC-130",
        ".h5": "PHOTON-HDF5",
        ".hdf5": "PHOTON-HDF5",
        ".hdf": "HDF",
        ".raw": "CZ-RAW",
        ".sm": "SM",
    }
    return suffix_to_format.get(suffix)


def _initialize_worker(session_id: str, env_id: str) -> None:
    """Initialize worker identity."""
    global _SESSION_ID, _ENV_ID
    _SESSION_ID = session_id
    _ENV_ID = env_id


def _store_tttr(tttr_obj: Any, uri: str) -> tuple[str, str]:
    """Store TTTR object in cache, return (ref_id, file:// URI)."""
    ref_id = uuid.uuid4().hex
    _TTTR_CACHE[ref_id] = {"obj": tttr_obj, "uri": uri}
    return ref_id, uri


def _load_tttr_cached(ref_id_or_uri: str) -> Any:
    """Load TTTR object from in-worker cache only."""
    if ref_id_or_uri in _TTTR_CACHE:
        return _TTTR_CACHE[ref_id_or_uri]["obj"]

    for data in _TTTR_CACHE.values():
        if data["uri"] == ref_id_or_uri:
            return data["obj"]

    raise KeyError(f"TTTR object not found: {ref_id_or_uri}")


def _load_tttr(ref_id_or_uri: str) -> Any:
    """Load TTTR object from cache."""
    try:
        return _load_tttr_cached(ref_id_or_uri)
    except KeyError:
        pass

    # If it's a file URI but not in cache, try opening it
    if ref_id_or_uri.startswith("file://"):
        path = Path(ref_id_or_uri[7:])
        if not path.exists():
            raise KeyError(f"TTTR file not found: {path}")

        import tttrlib

        tttr = tttrlib.TTTR(str(path))
        _store_tttr(tttr, ref_id_or_uri)
        return tttr

    raise KeyError(f"TTTR object not found: {ref_id_or_uri}")


def _load_tttr_from_input(tttr_ref: dict[str, Any]) -> Any:
    """Load TTTR from input payload, preferring in-worker ref cache."""
    ref_id = tttr_ref.get("ref_id")
    uri = tttr_ref.get("uri")

    load_errors: list[str] = []
    if ref_id:
        try:
            return _load_tttr_cached(ref_id)
        except KeyError as exc:
            load_errors.append(str(exc))

    if uri:
        try:
            return _load_tttr(uri)
        except KeyError as exc:
            load_errors.append(str(exc))

    if load_errors:
        raise KeyError(load_errors[-1])
    raise KeyError("TTTR object not found: missing ref_id and uri")


def _store_object(obj: Any, class_name: str) -> dict[str, Any]:
    """Store object (e.g., CLSMImage) in cache and return ObjectRef."""
    if _SESSION_ID is None or _ENV_ID is None:
        raise RuntimeError("Worker not initialized")
    object_id = uuid.uuid4().hex
    _OBJECT_CACHE[object_id] = obj
    obj_uri = f"obj://{_SESSION_ID}/{_ENV_ID}/{object_id}"

    return {
        "ref_id": object_id,
        "type": "ObjectRef",
        "uri": obj_uri,
        "python_class": class_name,
        "storage_type": "memory",
        "created_at": datetime.now(UTC).isoformat(),
    }


def _load_object(uri_or_id: str) -> Any:
    """Load object from cache by obj:// URI or ref_id."""
    if uri_or_id in _OBJECT_CACHE:
        return _OBJECT_CACHE[uri_or_id]

    if not uri_or_id.startswith("obj://"):
        raise ValueError(f"Invalid object URI or ID: {uri_or_id}")
    parts = uri_or_id[6:].split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid object URI format: {uri_or_id}")
    _, _, object_id = parts
    if object_id not in _OBJECT_CACHE:
        raise KeyError(f"Object not found: {object_id}")
    return _OBJECT_CACHE[object_id]


# Function handlers


def handle_tttr_open(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR - open a TTTR file."""
    import tttrlib

    filename = params.get("filename")
    container_type = params.get("container_type")

    if not filename:
        return {"ok": False, "error": {"message": "filename is required"}}

    filepath = Path(filename)
    if not filepath.exists():
        return {
            "ok": False,
            "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {filename}"},
        }

    # Map container_type to tttrlib format codes
    container_map = {
        "PTU": 0,
        "HT3": 1,
        "SPC-130": 2,
        "SPC-630_256": 3,
        "SPC-630_4096": 4,
        "PHOTON-HDF5": 5,
        "CZ-RAW": 6,
        "SM": 7,
    }

    try:
        if container_type and container_type in container_map:
            tttr = tttrlib.TTTR(str(filepath), container_map[container_type])
        else:
            # Auto-detect format
            tttr = tttrlib.TTTR(str(filepath))

        # Store in cache
        file_uri = f"file://{filepath.absolute()}"
        ref_id, uri = _store_tttr(tttr, file_uri)

        # Get metadata
        n_valid = tttr.n_valid_events if hasattr(tttr, "n_valid_events") else None

        output = {
            "ref_id": ref_id,
            "type": "TTTRRef",
            "uri": uri,
            "path": str(filepath.absolute()),
            "format": container_type or "auto",
            "storage_type": "file",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "n_valid_events": n_valid,
            },
        }

        return {"ok": True, "outputs": {"tttr": output}, "log": f"Opened TTTR file: {filename}"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_tttr_header(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.header - extract metadata."""
    import json as json_module

    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    ref_id = tttr_ref.get("ref_id") or uuid.uuid4().hex

    try:
        tttr = _load_tttr(tttr_key)
        # Extract header data safely
        header_data = {}
        if hasattr(tttr, "header"):
            try:
                header_data = dict(tttr.header.data)
            except (AttributeError, TypeError):
                # Fallback if .data is not directly dict-convertible
                header_data = {"info": "Header object present but data extraction failed"}

        # Write header to JSON file
        header_path = work_dir / f"header_{ref_id[:8]}.json"
        with open(header_path, "w") as f:
            json_module.dump(header_data, f, indent=2, default=str)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "NativeOutputRef",
            "uri": f"file://{header_path.absolute()}",
            "path": str(header_path.absolute()),
            "format": "json",
            "mime_type": "application/json",
            "created_at": datetime.now(UTC).isoformat(),
        }

        return {"ok": True, "outputs": {"header": output}, "log": "Header extracted"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_clsm_image(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage - reconstruct image from TTTR."""
    import tttrlib

    tttr_ref = inputs.get("tttr", {})

    try:
        tttr = _load_tttr_from_input(tttr_ref)

        # Forward only explicitly supplied parameters to preserve native tttrlib defaults.
        clsm_kwargs: dict[str, Any] = {}
        for key in [
            "reading_routine",
            "marker_frame_start",
            "marker_line_start",
            "marker_line_stop",
            "channels",
            "fill",
            "n_pixel_per_line",
            "n_lines",
            "n_frames",
            "skip_before_first_frame_marker",
        ]:
            if key in params:
                clsm_kwargs[key] = params[key]

        # Use direct-style constructor call for better parity with native usage.
        clsm = tttrlib.CLSMImage(tttr, **clsm_kwargs)

        output = _store_object(clsm, "tttrlib.CLSMImage")

        return {
            "ok": True,
            "outputs": {"clsm": output},
            "log": f"Reconstructed CLSMImage with {clsm.n_frames} frames",
        }

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_correlator(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.Correlator - compute correlation."""
    import numpy as np
    import tttrlib

    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    try:
        tttr = _load_tttr(tttr_key)

        correlator_kwargs: dict[str, Any] = {
            "tttr": tttr,
            "n_bins": params.get("n_bins", 17),
            "n_casc": params.get("n_casc", 25),
            "make_fine": params.get("make_fine", False),
            "method": params.get("method", "wahl"),
        }
        if "channels" in params:
            correlator_kwargs["channels"] = params["channels"]

        correlator = tttrlib.Correlator(**correlator_kwargs)

        x = correlator.x
        y = correlator.y
        data = np.column_stack((x, y))
        curve = _write_table_output(["tau", "correlation"], data, "correlation", work_dir)

        return {
            "ok": True,
            "outputs": {"curve": curve},
            "log": "Correlation computed",
        }

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def _build_correlator(
    inputs: dict[str, Any], params: dict[str, Any], method_id: str
) -> tuple[Any, dict[str, Any] | None]:
    """Construct a correlator from a strict supported subset."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    required = {"channels"}
    allowed = required | {"n_bins", "n_casc", "make_fine", "method"}
    extra = sorted(set(params) - allowed)
    if extra:
        return None, _unsupported_argument_pattern_error(
            method_id,
            f"unsupported params: {', '.join(extra)}",
        )

    missing = sorted(required - set(params))
    if missing:
        return None, _unsupported_argument_pattern_error(
            method_id,
            f"missing params: {', '.join(missing)}",
        )

    channels = params.get("channels")
    if not isinstance(channels, list) or len(channels) != 2:
        return None, _unsupported_argument_pattern_error(
            method_id,
            "channels must be [[...], [...]]",
        )

    try:
        import tttrlib

        tttr = _load_tttr(tttr_key)
        correlator = tttrlib.Correlator(
            tttr=tttr,
            channels=channels,
            n_bins=params.get("n_bins", 17),
            n_casc=params.get("n_casc", 25),
            make_fine=params.get("make_fine", False),
            method=params.get("method", "wahl"),
        )
        return correlator, None
    except Exception as exc:
        return None, {"message": str(exc)}


def handle_clsm_get_image_info(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_image_info metadata export."""
    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    if params:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.CLSMImage.get_image_info", "no params"
            ),
        }

    try:
        clsm = _load_object(clsm_key)
        output = _write_native_output(
            _normalize_json_safe_value(clsm.get_image_info()),
            "clsm_image_info",
            work_dir,
        )
        return {"ok": True, "outputs": {"image_info": output}, "log": "CLSM image info extracted"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_clsm_get_settings(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_settings metadata export."""
    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    if params:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.CLSMImage.get_settings", "no params"
            ),
        }

    try:
        clsm = _load_object(clsm_key)
        output = _write_native_output(
            _serialize_clsm_settings(clsm.get_settings()),
            "clsm_settings",
            work_dir,
        )
        return {"ok": True, "outputs": {"settings": output}, "log": "CLSM settings extracted"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_correlator_get_curve(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.Correlator.get_curve as tabular output."""
    import numpy as np

    correlator, error = _build_correlator(inputs, params, "tttrlib.Correlator.get_curve")
    if error:
        return {"ok": False, "error": error}

    try:
        curve = correlator.get_curve()
        tau, corr = _extract_correlator_curve_columns(curve)
        data = np.column_stack((np.asarray(tau, dtype=float), np.asarray(corr, dtype=float)))
        output = _write_table_output(["tau", "correlation"], data, "correlator_curve", work_dir)
        return {"ok": True, "outputs": {"curve": output}, "log": "Correlator curve extracted"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_correlator_get_x_axis(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.Correlator.get_x_axis as tabular output."""
    import numpy as np

    correlator, error = _build_correlator(inputs, params, "tttrlib.Correlator.get_x_axis")
    if error:
        return {"ok": False, "error": error}

    try:
        tau = np.asarray(correlator.get_x_axis(), dtype=float)
        output = _write_table_output(["tau"], tau, "correlator_x_axis", work_dir)
        return {"ok": True, "outputs": {"tau": output}, "log": "Correlator x-axis extracted"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_correlator_get_corr(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.Correlator.get_corr as tabular output."""
    import numpy as np

    correlator, error = _build_correlator(inputs, params, "tttrlib.Correlator.get_corr")
    if error:
        return {"ok": False, "error": error}

    try:
        corr = np.asarray(correlator.get_corr(), dtype=float)
        output = _write_table_output(["correlation"], corr, "correlator_corr", work_dir)
        return {
            "ok": True,
            "outputs": {"correlation": output},
            "log": "Correlator values extracted",
        }
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_time_window_ranges(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.get_time_window_ranges - burst selection."""
    import numpy as np

    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    try:
        tttr = _load_tttr(tttr_key)

        ranges = tttr.get_time_window_ranges(**params)

        csv_path = work_dir / f"ranges_{uuid.uuid4().hex[:8]}.csv"
        np.savetxt(
            csv_path,
            ranges,
            delimiter=",",
            header="start_index,stop_index",
            comments="",
            fmt="%d",
        )

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "TableRef",
            "uri": f"file://{csv_path.absolute()}",
            "path": str(csv_path.absolute()),
            "format": "csv",
            "created_at": datetime.now(UTC).isoformat(),
            "columns": ["start_index", "stop_index"],
            "row_count": len(ranges),
            "metadata": {
                "columns": [
                    {"name": "start_index", "dtype": "int64"},
                    {"name": "stop_index", "dtype": "int64"},
                ],
                "row_count": len(ranges),
            },
        }

        return {"ok": True, "outputs": {"ranges": output}, "log": "Time window ranges computed"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_count_rate(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.get_count_rate - return scalar count rate."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    if params:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_count_rate", "no params"
            ),
        }

    try:
        tttr = _load_tttr(tttr_key)
        count_rate = float(tttr.get_count_rate())

        output_path = work_dir / f"count_rate_{uuid.uuid4().hex[:8]}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"count_rate": count_rate}, f)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "NativeOutputRef",
            "uri": f"file://{output_path.absolute()}",
            "path": str(output_path.absolute()),
            "format": "json",
            "mime_type": "application/json",
            "created_at": datetime.now(UTC).isoformat(),
        }
        return {"ok": True, "outputs": {"count_rate": output}, "log": "Count rate computed"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_intensity_trace(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.get_intensity_trace - return trace table."""
    import numpy as np

    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    allowed_params = {"time_window_length"}
    extra = sorted(set(params) - allowed_params)
    if extra:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_intensity_trace", f"unsupported params: {', '.join(extra)}"
            ),
        }

    try:
        tttr = _load_tttr(tttr_key)
        trace = np.asarray(tttr.get_intensity_trace(**params), dtype=float)
        if trace.ndim == 1:
            trace = np.column_stack((np.arange(trace.size, dtype=float), trace))
        if trace.ndim != 2 or trace.shape[1] < 2:
            return {
                "ok": False,
                "error": _unsupported_argument_pattern_error(
                    "tttrlib.TTTR.get_intensity_trace", "expected tabular two-column output"
                ),
            }

        csv_path = work_dir / f"intensity_trace_{uuid.uuid4().hex[:8]}.csv"
        np.savetxt(
            csv_path,
            trace[:, :2],
            delimiter=",",
            header="time,count_rate",
            comments="",
        )

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "TableRef",
            "uri": f"file://{csv_path.absolute()}",
            "path": str(csv_path.absolute()),
            "format": "csv",
            "created_at": datetime.now(UTC).isoformat(),
            "columns": ["time", "count_rate"],
            "row_count": int(trace.shape[0]),
            "metadata": {
                "columns": [
                    {"name": "time", "dtype": "float64"},
                    {"name": "count_rate", "dtype": "float64"},
                ],
                "row_count": int(trace.shape[0]),
            },
        }
        return {"ok": True, "outputs": {"trace": output}, "log": "Intensity trace extracted"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_selection_by_channel(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.get_selection_by_channel with a strict supported subset."""

    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    allowed_params = {"input"}
    extra = sorted(set(params) - allowed_params)
    if extra:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_selection_by_channel", f"unsupported params: {', '.join(extra)}"
            ),
        }

    selection_input = params.get("input")
    if not isinstance(selection_input, list) or not selection_input:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_selection_by_channel", "input must be a non-empty integer list"
            ),
        }

    try:
        tttr = _load_tttr(tttr_key)
        selection = _selection_to_indices(tttr.get_selection_by_channel(selection_input))
        output = _write_selection_table(selection, "selection_channel", work_dir)
        return {"ok": True, "outputs": {"selection": output}, "log": "Channel selection extracted"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_selection_by_count_rate(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.get_selection_by_count_rate with a strict supported subset."""

    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    required = {"time_window", "n_ph_max"}
    allowed = required | {"invert"}
    extra = sorted(set(params) - allowed)
    if extra:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_selection_by_count_rate",
                f"unsupported params: {', '.join(extra)}",
            ),
        }
    missing = sorted(required - set(params))
    if missing:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_selection_by_count_rate", f"missing params: {', '.join(missing)}"
            ),
        }

    try:
        tttr = _load_tttr(tttr_key)
        selection = _selection_to_indices(
            tttr.get_selection_by_count_rate(
                params["time_window"],
                params["n_ph_max"],
                invert=params.get("invert", False),
            )
        )

        output = _write_selection_table(selection, "selection_rate", work_dir)
        return {
            "ok": True,
            "outputs": {"selection": output},
            "log": "Count-rate selection extracted",
        }
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_tttr_by_selection(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.get_tttr_by_selection with a list-based subset."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    allowed_params = {"selection"}
    extra = sorted(set(params) - allowed_params)
    if extra:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_tttr_by_selection", f"unsupported params: {', '.join(extra)}"
            ),
        }

    selection = params.get("selection")
    if not isinstance(selection, list) or not selection:
        return {
            "ok": False,
            "error": _unsupported_argument_pattern_error(
                "tttrlib.TTTR.get_tttr_by_selection", "selection must be a non-empty list"
            ),
        }

    try:
        tttr = _load_tttr(tttr_key)
        tttr_subset = tttr.get_tttr_by_selection(selection)
        fmt, suffix = _infer_tttr_format_and_suffix(tttr_ref)
        subset_path = work_dir / f"tttr_subset_{uuid.uuid4().hex[:8]}{suffix}"
        tttr_subset.write(str(subset_path))
        subset_ref_id, _uri = _store_tttr(tttr_subset, f"file://{subset_path.absolute()}")

        output = _build_tttr_file_output(subset_path, fmt, ref_id=subset_ref_id)
        return {"ok": True, "outputs": {"tttr": output}, "log": "TTTR subset selected"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_tttr_write(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.write - export TTTR data."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    filename = params.get("filename")

    if not filename:
        return {"ok": False, "error": {"message": "filename is required"}}

    try:
        tttr = _load_tttr(tttr_key)

        try:
            filepath = _resolve_output_path(filename, work_dir)
        except ValueError:
            return {"ok": False, "error": _export_path_error(filename)}

        canonical_format = _canonical_tttr_write_format(filepath)
        if canonical_format is None:
            return {
                "ok": False,
                "error": _tttr_write_subset_error(
                    "expected a supported TTTR export extension, "
                    f"got '{filepath.suffix or '<none>'}'"
                ),
            }

        write_result = tttr.write(str(filepath))
        if write_result is False or not filepath.exists():
            return {
                "ok": False,
                "error": _tttr_write_subset_error(
                    "source TTTR/container combination did not produce an export file"
                ),
            }

        output = _build_tttr_file_output(filepath, canonical_format)

        return {"ok": True, "outputs": {"tttr_out": output}, "log": f"TTTR written to {filename}"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_tttr_write_header(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.write_header - write header to output path."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    filename = params.get("filename")
    if not filename:
        return {"ok": False, "error": {"message": "filename is required"}}

    try:
        tttr = _load_tttr(tttr_key)
        try:
            filepath = _resolve_output_path(filename, work_dir)
        except ValueError:
            return {"ok": False, "error": _export_path_error(filename)}

        tttr.write_header(str(filepath))
        output = _build_tttr_file_output(
            filepath, filepath.suffix[1:].upper() if filepath.suffix else "auto"
        )
        return {"ok": True, "outputs": {"tttr_out": output}, "log": "TTTR header written"}
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_tttr_write_hht3v2_events(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.write_hht3v2_events export."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    filename = params.get("filename")
    if not filename:
        return {"ok": False, "error": {"message": "filename is required"}}

    try:
        tttr = _load_tttr(tttr_key)
        try:
            filepath = _resolve_output_path(filename, work_dir)
        except ValueError:
            return {"ok": False, "error": _export_path_error(filename)}

        extension_error = _validate_export_extension(
            "tttrlib.TTTR.write_hht3v2_events", filepath, {".ht3"}
        )
        if extension_error:
            return {"ok": False, "error": extension_error}

        tttr.write_hht3v2_events(str(filepath), tttr)
        output = _build_tttr_file_output(
            filepath, filepath.suffix[1:].upper() if filepath.suffix else "auto"
        )
        return {
            "ok": True,
            "outputs": {"tttr_out": output},
            "log": "HHT3v2 events written",
        }
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_tttr_write_spc132_events(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.write_spc132_events export."""
    tttr_ref = inputs.get("tttr", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""
    filename = params.get("filename")
    if not filename:
        return {"ok": False, "error": {"message": "filename is required"}}

    try:
        tttr = _load_tttr(tttr_key)
        try:
            filepath = _resolve_output_path(filename, work_dir)
        except ValueError:
            return {"ok": False, "error": _export_path_error(filename)}

        extension_error = _validate_export_extension(
            "tttrlib.TTTR.write_spc132_events", filepath, {".spc"}
        )
        if extension_error:
            return {"ok": False, "error": extension_error}

        tttr.write_spc132_events(str(filepath), tttr)
        output = _build_tttr_file_output(
            filepath, filepath.suffix[1:].upper() if filepath.suffix else "auto"
        )
        return {
            "ok": True,
            "outputs": {"tttr_out": output},
            "log": "SPC132 events written",
        }
    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_compute_ics(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.compute_ics - compute Image Correlation Spectroscopy."""
    import numpy as np
    import tttrlib

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    try:
        clsm = _load_object(clsm_key)

        subtract_average = params.get("subtract_average", "frame")
        if isinstance(subtract_average, bool):
            subtract_average = "frame" if subtract_average else ""

        ics_kwargs: dict[str, Any] = {
            "clsm": clsm,
            "subtract_average": subtract_average,
            "x_range": params.get("x_range", [0, -1]),
            "y_range": params.get("y_range", [0, -1]),
        }

        # Handle frames_index_pairs
        if "frames_index_pairs" in params:
            # Convert list of lists to list of tuples if needed
            ics_kwargs["frames_index_pairs"] = [tuple(p) for p in params["frames_index_pairs"]]
        else:
            # Default: autocorrelation for all frames
            n_frames = clsm.n_frames
            frame_range = range(n_frames)
            ics_kwargs["frames_index_pairs"] = list(zip(frame_range, frame_range, strict=True))

        # Static method call as per tttrlib docs
        ics_data = tttrlib.CLSMImage.compute_ics(**ics_kwargs)
        ics_data = np.asarray(ics_data)

        # Ensure we have at least 2D (YX) for OME-Zarr
        if ics_data.ndim < 2:
            ics_data = np.atleast_2d(ics_data)

        out_path = work_dir / f"ics_{uuid.uuid4().hex[:8]}.ome.zarr"
        from bioio_ome_zarr.writers import OMEZarrWriter

        dims_map = {2: "YX", 3: "ZYX", 4: "CZYX", 5: "TCZYX"}
        axes = dims_map.get(
            ics_data.ndim, "TCZYX"[-ics_data.ndim :] if ics_data.ndim <= 5 else "TCZYX"
        )
        axes_names = [d.lower() for d in axes]
        type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
        axes_types = [type_map.get(d, "space") for d in axes_names]

        writer = OMEZarrWriter(
            store=str(out_path),
            level_shapes=[ics_data.shape],
            dtype=ics_data.dtype,
            axes_names=axes_names,
            axes_types=axes_types,
            zarr_format=2,
        )
        writer.write_full_volume(ics_data)

        outputs: dict[str, Any] = {
            "ics": {
                "ref_id": uuid.uuid4().hex,
                "type": "BioImageRef",
                "uri": f"file://{out_path.absolute()}",
                "path": str(out_path.absolute()),
                "format": "OME-Zarr",
                "storage_type": "zarr-temp",
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": {
                    "axes": axes,
                    "dims": list(axes),
                    "shape": list(ics_data.shape),
                    "ndim": ics_data.ndim,
                    "dtype": str(ics_data.dtype),
                },
            }
        }

        if params.get("include_summary", False):
            summary_path = work_dir / f"ics_summary_{uuid.uuid4().hex[:8]}.csv"
            rows = [
                ("subtract_average", str(subtract_average)),
                ("x_range", json.dumps(ics_kwargs["x_range"])),
                ("y_range", json.dumps(ics_kwargs["y_range"])),
                ("shape", json.dumps(list(ics_data.shape))),
                ("dtype", str(ics_data.dtype)),
            ]
            with open(summary_path, "w") as f:
                f.write("metric,value\n")
                for metric, value in rows:
                    f.write(f"{metric},{value}\n")

            outputs["summary"] = {
                "ref_id": uuid.uuid4().hex,
                "type": "TableRef",
                "uri": f"file://{summary_path.absolute()}",
                "path": str(summary_path.absolute()),
                "format": "csv",
                "created_at": datetime.now(UTC).isoformat(),
                "columns": ["metric", "value"],
                "row_count": len(rows),
            }

        return {"ok": True, "outputs": outputs, "log": "ICS computed"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_intensity(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_intensity - extract intensity image."""
    import numpy as np

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    try:
        clsm = _load_object(clsm_key)

        # Get intensity array from CLSMImage
        # tttrlib API: CLSMImage.get_intensity() -> (n_frames, n_lines, n_pixel)
        intensity = np.asarray(clsm.get_intensity())

        stack_frames = params.get("stack_frames", False)
        if stack_frames:
            # Sum across frames to get 2D image
            intensity = intensity.sum(axis=0)

        # tttrlib returns uint64, and sum() might result in uint64.
        # OME-TIFF supports up to uint32.
        intensity = intensity.astype(np.uint32)

        # Squeeze leading singletons (e.g. T=1)
        while intensity.ndim > 2 and intensity.shape[0] == 1:
            intensity = np.squeeze(intensity, axis=0)

        if intensity.ndim == 2:
            dim_order = "YX"
            dims = ["Y", "X"]
        elif intensity.ndim == 3:
            dim_order = "ZYX"
            dims = ["Z", "Y", "X"]
        else:
            dims = list("TCZYX"[-intensity.ndim :])
            dim_order = "".join(dims)

        out_path = work_dir / f"intensity_{uuid.uuid4().hex[:8]}.ome.zarr"
        from bioio_ome_zarr.writers import OMEZarrWriter

        axes_names = [d.lower() for d in dim_order]
        type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
        axes_types = [type_map.get(d, "space") for d in axes_names]

        writer = OMEZarrWriter(
            store=str(out_path),
            level_shapes=[intensity.shape],
            dtype=intensity.dtype,
            axes_names=axes_names,
            axes_types=axes_types,
            zarr_format=2,
        )
        writer.write_full_volume(intensity)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-Zarr",
            "storage_type": "zarr-temp",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "dims": dims,
                "shape": list(intensity.shape),
                "ndim": intensity.ndim,
                "dtype": str(intensity.dtype),
            },
        }

        return {"ok": True, "outputs": {"intensity": output}, "log": "Intensity extracted"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_phasor(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_phasor - compute phasor image."""
    import numpy as np

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    tttr_ref = inputs.get("tttr_data", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    tttr_irf_ref = inputs.get("tttr_irf")

    try:
        clsm = _load_object(clsm_key)
        tttr_data = _load_tttr(tttr_key)

        # Prepare IRF if provided
        tttr_irf = None
        if tttr_irf_ref:
            irf_key = tttr_irf_ref.get("uri") or tttr_irf_ref.get("ref_id") or ""
            if irf_key:
                tttr_irf = _load_tttr(irf_key)

        phasor_kwargs = {
            "tttr_data": tttr_data,
            "frequency": params.get("frequency", -1.0),
            "minimum_number_of_photons": params.get("minimum_number_of_photons", 2),
            "stack_frames": params.get("stack_frames", False),
        }
        if tttr_irf is not None:
            phasor_kwargs["tttr_irf"] = tttr_irf

        # get_phasor returns array with last dim being [g, s]
        phasor_data = clsm.get_phasor(**phasor_kwargs)
        phasor_data = np.asarray(phasor_data, dtype=np.float32)

        # Move g/s coordinates to front as channels
        phasor_data = np.moveaxis(phasor_data, -1, 0)

        # Squeeze leading singletons (e.g. T=1) except C, Y, X
        while phasor_data.ndim > 3 and phasor_data.shape[1] == 1:
            phasor_data = np.squeeze(phasor_data, axis=1)

        if phasor_data.ndim == 3:  # (C, Y, X)
            dim_order = "CYX"
            dims = ["C", "Y", "X"]
        elif phasor_data.ndim == 4:  # (C, Z, Y, X)
            dim_order = "CZYX"
            dims = ["C", "Z", "Y", "X"]
        else:
            dims = list("TCZYX"[-phasor_data.ndim :])
            dim_order = "".join(dims)

        out_path = work_dir / f"phasor_{uuid.uuid4().hex[:8]}.ome.zarr"
        from bioio_ome_zarr.writers import OMEZarrWriter

        axes_names = [d.lower() for d in dims]
        type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
        axes_types = [type_map.get(d, "space") for d in axes_names]

        writer = OMEZarrWriter(
            store=str(out_path),
            level_shapes=[phasor_data.shape],
            dtype=phasor_data.dtype,
            axes_names=axes_names,
            axes_types=axes_types,
            zarr_format=2,
        )
        writer.write_full_volume(phasor_data)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-Zarr",
            "storage_type": "zarr-temp",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "dims": dims,
                "shape": list(phasor_data.shape),
                "ndim": phasor_data.ndim,
                "dtype": str(phasor_data.dtype),
                "channel_names": ["g", "s"],
                "frequency_mhz": params.get("frequency", -1.0),
            },
        }

        sys.stderr.write(
            f"DEBUG tttrlib: returning output with axes={output['metadata']['axes']}\n"
        )
        sys.stderr.flush()

        return {"ok": True, "outputs": {"phasor": output}, "log": "Phasor computed"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_fluorescence_decay(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_fluorescence_decay - extract decay histogram per pixel."""
    import numpy as np
    from bioio_ome_zarr.writers import OMEZarrWriter

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    tttr_ref = inputs.get("tttr_data", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    try:
        clsm = _load_object(clsm_key)
        tttr_data = _load_tttr(tttr_key)

        decay_kwargs = {
            "tttr_data": tttr_data,
            "micro_time_coarsening": params.get("micro_time_coarsening", 1),
            "stack_frames": params.get("stack_frames", False),
        }

        # get_fluorescence_decay returns (Y, X, bins) or (Z, Y, X, bins)
        decay_data = clsm.get_fluorescence_decay(**decay_kwargs)
        decay_data = np.asarray(decay_data, dtype=np.float32)

        # Move bins axis to front: (Y, X, bins) -> (bins, Y, X)
        # or (Z, Y, X, bins) -> (bins, Z, Y, X)
        decay_data = np.moveaxis(decay_data, -1, 0)

        micro_time_coarsening = params.get("micro_time_coarsening", 1)

        if decay_data.ndim == 3:  # (bins, Y, X)
            axes_names = ["bins", "y", "x"]
            axes_types = ["other", "space", "space"]
            dims = ["bins", "Y", "X"]
        elif decay_data.ndim == 4:  # (bins, Z, Y, X)
            axes_names = ["bins", "z", "y", "x"]
            axes_types = ["other", "space", "space", "space"]
            dims = ["bins", "Z", "Y", "X"]
        else:
            return {
                "ok": False,
                "error": {
                    "message": f"Unexpected decay ndim={decay_data.ndim} shape={decay_data.shape}"
                },
            }

        out_path = work_dir / f"decay_{uuid.uuid4().hex[:8]}.ome.zarr"

        writer = OMEZarrWriter(
            store=str(out_path),
            level_shapes=[decay_data.shape],
            dtype=decay_data.dtype,
            axes_names=axes_names,
            axes_types=axes_types,
            zarr_format=2,  # Zarr v2 for OME-Zarr v0.4 compatibility
        )
        writer.write_full_volume(decay_data)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-Zarr",
            "storage_type": "zarr-temp",
            "mime_type": "application/zarr+ome",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "dims": dims,
                "shape": list(decay_data.shape),
                "ndim": decay_data.ndim,
                "dtype": str(decay_data.dtype),
                "axis_roles": {"bins": "microtime_histogram"},
                "micro_time_coarsening": micro_time_coarsening,
                "n_microtime_bins": decay_data.shape[0],
            },
        }

        return {"ok": True, "outputs": {"decay": output}, "log": "Decay extracted"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_get_mean_lifetime(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.get_mean_lifetime - compute lifetime image."""
    import numpy as np

    clsm_ref = inputs.get("clsm", {})
    clsm_key = clsm_ref.get("uri") or clsm_ref.get("ref_id") or ""

    tttr_ref = inputs.get("tttr_data", {})
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    tttr_irf_ref = inputs.get("tttr_irf")

    try:
        clsm = _load_object(clsm_key)
        tttr_data = _load_tttr(tttr_key)

        lifetime_kwargs = {
            "tttr_data": tttr_data,
            "minimum_number_of_photons": params.get("minimum_number_of_photons", 3),
            "stack_frames": params.get("stack_frames", False),
        }

        # IRF for accurate lifetime calculation
        if tttr_irf_ref:
            irf_key = tttr_irf_ref.get("uri") or tttr_irf_ref.get("ref_id") or ""
            if irf_key:
                lifetime_kwargs["tttr_irf"] = _load_tttr(irf_key)

        # get_mean_lifetime returns (Z, Y, X) in nanoseconds
        lifetime_data = clsm.get_mean_lifetime(**lifetime_kwargs)
        lifetime_data = np.asarray(lifetime_data, dtype=np.float32)

        # Squeeze leading singletons (e.g. T=1)
        while lifetime_data.ndim > 2 and lifetime_data.shape[0] == 1:
            lifetime_data = np.squeeze(lifetime_data, axis=0)

        if lifetime_data.ndim == 2:
            dim_order = "YX"
            dims = ["Y", "X"]
        elif lifetime_data.ndim == 3:
            dim_order = "ZYX"
            dims = ["Z", "Y", "X"]
        else:
            dims = list("TCZYX"[-lifetime_data.ndim :])
            dim_order = "".join(dims)

        out_path = work_dir / f"lifetime_{uuid.uuid4().hex[:8]}.ome.zarr"
        from bioio_ome_zarr.writers import OMEZarrWriter

        axes_names = [d.lower() for d in dims]
        type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
        axes_types = [type_map.get(d, "space") for d in axes_names]

        writer = OMEZarrWriter(
            store=str(out_path),
            level_shapes=[lifetime_data.shape],
            dtype=lifetime_data.dtype,
            axes_names=axes_names,
            axes_types=axes_types,
            zarr_format=2,
        )
        writer.write_full_volume(lifetime_data)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-Zarr",
            "storage_type": "zarr-temp",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "dims": dims,
                "shape": list(lifetime_data.shape),
                "ndim": lifetime_data.ndim,
                "dtype": str(lifetime_data.dtype),
                "unit": "nanoseconds",
            },
        }

        return {"ok": True, "outputs": {"lifetime": output}, "log": "Lifetime computed"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


# Function dispatch table
FUNCTION_HANDLERS = {
    "tttrlib.TTTR": handle_tttr_open,
    "tttrlib.TTTR.header": handle_tttr_header,
    "tttrlib.TTTR.get_count_rate": handle_get_count_rate,
    "tttrlib.TTTR.get_intensity_trace": handle_get_intensity_trace,
    "tttrlib.TTTR.get_selection_by_channel": handle_get_selection_by_channel,
    "tttrlib.TTTR.get_selection_by_count_rate": handle_get_selection_by_count_rate,
    "tttrlib.TTTR.get_tttr_by_selection": handle_get_tttr_by_selection,
    "tttrlib.TTTR.get_time_window_ranges": handle_get_time_window_ranges,
    "tttrlib.TTTR.write": handle_tttr_write,
    "tttrlib.TTTR.write_header": handle_tttr_write_header,
    "tttrlib.TTTR.write_hht3v2_events": handle_tttr_write_hht3v2_events,
    "tttrlib.TTTR.write_spc132_events": handle_tttr_write_spc132_events,
    "tttrlib.CLSMImage": handle_clsm_image,
    "tttrlib.CLSMImage.compute_ics": handle_compute_ics,
    "tttrlib.CLSMImage.get_image_info": handle_clsm_get_image_info,
    "tttrlib.CLSMImage.get_intensity": handle_get_intensity,
    "tttrlib.CLSMImage.get_settings": handle_clsm_get_settings,
    "tttrlib.CLSMImage.get_phasor": handle_get_phasor,
    "tttrlib.CLSMImage.get_fluorescence_decay": handle_get_fluorescence_decay,
    "tttrlib.CLSMImage.get_mean_lifetime": handle_get_mean_lifetime,
    "tttrlib.Correlator": handle_correlator,
    "tttrlib.Correlator.get_curve": handle_correlator_get_curve,
    "tttrlib.Correlator.get_x_axis": handle_correlator_get_x_axis,
    "tttrlib.Correlator.get_corr": handle_correlator_get_corr,
}


def process_execute_request(request: dict[str, Any]) -> dict[str, Any]:
    """Process an execute request."""
    fn_id = request.get("id") or request.get("fn_id", "")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)
    ordinal = request.get("ordinal")

    try:
        coverage_entry = _get_coverage_entry(fn_id)
        coverage_status = str(coverage_entry.get("status")) if coverage_entry else ""

        if coverage_status in UNSUPPORTED_STATUSES:
            response = {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "error": _unsupported_method_error(fn_id, coverage_entry),
            }
        elif fn_id in FUNCTION_HANDLERS:
            handler = FUNCTION_HANDLERS[fn_id]
            result = handler(inputs, params, work_dir)

            if result.get("ok"):
                response = {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": result.get("outputs", {}),
                    "log": result.get("log", "ok"),
                }
            else:
                response = {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": result.get("error", {"message": "Unknown error"}),
                }
        else:
            response = {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "error": {"message": f"Unknown function: {fn_id}"},
            }
    except Exception as e:
        response = {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"message": str(e)},
            "log": traceback.format_exc(),
        }
    response["id"] = fn_id
    return response


def main() -> int:
    """Main entrypoint."""
    is_persistent_mode = "BIOIMAGE_MCP_SESSION_ID" in os.environ

    # Initialize worker
    session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
    env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", TOOL_ENV_NAME)
    _initialize_worker(session_id, env_id)

    # Verify tttrlib import
    try:
        import tttrlib  # noqa: F401
    except ImportError as e:
        error_json = {
            "command": "error",
            "ok": False,
            "error": {"code": "IMPORT_FAILED", "message": str(e)},
        }
        print(json.dumps(error_json), flush=True)
        return 1

    if is_persistent_mode:
        # NDJSON persistent mode
        print(
            json.dumps({"command": "ready", "status": "complete", "version": TOOL_VERSION}),
            flush=True,
        )

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                print(
                    json.dumps(
                        {"command": "error", "ok": False, "error": {"message": "Invalid JSON"}}
                    ),
                    flush=True,
                )
                continue

            if request.get("command") == "execute":
                response = process_execute_request(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "shutdown":
                _TTTR_CACHE.clear()
                _OBJECT_CACHE.clear()
                print(
                    json.dumps(
                        {"command": "shutdown_ack", "ok": True, "ordinal": request.get("ordinal")}
                    ),
                    flush=True,
                )
                break
        return 0
    else:
        # Single request mode
        raw_input = sys.stdin.read()
        if not raw_input:
            return 0
        try:
            request = json.loads(raw_input)
        except json.JSONDecodeError:
            print(
                json.dumps({"command": "error", "ok": False, "error": {"message": "Invalid JSON"}})
            )
            return 1

        if "command" in request and request.get("command") == "execute":
            response = process_execute_request(request)
        else:
            # Legacy format
            response = process_execute_request(
                {
                    "id": request.get("id") or request.get("fn_id"),
                    "params": request.get("params"),
                    "inputs": request.get("inputs"),
                    "work_dir": request.get("work_dir"),
                }
            )
        print(json.dumps(response))
        return 0 if response.get("ok") else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
