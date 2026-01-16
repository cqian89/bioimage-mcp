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


def _load_tttr(ref_id_or_uri: str) -> Any:
    """Load TTTR object from cache."""
    # Try direct ref_id lookup
    if ref_id_or_uri in _TTTR_CACHE:
        return _TTTR_CACHE[ref_id_or_uri]["obj"]
    # Try URI lookup
    for _ref_id, data in _TTTR_CACHE.items():
        if data["uri"] == ref_id_or_uri:
            return data["obj"]

    # If it's a file URI but not in cache, try opening it
    if ref_id_or_uri.startswith("file://"):
        import tttrlib

        path = ref_id_or_uri[7:]
        tttr = tttrlib.TTTR(path)
        _store_tttr(tttr, ref_id_or_uri)
        return tttr

    raise KeyError(f"TTTR object not found: {ref_id_or_uri}")


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
    tttr_key = tttr_ref.get("uri") or tttr_ref.get("ref_id") or ""

    try:
        tttr = _load_tttr(tttr_key)

        # Reconstruct image from TTTR data
        clsm_kwargs = {
            "tttr_data": tttr,
            "reading_routine": params.get("reading_routine", "SP5"),
            "marker_frame_start": params.get("marker_frame_start", [4]),
            "marker_line_start": params.get("marker_line_start", 2),
            "marker_line_stop": params.get("marker_line_stop", 3),
            "channels": params.get("channels", [0]),
            "fill": params.get("fill", True),
        }

        # Add optional parameters if present
        for key in [
            "n_pixel_per_line",
            "n_lines",
            "n_frames",
            "skip_before_first_frame_marker",
        ]:
            if key in params:
                clsm_kwargs[key] = params[key]

        clsm = tttrlib.CLSMImage(**clsm_kwargs)

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

        # Save to CSV
        csv_path = work_dir / f"correlation_{uuid.uuid4().hex[:8]}.csv"
        data = np.column_stack((x, y))
        np.savetxt(csv_path, data, delimiter=",", header="tau,correlation", comments="")

        curve = {
            "ref_id": uuid.uuid4().hex,
            "type": "TableRef",
            "uri": f"file://{csv_path.absolute()}",
            "path": str(csv_path.absolute()),
            "format": "csv",
            "created_at": datetime.now(UTC).isoformat(),
            "columns": ["tau", "correlation"],
            "row_count": len(x),
            "metadata": {
                "columns": [
                    {"name": "tau", "dtype": "float64"},
                    {"name": "correlation", "dtype": "float64"},
                ],
                "row_count": len(x),
            },
        }

        return {
            "ok": True,
            "outputs": {"curve": curve},
            "log": "Correlation computed",
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

        filepath = Path(filename)
        if not filepath.is_absolute():
            filepath = work_dir / filepath

        tttr.write(str(filepath))

        ext = filepath.suffix.lower()
        if ext in {".h5", ".hdf5"}:
            fmt = "PHOTON-HDF5"
        else:
            fmt = filepath.suffix[1:].upper() if filepath.suffix else "auto"

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "TTTRRef",
            "uri": f"file://{filepath.absolute()}",
            "path": str(filepath.absolute()),
            "format": fmt,
            "storage_type": "file",
            "created_at": datetime.now(UTC).isoformat(),
        }

        return {"ok": True, "outputs": {"tttr_out": output}, "log": f"TTTR written to {filename}"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_compute_ics(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage.compute_ics - compute Image Correlation Spectroscopy."""
    import numpy as np
    import tttrlib
    from bioio.writers import OmeTiffWriter

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

        # Ensure we have at least 2D (YX) for OmeTiffWriter
        if ics_data.ndim < 2:
            ics_data = np.atleast_2d(ics_data)

        out_path = work_dir / f"ics_{uuid.uuid4().hex[:8]}.ome.tif"
        ndim_map = {2: "YX", 3: "ZYX", 4: "CZYX", 5: "TCZYX"}
        dim_order = ndim_map.get(
            ics_data.ndim, "TCZYX"[-ics_data.ndim :] if ics_data.ndim <= 5 else "TCZYX"
        )
        OmeTiffWriter.save(ics_data, str(out_path), dim_order=dim_order)

        outputs: dict[str, Any] = {
            "ics": {
                "ref_id": uuid.uuid4().hex,
                "type": "BioImageRef",
                "uri": f"file://{out_path.absolute()}",
                "path": str(out_path.absolute()),
                "format": "OME-TIFF",
                "created_at": datetime.now(UTC).isoformat(),
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
    from bioio.writers import OmeTiffWriter

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
            dim_order = "YX"
        else:
            dim_order = "ZYX"  # Frames as Z

        # Ensure YX are at the end for OmeTiffWriter
        if intensity.ndim == 3 and dim_order == "ZYX":
            # Already ZYX, which is fine as YX are at the end
            pass

        out_path = work_dir / f"intensity_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(intensity, str(out_path), dim_order=dim_order)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(intensity.shape),
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
    from bioio.writers import OmeTiffWriter

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

        # Determine dimension order based on shape.
        # tttrlib returns (frames, lines, pixels, 2) or (lines, pixels, 2) if stacked,
        # where the last axis contains the phasor coordinates [g, s].
        # Store g/s as channels to preserve semantics.
        if phasor_data.ndim == 3:  # (Y, X, 2) - stacked
            phasor_data = np.moveaxis(phasor_data, -1, 0)  # (C, Y, X)
            dim_order = "CYX"
        elif phasor_data.ndim == 4:  # (Z, Y, X, 2)
            phasor_data = np.moveaxis(phasor_data, -1, 0)  # (C, Z, Y, X)
            dim_order = "CZYX"
        else:
            return {
                "ok": False,
                "error": {
                    "message": (
                        f"Unexpected phasor ndim={phasor_data.ndim} shape={phasor_data.shape}"
                    )
                },
            }

        out_path = work_dir / f"phasor_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(phasor_data, str(out_path), dim_order=dim_order)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(phasor_data.shape),
                "dtype": str(phasor_data.dtype),
                "channel_names": ["g", "s"],
                "frequency_mhz": params.get("frequency", -1.0),
            },
        }

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

        micro_time_coarsening = params.get("micro_time_coarsening", 1)

        # Keep native tttrlib output order - no moveaxis needed!
        # tttrlib returns (Y, X, bins) or (Z, Y, X, bins)
        if decay_data.ndim == 3:  # (Y, X, B)
            axes_names = ["y", "x", "b"]
            axes_types = ["space", "space", "other"]
            dims = ["Y", "X", "B"]
        elif decay_data.ndim == 4:  # (Z, Y, X, B)
            axes_names = ["z", "y", "x", "b"]
            axes_types = ["space", "space", "space", "other"]
            dims = ["Z", "Y", "X", "B"]
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
                "axis_roles": {"B": "microtime_histogram"},
                "micro_time_coarsening": micro_time_coarsening,
                "n_microtime_bins": decay_data.shape[-1],
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
    from bioio.writers import OmeTiffWriter

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

        dim_order = "YX" if lifetime_data.ndim == 2 else "ZYX"

        out_path = work_dir / f"lifetime_{uuid.uuid4().hex[:8]}.ome.tif"
        OmeTiffWriter.save(lifetime_data, str(out_path), dim_order=dim_order)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "BioImageRef",
            "uri": f"file://{out_path.absolute()}",
            "path": str(out_path.absolute()),
            "format": "OME-TIFF",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "axes": dim_order,
                "shape": list(lifetime_data.shape),
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
    "tttrlib.TTTR.get_time_window_ranges": handle_get_time_window_ranges,
    "tttrlib.TTTR.write": handle_tttr_write,
    "tttrlib.CLSMImage": handle_clsm_image,
    "tttrlib.CLSMImage.compute_ics": handle_compute_ics,
    "tttrlib.CLSMImage.get_intensity": handle_get_intensity,
    "tttrlib.CLSMImage.get_phasor": handle_get_phasor,
    "tttrlib.CLSMImage.get_fluorescence_decay": handle_get_fluorescence_decay,
    "tttrlib.CLSMImage.get_mean_lifetime": handle_get_mean_lifetime,
    "tttrlib.Correlator": handle_correlator,
}


def process_execute_request(request: dict[str, Any]) -> dict[str, Any]:
    """Process an execute request."""
    fn_id = request.get("fn_id", "")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)
    ordinal = request.get("ordinal")

    try:
        if fn_id in FUNCTION_HANDLERS:
            handler = FUNCTION_HANDLERS[fn_id]
            result = handler(inputs, params, work_dir)

            if result.get("ok"):
                return {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": result.get("outputs", {}),
                    "log": result.get("log", "ok"),
                }
            else:
                return {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": result.get("error", {"message": "Unknown error"}),
                }
        else:
            return {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "error": {"message": f"Unknown fn_id: {fn_id}"},
            }
    except Exception as e:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"message": str(e)},
            "log": traceback.format_exc(),
        }


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
                    "fn_id": request.get("fn_id"),
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
