from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pytest
import tifffile

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import io


def _write_plain_tiff(path: Path) -> None:
    data = np.arange(12, dtype=np.uint16).reshape(3, 4)
    tifffile.imwrite(str(path), data)


def _mock_bioio_failure(monkeypatch) -> None:
    class _FailingBioImage:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("bioio plugin missing")

    fake_bioio = types.SimpleNamespace(BioImage=_FailingBioImage)
    monkeypatch.setitem(sys.modules, "bioio", fake_bioio)


def test_convert_to_ome_zarr_requires_uri() -> None:
    with pytest.raises(ValueError, match="uri"):
        io.convert_to_ome_zarr(inputs={"image": {}}, params={}, work_dir=Path("."))


def test_export_ome_tiff_requires_uri() -> None:
    with pytest.raises(ValueError, match="uri"):
        io.export_ome_tiff(inputs={"image": {}}, params={}, work_dir=Path("."))


def test_convert_to_ome_zarr_accepts_string_uri(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _Sentinel(Exception):
        pass

    def _fake_uri_to_path(uri: str) -> Path:
        captured["uri"] = uri
        raise _Sentinel

    monkeypatch.setattr(io, "uri_to_path", _fake_uri_to_path)

    with pytest.raises(_Sentinel):
        io.convert_to_ome_zarr(
            inputs={"image": "file:///tmp/sample.tif"},
            params={},
            work_dir=Path("."),
        )

    assert captured["uri"] == "file:///tmp/sample.tif"


def test_oversized_input_threshold_bytes_env_override(monkeypatch) -> None:
    monkeypatch.delenv("BIOIMAGE_MCP_OVERSIZED_INPUT_THRESHOLD_BYTES", raising=False)
    assert io._get_oversized_input_threshold_bytes() == 4 * 1024**3

    monkeypatch.setenv("BIOIMAGE_MCP_OVERSIZED_INPUT_THRESHOLD_BYTES", "123")
    assert io._get_oversized_input_threshold_bytes() == 123


def test_convert_to_ome_zarr_handles_plain_tiff(tmp_path, monkeypatch) -> None:
    tiff_path = tmp_path / "plain.tif"
    _write_plain_tiff(tiff_path)
    _mock_bioio_failure(monkeypatch)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    out_dir = io.convert_to_ome_zarr(
        inputs={"image": {"uri": f"file://{tiff_path}"}},
        params={},
        work_dir=work_dir,
    )

    assert out_dir.exists()
    assert (out_dir / "0").exists()
