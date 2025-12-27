from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from bioimage_mcp_base.utils import load_image, resolve_axis, save_zarr, uri_to_path


class ToolInputError(ValueError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def _assert_read_allowed(path: Path) -> None:
    allowlist = os.environ.get("BIOIMAGE_MCP_FS_ALLOWLIST_READ")
    if not allowlist:
        return

    try:
        roots = json.loads(allowlist)
    except json.JSONDecodeError:
        return

    target = path.expanduser().absolute()
    for root in roots:
        root_path = Path(root).expanduser().absolute()
        try:
            target.relative_to(root_path)
            return
        except ValueError:
            continue

    raise PermissionError(f"Path not under allowlist read roots: {target}")


def resize(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.transform import resize as sk_resize

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    output_shape = params.get("output_shape")
    if output_shape is None:
        raise ValueError("'output_shape' is required")

    preserve_range = bool(params.get("preserve_range", True))
    anti_aliasing = bool(params.get("anti_aliasing", True))

    data = load_image(uri_to_path(str(uri)))
    resized = sk_resize(
        data,
        output_shape=tuple(output_shape),
        preserve_range=preserve_range,
        anti_aliasing=anti_aliasing,
    )
    return save_zarr(resized, work_dir, "resized.ome.zarr")


def rescale(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.transform import rescale as sk_rescale

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    scale = params.get("scale")
    if scale is None:
        raise ValueError("'scale' is required")

    preserve_range = bool(params.get("preserve_range", True))
    anti_aliasing = bool(params.get("anti_aliasing", True))

    data = load_image(uri_to_path(str(uri)))
    rescaled = sk_rescale(
        data,
        scale=scale,
        preserve_range=preserve_range,
        anti_aliasing=anti_aliasing,
    )
    return save_zarr(rescaled, work_dir, "rescaled.ome.zarr")


def rotate(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    from skimage.transform import rotate as sk_rotate

    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    angle = params.get("angle")
    if angle is None:
        raise ValueError("'angle' is required")

    resize = bool(params.get("resize", False))
    preserve_range = bool(params.get("preserve_range", True))

    data = load_image(uri_to_path(str(uri)))
    rotated = sk_rotate(data, angle=float(angle), resize=resize, preserve_range=preserve_range)
    return save_zarr(rotated, work_dir, "rotated.ome.zarr")


def flip(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis")
    if axis is None:
        raise ValueError("'axis' is required")

    data = load_image(uri_to_path(str(uri)))
    idx = resolve_axis(axis, data.ndim)
    flipped = np.flip(data, axis=idx)
    return save_zarr(flipped, work_dir, "flipped.ome.zarr")


def crop(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    start = params.get("start")
    stop = params.get("stop")
    if start is None or stop is None:
        raise ValueError("'start' and 'stop' are required")

    data = load_image(uri_to_path(str(uri)))
    if len(start) != data.ndim or len(stop) != data.ndim:
        raise ValueError("'start' and 'stop' must match image dimensions")

    slices = tuple(slice(int(s), int(e)) for s, e in zip(start, stop, strict=True))
    cropped = data[slices]
    return save_zarr(cropped, work_dir, "cropped.ome.zarr")


def pad(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    pad_width = params.get("pad_width")
    if pad_width is None:
        raise ValueError("'pad_width' is required")

    mode = params.get("mode", "constant")
    constant_values = params.get("constant_values", 0)

    data = load_image(uri_to_path(str(uri)))
    padded = np.pad(data, pad_width=pad_width, mode=mode, constant_values=constant_values)
    return save_zarr(padded, work_dir, "padded.ome.zarr")


def project_sum(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", 0)
    path = uri_to_path(str(uri))
    _assert_read_allowed(path)
    data = load_image(path)
    idx = resolve_axis(axis, data.ndim)
    projected = np.sum(data, axis=idx)
    return save_zarr(projected, work_dir, "project_sum.ome.zarr")


def project_max(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    axis = params.get("axis", 0)
    data = load_image(uri_to_path(str(uri)))
    idx = resolve_axis(axis, data.ndim)
    projected = np.max(data, axis=idx)
    return save_zarr(projected, work_dir, "project_max.ome.zarr")


OVERSIZED_INPUT_THRESHOLD_BYTES = 4 * 1024**3


def _extract_time_increment(image: Any) -> float | None:
    for attr in ("time_increment", "time_interval"):
        value = getattr(image, attr, None)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    ome = getattr(image, "ome_metadata", None)
    if ome is None:
        return None

    images = getattr(ome, "images", None)
    if images is None:
        image_obj = getattr(ome, "image", None)
        if image_obj is None:
            return None
        images = [image_obj]

    if not images:
        return None

    pixels = getattr(images[0], "pixels", None)
    if pixels is None:
        return None

    value = getattr(pixels, "time_increment", None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_flim_data(image_ref: dict) -> tuple[np.ndarray, str, dict, int, list[dict[str, str]]]:
    """Load FLIM data from an image reference.

    Returns:
        Tuple of (data, axes, metadata, size_bytes, warnings) where warnings
        is a list of warning dicts with 'code' and 'message' keys.
    """
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'dataset' must include uri")

    path = uri_to_path(str(uri))
    if not path.exists():
        raise FileNotFoundError(f"Input dataset not found: {path}")

    fmt = (image_ref.get("format") or "").lower()
    if "zarr" in fmt or path.suffix.lower() == ".zarr":
        raise ValueError(
            "OME-Zarr format is not supported. Convert to OME-TIFF first (base.export_ome_tiff)."
        )
    if fmt and "tiff" not in fmt:
        raise ValueError(f"Unsupported input format: {image_ref.get('format')}")
    if not fmt and path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Input must be an OME-TIFF (.tif/.tiff) file")

    # Try BioImage first, fallback to tifffile for datasets with problematic OME-XML
    img = None
    data = None
    axes = ""
    metadata: dict[str, Any] = {}
    load_warnings: list[dict[str, str]] = []
    used_tifffile_fallback = False

    try:
        from bioio import BioImage  # type: ignore

        img = BioImage(str(path))
        data = img.get_image_data()  # type: ignore[attr-defined]
        axes = getattr(img, "axes", "") or getattr(getattr(img, "dims", None), "order", "")
        time_increment = _extract_time_increment(img)
        if time_increment is not None:
            metadata["time_increment"] = time_increment
    except Exception as exc:
        # Fallback: use tifffile for datasets with incompatible OME-XML metadata
        import tifffile

        used_tifffile_fallback = True
        load_warnings.append(
            {
                "code": "TIFFFILE_FALLBACK",
                "message": (
                    f"BioImage failed to load file ({type(exc).__name__}); "
                    "using tifffile fallback. Metadata may be incomplete."
                ),
            }
        )

        data = tifffile.imread(str(path))
        # Try to extract axes from tifffile metadata
        with tifffile.TiffFile(str(path)) as tif:
            if tif.ome_metadata:
                try:
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(tif.ome_metadata)
                    pixels = root.find(".//{*}Pixels")
                    if pixels is not None:
                        dim_order = pixels.get("DimensionOrder", "")
                        if dim_order:
                            # DimensionOrder is like XYZCT; reverse for array order
                            axes = dim_order[::-1]
                except Exception:
                    pass
            if not axes and tif.pages and hasattr(tif.pages[0], "axes"):
                axes = tif.pages[0].axes or ""

    # Override axes from image_ref metadata if provided
    axes_from_ref = (image_ref.get("metadata") or {}).get("axes", "")
    if axes_from_ref:
        axes = axes_from_ref
    elif not axes:
        axes = ""

    if axes and len(axes) > data.ndim:
        trimmed_axes = axes[-data.ndim :]
        if trimmed_axes != axes:
            load_warnings.append(
                {
                    "code": "AXES_TRIMMED",
                    "message": (
                        "Axis metadata includes singleton dimensions not present in the array; "
                        f"trimmed '{axes}' to '{trimmed_axes}'."
                    ),
                }
            )
            axes = trimmed_axes
            metadata["_axes_trimmed"] = True

    axes_inferred = False
    inferred_axes = ""
    if not axes or len(axes) != data.ndim:
        # Attempt to infer axes based on common FLIM data patterns
        # Typical FLIM: TCZYX or TCYX where T is time bins
        axes_inferred = True
        if data.ndim == 5:
            inferred_axes = "TCZYX"
        elif data.ndim == 4:
            inferred_axes = "TCYX"
        elif data.ndim == 3:
            inferred_axes = "TYX"
        elif data.ndim == 2:
            inferred_axes = "YX"
        else:
            raise ValueError(
                f"Cannot infer axes for {data.ndim}D data. "
                "Provide explicit axis metadata via input metadata or time_axis parameter."
            )
        load_warnings.append(
            {
                "code": "AXES_INFERRED",
                "message": (
                    f"Axis metadata missing or mismatched; "
                    f"inferred '{inferred_axes}' from shape {data.shape}. "
                    "This may be incorrect for non-standard FLIM layouts. "
                    "Provide explicit 'time_axis' parameter or input metadata "
                    "to ensure correct interpretation."
                ),
            }
        )
        axes = inferred_axes

    # Record provenance about loading method
    metadata["_load_method"] = "tifffile" if used_tifffile_fallback else "bioio"
    if axes_inferred:
        metadata["_axes_inferred"] = True
        metadata["_inferred_axes"] = inferred_axes

    size_bytes = int(image_ref.get("size_bytes") or path.stat().st_size or data.nbytes)
    return data, axes.upper(), metadata, size_bytes, load_warnings


def _resolve_time_axis(
    time_axis: str | int | None,
    axes: str,
    ndim: int,
) -> tuple[int, str]:
    if time_axis is None:
        if axes.count("T") == 1:
            idx = axes.index("T")
            return idx, "T"
        raise ValueError("Time axis is missing or ambiguous; provide 'time_axis' override")

    if isinstance(time_axis, str):
        axis_name = time_axis.upper()
        if axis_name not in axes:
            raise ValueError(f"Unknown time_axis '{time_axis}' for axes '{axes}'")
        return axes.index(axis_name), axis_name

    idx = int(time_axis)
    if idx < 0:
        idx += ndim
    if idx < 0 or idx >= ndim:
        raise ValueError(f"time_axis index {time_axis} out of bounds for ndim={ndim}")
    axis_name = axes[idx] if axes else str(idx)
    return idx, axis_name


def _infer_sample_phase(metadata: dict, n_bins: int) -> tuple[np.ndarray | None, str]:
    time_increment = metadata.get("time_increment")
    if time_increment is not None:
        times = np.arange(n_bins, dtype="float32") * float(time_increment)
        span = float(times[-1] - times[0]) if n_bins > 1 else 0.0
        if span > 0:
            phase = 2 * np.pi * (times - times[0]) / span
            return phase, "physical"
    return None, "uniform"


def _remove_axis(axes: str, axis_index: int) -> str:
    if not axes or axis_index < 0 or axis_index >= len(axes):
        return axes
    return axes[:axis_index] + axes[axis_index + 1 :]


def _compute_phasor(
    signal: np.ndarray,
    time_axis: int,
    harmonic: int,
    sample_phase: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    try:
        import inspect

        from phasorpy.phasor import phasor_from_signal
    except Exception as exc:
        raise RuntimeError("Missing dependencies for phasor_from_flim") from exc

    kwargs: dict[str, Any] = {}
    sig = inspect.signature(phasor_from_signal)
    if "axis" in sig.parameters:
        kwargs["axis"] = time_axis
    if "harmonic" in sig.parameters:
        kwargs["harmonic"] = harmonic
    elif "harmonics" in sig.parameters:
        kwargs["harmonics"] = harmonic
    if sample_phase is not None and "sample_phase" in sig.parameters:
        kwargs["sample_phase"] = sample_phase

    result = phasor_from_signal(signal, **kwargs)
    if isinstance(result, tuple) and len(result) >= 2:
        return result[0], result[1]
    raise RuntimeError("phasor_from_signal returned unexpected output")


def _write_ome_tiff(
    array: np.ndarray,
    work_dir: Path,
    name: str,
    axes: str,
) -> Path:
    import tifffile

    out_path = work_dir / name
    if out_path.exists():
        raise FileExistsError(out_path)

    tifffile.imwrite(
        str(out_path),
        array,
        compression="zlib",
        photometric="minisblack",
        metadata={"axes": axes},
    )
    return out_path


def phasor_from_flim(*, inputs: dict, params: dict, work_dir: Path) -> dict[str, Any]:
    dataset_ref = inputs.get("dataset") or {}
    data, axes, metadata, size_bytes, load_warnings = _load_flim_data(dataset_ref)

    if "X" not in axes or "Y" not in axes:
        raise ValueError("Input dataset must include spatial X/Y axes")

    time_axis_param = params.get("time_axis")
    time_axis_idx, time_axis_name = _resolve_time_axis(time_axis_param, axes, data.ndim)

    n_time_samples = int(data.shape[time_axis_idx])
    if n_time_samples < 2:
        raise ToolInputError(
            "Time axis must have at least 2 samples for phasor calculation",
            "AXIS_SAMPLES_ERROR",
        )

    if not np.isfinite(data).all():
        raise ValueError("Input dataset contains NaN or Inf values")

    warnings: list[dict[str, str]] = list(load_warnings)  # Start with load warnings
    if size_bytes > OVERSIZED_INPUT_THRESHOLD_BYTES:
        warnings.append(
            {
                "code": "OVERSIZED_INPUT",
                "message": "Input dataset exceeds 4GB; execution may be slow or memory-heavy",
            }
        )

    sample_phase, mapping_mode = _infer_sample_phase(metadata, data.shape[time_axis_idx])
    harmonic = int(params.get("harmonic", 1))

    g_map, s_map = _compute_phasor(data, time_axis_idx, harmonic, sample_phase)
    intensity = np.sum(data, axis=time_axis_idx, dtype="float32")

    output_axes = _remove_axis(axes, time_axis_idx)
    g_path = _write_ome_tiff(
        np.asarray(g_map, dtype="float32"), work_dir, "phasor_g.ome.tiff", output_axes
    )
    s_path = _write_ome_tiff(
        np.asarray(s_map, dtype="float32"), work_dir, "phasor_s.ome.tiff", output_axes
    )
    i_path = _write_ome_tiff(
        np.asarray(intensity, dtype="float32"), work_dir, "phasor_intensity.ome.tiff", output_axes
    )

    stack_output = bool(params.get("stack", False))
    stack_path = None
    stack_axes = None
    if stack_output:
        stack_axes = f"C{output_axes}" if "C" not in output_axes else f"P{output_axes}"
        stacked = np.stack(
            [np.asarray(g_map, dtype="float32"), np.asarray(s_map, dtype="float32")],
            axis=0,
        )
        stack_path = _write_ome_tiff(
            stacked,
            work_dir,
            "phasor_stack.ome.tiff",
            stack_axes,
        )

    provenance = {
        "resolved_params": {
            "time_axis": time_axis_name,
            "time_axis_index": time_axis_idx,
            "harmonic": harmonic,
        },
        "mapping_mode": mapping_mode,
        "load_method": metadata.get("_load_method", "unknown"),
    }

    # Record axes inference in provenance if heuristics were used
    if metadata.get("_axes_inferred"):
        provenance["axes_inferred"] = True
        provenance["inferred_axes"] = metadata.get("_inferred_axes", "")

    outputs = {
        "g_image": {"type": "BioImageRef", "format": "OME-TIFF", "path": str(g_path)},
        "s_image": {"type": "BioImageRef", "format": "OME-TIFF", "path": str(s_path)},
        "intensity_image": {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "path": str(i_path),
        },
    }
    if stack_path is not None and stack_axes is not None:
        outputs["phasor_stack"] = {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "path": str(stack_path),
            "metadata": {"axes": stack_axes},
        }

    return {
        "outputs": outputs,
        "warnings": warnings,
        "provenance": provenance,
        "log": f"phasor_from_flim completed (mapping_mode={mapping_mode})",
    }


def phasor_calibrate(*, inputs: dict, params: dict, work_dir: Path) -> dict[str, Any]:
    """Calibrate phasor coordinates using a reference standard.

    Uses phasorpy.lifetime.phasor_calibrate to apply phase rotation and
    modulation correction based on a reference sample with known lifetime.

    Args:
        inputs: Dict with 'sample_phasors' and 'reference_phasors' BioImageRefs
        params: Dict with 'lifetime', 'frequency', and optional 'harmonic'
        work_dir: Working directory for output files

    Returns:
        Dict with 'outputs', 'provenance', and optional 'warnings'
    """
    # Parameter validation
    lifetime = params.get("lifetime")
    frequency = params.get("frequency")
    harmonic = int(params.get("harmonic", 1))

    if lifetime is None or lifetime <= 0:
        raise ValueError(f"lifetime must be positive, got {lifetime}")
    if frequency is None or frequency <= 0:
        raise ValueError(f"frequency must be positive, got {frequency}")

    # Load sample phasors
    sample_ref = inputs.get("sample_phasors") or {}
    sample_uri = sample_ref.get("uri")
    if not sample_uri:
        raise ValueError("Input 'sample_phasors' must include uri")

    # Load reference phasors
    ref_ref = inputs.get("reference_phasors") or {}
    ref_uri = ref_ref.get("uri")
    if not ref_uri:
        raise ValueError("Input 'reference_phasors' must include uri")

    sample_path = uri_to_path(str(sample_uri))
    ref_path = uri_to_path(str(ref_uri))

    sample_data = np.squeeze(load_image(sample_path))
    ref_data = np.squeeze(load_image(ref_path))

    if sample_data.ndim != 3:
        raise ValueError(
            "Expected phasor image with shape (C, Y, X) after squeezing singleton axes"
        )
    if ref_data.ndim != 3:
        raise ValueError(
            "Expected reference phasor image with shape (C, Y, X) after squeezing singleton axes"
        )

    # Validate 2-channel structure
    if sample_data.shape[0] != 2:
        raise ValueError(f"Expected 2-channel phasor image, got {sample_data.shape[0]} channels")
    if ref_data.shape[0] != 2:
        raise ValueError(f"Expected 2-channel reference phasor, got {ref_data.shape[0]} channels")

    # Extract G and S channels
    sample_g = sample_data[0]
    sample_s = sample_data[1]
    ref_g = ref_data[0]
    ref_s = ref_data[1]

    # Calculate reference intensity (mean across all pixels)
    ref_mean = np.ones_like(ref_g)  # Uniform intensity

    # Use phasorpy for calibration
    try:
        from phasorpy.lifetime import phasor_calibrate as pp_calibrate
    except ImportError:
        raise RuntimeError("phasorpy is required for phasor calibration") from None

    # phasorpy.lifetime.phasor_calibrate(real, imag, ref_mean, ref_real, ref_imag,
    #                                     frequency, lifetime, harmonic=...)
    # frequency needs to be in MHz and lifetime in ns for default unit_conversion
    cal_g, cal_s = pp_calibrate(
        sample_g,
        sample_s,
        ref_mean,
        ref_g,
        ref_s,
        frequency=frequency / 1e6,  # Convert Hz to MHz
        lifetime=lifetime,
        harmonic=harmonic,
    )

    # Stack calibrated channels
    calibrated = np.stack([cal_g.astype(np.float32), cal_s.astype(np.float32)], axis=0)

    # Write output
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path = _write_ome_tiff(calibrated, work_dir, "calibrated_phasors.ome.tiff", "CYX")

    provenance = {
        "reference_lifetime": lifetime,
        "reference_frequency": frequency,
        "reference_harmonic": harmonic,
        "calibration_method": "phasorpy.lifetime.phasor_calibrate",
    }

    return {
        "outputs": {
            "calibrated_phasors": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
            },
        },
        "provenance": provenance,
        "log": (
            f"phasor_calibrate completed (lifetime={lifetime}ns, frequency={frequency / 1e6}MHz)"
        ),
    }
