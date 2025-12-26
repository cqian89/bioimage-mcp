from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import transforms


def test_phasor_outputs_artifact_refs_and_intensity_sum(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="float32").reshape(2, 3, 4)
    axes = "TYX"
    metadata: dict = {}
    captured: dict[str, list[tuple[str, np.ndarray, str]]] = {"writes": []}

    def _load_flim_data(_image_ref: dict) -> tuple[np.ndarray, str, dict, int, list]:
        return data, axes, metadata, data.nbytes, []

    def _compute_phasor(
        signal: np.ndarray,
        time_axis: int,
        harmonic: int,
        sample_phase: np.ndarray | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        assert time_axis == 0
        assert harmonic == 1
        assert sample_phase is None
        return np.ones((3, 4), dtype="float32"), np.zeros((3, 4), dtype="float32")

    def _write_ome_tiff(
        array: np.ndarray,
        work_dir: Path,
        name: str,
        axes: str,
        **_kwargs: dict,
    ) -> Path:
        captured["writes"].append((name, array.copy(), axes))
        return work_dir / name

    monkeypatch.setattr(transforms, "_load_flim_data", _load_flim_data)
    monkeypatch.setattr(transforms, "_compute_phasor", _compute_phasor)
    monkeypatch.setattr(transforms, "_write_ome_tiff", _write_ome_tiff)

    result = transforms.phasor_from_flim(
        inputs={"dataset": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
        params={},
        work_dir=tmp_path,
    )

    outputs = result["outputs"]
    assert set(outputs.keys()) == {"g_image", "s_image", "intensity_image"}
    for output in outputs.values():
        assert output["type"] == "BioImageRef"
        assert output["format"] == "OME-TIFF"
        assert output["path"]

    assert result["warnings"] == []
    assert result["provenance"]["mapping_mode"] == "uniform"

    intensity_write = next(
        item for item in captured["writes"] if item[0] == "phasor_intensity.ome.tiff"
    )
    np.testing.assert_array_equal(intensity_write[1], data.sum(axis=0))
    assert intensity_write[2] == "YX"


def test_phasor_requires_time_axis(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((2, 3, 4), dtype="float32")
    axes = "CYX"
    metadata: dict = {}

    def _load_flim_data(_image_ref: dict) -> tuple[np.ndarray, str, dict, int, list]:
        return data, axes, metadata, data.nbytes, []

    monkeypatch.setattr(transforms, "_load_flim_data", _load_flim_data)

    with pytest.raises(ValueError, match="Time axis"):
        transforms.phasor_from_flim(
            inputs={"dataset": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
            params={},
            work_dir=tmp_path,
        )


def test_phasor_preserves_channel_dimension(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((2, 3, 4, 5), dtype="float32")
    axes = "CTYX"
    metadata: dict = {}
    captured: dict[str, list[tuple[str, np.ndarray, str]]] = {"writes": []}
    seen: dict[str, int] = {}

    def _load_flim_data(_image_ref: dict) -> tuple[np.ndarray, str, dict, int, list]:
        return data, axes, metadata, data.nbytes, []

    def _compute_phasor(
        signal: np.ndarray,
        time_axis: int,
        harmonic: int,
        sample_phase: np.ndarray | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        seen["time_axis"] = time_axis
        return np.ones((2, 4, 5), dtype="float32"), np.zeros((2, 4, 5), dtype="float32")

    def _write_ome_tiff(
        array: np.ndarray,
        work_dir: Path,
        name: str,
        axes: str,
        **_kwargs: dict,
    ) -> Path:
        captured["writes"].append((name, array.copy(), axes))
        return work_dir / name

    monkeypatch.setattr(transforms, "_load_flim_data", _load_flim_data)
    monkeypatch.setattr(transforms, "_compute_phasor", _compute_phasor)
    monkeypatch.setattr(transforms, "_write_ome_tiff", _write_ome_tiff)

    result = transforms.phasor_from_flim(
        inputs={"dataset": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
        params={"time_axis": "T"},
        work_dir=tmp_path,
    )

    assert seen["time_axis"] == 1
    assert result["provenance"]["resolved_params"]["time_axis"] == "T"

    g_write = next(item for item in captured["writes"] if item[0] == "phasor_g.ome.tiff")
    assert g_write[1].shape == (2, 4, 5)
    assert g_write[2] == "CYX"


def test_phasor_warns_on_large_input(monkeypatch, tmp_path: Path) -> None:
    data = np.zeros((1, 2, 2), dtype="float32")
    axes = "TYX"
    metadata: dict = {}

    def _load_flim_data(_image_ref: dict) -> tuple[np.ndarray, str, dict, int, list]:
        return data, axes, metadata, 5 * 1024**3, []

    def _compute_phasor(
        signal: np.ndarray,
        time_axis: int,
        harmonic: int,
        sample_phase: np.ndarray | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        return np.zeros((2, 2), dtype="float32"), np.zeros((2, 2), dtype="float32")

    def _write_ome_tiff(
        array: np.ndarray,
        work_dir: Path,
        name: str,
        axes: str,
        **_kwargs: dict,
    ) -> Path:
        return work_dir / name

    monkeypatch.setattr(transforms, "_load_flim_data", _load_flim_data)
    monkeypatch.setattr(transforms, "_compute_phasor", _compute_phasor)
    monkeypatch.setattr(transforms, "_write_ome_tiff", _write_ome_tiff)

    result = transforms.phasor_from_flim(
        inputs={"dataset": {"uri": "file:///tmp/sample.tif", "format": "OME-TIFF"}},
        params={},
        work_dir=tmp_path,
    )

    warnings = result["warnings"]
    assert any(warning.get("code") == "OVERSIZED_INPUT" for warning in warnings)
