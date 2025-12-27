from __future__ import annotations

from pathlib import Path

import numpy as np
from bioimage_mcp_base.utils import uri_to_path
from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class AxisToolParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AxisMapping(RootModel[dict[str, str]]):
    @field_validator("root")
    @classmethod
    def _validate_axis_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        for mapped in value.values():
            _validate_axis_name(mapped)
        return value


class RelabelAxesParams(AxisToolParams):
    axis_mapping: dict[str, str] = Field(..., description="Mapping from old axes to new axes")

    @field_validator("axis_mapping")
    @classmethod
    def _validate_axis_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        AxisMapping.model_validate(value)
        return value


class SqueezeParams(AxisToolParams):
    axis: int | str | None = None

    @field_validator("axis")
    @classmethod
    def _validate_axis(cls, value: int | str | None) -> int | str | None:
        if isinstance(value, str):
            return _validate_axis_name(value)
        return value


class ExpandDimsParams(AxisToolParams):
    axis: int
    new_axis_name: str

    @field_validator("new_axis_name")
    @classmethod
    def _validate_new_axis_name(cls, value: str) -> str:
        return _validate_axis_name(value)


class MoveAxisParams(AxisToolParams):
    source: int | str
    destination: int

    @field_validator("source")
    @classmethod
    def _validate_source(cls, value: int | str) -> int | str:
        if isinstance(value, str):
            return _validate_axis_name(value)
        return value


class SwapAxesParams(AxisToolParams):
    axis1: int | str
    axis2: int | str

    @field_validator("axis1", "axis2")
    @classmethod
    def _validate_axis(cls, value: int | str) -> int | str:
        if isinstance(value, str):
            return _validate_axis_name(value)
        return value


def load_image(path: Path) -> np.ndarray:
    try:
        from bioio import BioImage  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for axis operations") from exc

    img = BioImage(str(path))
    return img.get_image_data()  # type: ignore[attr-defined]


def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
    try:
        from bioio.writers import OmeTiffWriter  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for OME-TIFF writing") from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    out_path = work_dir / name
    if out_path.exists():
        raise FileExistsError(out_path)

    OmeTiffWriter.save(array, str(out_path), dim_order=axes)
    return out_path


def relabel_axes(inputs: dict, params: dict, work_dir: Path) -> dict:
    validated = RelabelAxesParams.model_validate(params)
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    data = load_image(uri_to_path(str(uri)))
    axes = str((image_ref.get("metadata") or {}).get("axes") or "")

    new_axes = "".join(validated.axis_mapping.get(axis, axis) for axis in axes)
    out_path = _write_ome_tiff(data, work_dir, "relabeled.ome.tiff", new_axes)

    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
                "metadata": {"axes": new_axes},
            }
        }
    }


def squeeze(inputs: dict, params: dict, work_dir: Path) -> dict:
    validated = SqueezeParams.model_validate(params)
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    data = load_image(uri_to_path(str(uri)))
    axes = str((image_ref.get("metadata") or {}).get("axes") or "")

    axis = validated.axis
    if axis is None:
        singleton_axes = [idx for idx, size in enumerate(data.shape) if size == 1]
        if not singleton_axes:
            raise ValueError("No singleton axes to squeeze")
        squeezed = np.squeeze(data)
        new_axes = _remove_axes_by_index(axes, singleton_axes)
    else:
        axis_idx = _resolve_axis_index(axis, axes, data.ndim)
        squeezed = np.squeeze(data, axis=axis_idx)
        new_axes = _remove_axes_by_index(axes, [axis_idx])

    out_path = _write_ome_tiff(squeezed, work_dir, "squeezed.ome.tiff", new_axes)
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
                "metadata": {"axes": new_axes},
            }
        }
    }


def expand_dims(inputs: dict, params: dict, work_dir: Path) -> dict:
    validated = ExpandDimsParams.model_validate(params)
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    data = load_image(uri_to_path(str(uri)))
    axes = str((image_ref.get("metadata") or {}).get("axes") or "")

    axis_idx = _normalize_insert_axis(validated.axis, data.ndim)
    expanded = np.expand_dims(data, axis=axis_idx)
    new_axes = _insert_axis_name(axes, axis_idx, validated.new_axis_name)

    out_path = _write_ome_tiff(expanded, work_dir, "expanded.ome.tiff", new_axes)
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
                "metadata": {"axes": new_axes},
            }
        }
    }


def moveaxis(inputs: dict, params: dict, work_dir: Path) -> dict:
    validated = MoveAxisParams.model_validate(params)
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    data = load_image(uri_to_path(str(uri)))
    axes = str((image_ref.get("metadata") or {}).get("axes") or "")

    source_idx = _resolve_axis_index(validated.source, axes, data.ndim)
    dest_idx = _normalize_move_destination(validated.destination, data.ndim)

    moved = np.moveaxis(data, source_idx, dest_idx)
    new_axes = _move_axis_name(axes, source_idx, dest_idx)

    out_path = _write_ome_tiff(moved, work_dir, "moved.ome.tiff", new_axes)
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
                "metadata": {"axes": new_axes},
            }
        }
    }


def swap_axes(inputs: dict, params: dict, work_dir: Path) -> dict:
    validated = SwapAxesParams.model_validate(params)
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    data = load_image(uri_to_path(str(uri)))
    axes = str((image_ref.get("metadata") or {}).get("axes") or "")

    axis1_idx = _resolve_axis_index(validated.axis1, axes, data.ndim)
    axis2_idx = _resolve_axis_index(validated.axis2, axes, data.ndim)

    swapped = np.swapaxes(data, axis1_idx, axis2_idx)
    new_axes = _swap_axis_names(axes, axis1_idx, axis2_idx)

    out_path = _write_ome_tiff(swapped, work_dir, "swapped.ome.tiff", new_axes)
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
                "metadata": {"axes": new_axes},
            }
        }
    }


def _validate_axis_name(name: str) -> str:
    if len(name) != 1 or not name.isalpha() or not name.isupper():
        raise ValueError("Axis names must be single uppercase letters")
    return name


def _resolve_axis_index(axis: int | str, axes: str, ndim: int) -> int:
    if isinstance(axis, str):
        axis_name = axis.upper()
        if axis_name not in axes:
            raise ValueError(f"Axis {axis_name} not found in axes '{axes}'")
        return axes.index(axis_name)

    idx = int(axis)
    if idx < 0:
        idx += ndim
    if idx < 0 or idx >= ndim:
        raise ValueError(f"Axis index {axis} out of bounds for ndim={ndim}")
    return idx


def _normalize_insert_axis(axis: int, ndim: int) -> int:
    idx = int(axis)
    if idx < 0:
        idx += ndim + 1
    if idx < 0 or idx > ndim:
        raise ValueError(f"Axis position {axis} out of bounds for ndim={ndim}")
    return idx


def _normalize_move_destination(axis: int, ndim: int) -> int:
    idx = int(axis)
    if idx < 0:
        idx += ndim
    if idx < 0 or idx >= ndim:
        raise ValueError(f"Axis position {axis} out of bounds for ndim={ndim}")
    return idx


def _remove_axes_by_index(axes: str, remove_indices: list[int]) -> str:
    if not axes:
        return axes
    remove_set = set(remove_indices)
    return "".join(axis for idx, axis in enumerate(axes) if idx not in remove_set)


def _insert_axis_name(axes: str, axis_index: int, axis_name: str) -> str:
    if not axes:
        return axis_name
    return axes[:axis_index] + axis_name + axes[axis_index:]


def _move_axis_name(axes: str, source_idx: int, dest_idx: int) -> str:
    if not axes:
        return axes
    axis_names = list(axes)
    name = axis_names.pop(source_idx)
    axis_names.insert(dest_idx, name)
    return "".join(axis_names)


def _swap_axis_names(axes: str, axis1_idx: int, axis2_idx: int) -> str:
    if not axes:
        return axes
    axis_names = list(axes)
    axis_names[axis1_idx], axis_names[axis2_idx] = axis_names[axis2_idx], axis_names[axis1_idx]
    return "".join(axis_names)
