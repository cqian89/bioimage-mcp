from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import io


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
