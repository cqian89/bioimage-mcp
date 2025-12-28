from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import tifffile

BUILTIN_TOOLS_ROOT = Path(__file__).resolve().parents[2] / "tools" / "builtin"
if str(BUILTIN_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILTIN_TOOLS_ROOT))

from bioimage_mcp_builtin.ops.convert_to_ome_zarr import convert_to_ome_zarr


def _write_plain_tiff(path: Path) -> None:
    data = np.arange(12, dtype=np.uint16).reshape(3, 4)
    tifffile.imwrite(str(path), data)


def _mock_bioio_failure(monkeypatch) -> None:
    class _FailingBioImage:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("bioio plugin missing")

    fake_bioio = types.SimpleNamespace(BioImage=_FailingBioImage)
    monkeypatch.setitem(sys.modules, "bioio", fake_bioio)


def test_builtin_entrypoint_inserts_tool_paths() -> None:
    entrypoint_path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "builtin"
        / "bioimage_mcp_builtin"
        / "entrypoint.py"
    )
    tools_root = entrypoint_path.parent.parent
    repo_tools_root = tools_root.parent

    original_sys_path = list(sys.path)
    try:
        sys.path[:] = [
            p for p in sys.path if str(tools_root) not in p and str(repo_tools_root) not in p
        ]

        spec = importlib.util.spec_from_file_location("test_builtin_entrypoint", entrypoint_path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        assert str(tools_root) in sys.path
        assert str(repo_tools_root) in sys.path
    finally:
        sys.path[:] = original_sys_path


def test_builtin_convert_to_ome_zarr_handles_plain_tiff(tmp_path, monkeypatch) -> None:
    tiff_path = tmp_path / "plain.tif"
    _write_plain_tiff(tiff_path)
    _mock_bioio_failure(monkeypatch)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    out_dir = convert_to_ome_zarr(
        inputs={"image": {"uri": f"file://{tiff_path}"}},
        params={},
        work_dir=work_dir,
    )

    assert out_dir.exists()
    assert (out_dir / "0").exists()
