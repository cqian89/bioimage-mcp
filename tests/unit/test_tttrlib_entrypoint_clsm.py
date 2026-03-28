from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
TOOLS_TTTRLIB = REPO_ROOT / "tools" / "tttrlib"
if str(TOOLS_TTTRLIB) not in sys.path:
    sys.path.insert(0, str(TOOLS_TTTRLIB))

import bioimage_mcp_tttrlib.entrypoint as entrypoint


def _prepare_mocks(monkeypatch, captured: dict[str, object], n_frames: int = 2) -> None:
    fake_tttr = object()

    def fake_clsm_ctor(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(n_frames=n_frames)

    monkeypatch.setitem(sys.modules, "tttrlib", SimpleNamespace(CLSMImage=fake_clsm_ctor))
    monkeypatch.setattr(entrypoint, "_load_tttr_from_input", lambda _tttr_ref: fake_tttr)
    monkeypatch.setattr(
        entrypoint,
        "_store_object",
        lambda _obj, class_name: {
            "ref_id": "obj-1",
            "type": "ObjectRef",
            "uri": "obj://session/env/obj-1",
            "python_class": class_name,
        },
    )


def test_handle_clsm_image_does_not_inject_defaults(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    _prepare_mocks(monkeypatch, captured)

    result = entrypoint.handle_clsm_image(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    assert len(captured["args"]) == 1
    assert captured["kwargs"] == {}


def test_handle_clsm_image_forwards_explicit_params(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    _prepare_mocks(monkeypatch, captured, n_frames=20)

    params = {
        "reading_routine": "BH_SPC130",
        "marker_frame_start": [4],
        "marker_line_start": 2,
        "marker_line_stop": 3,
        "channels": [0],
        "fill": True,
    }
    result = entrypoint.handle_clsm_image(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params=params,
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    assert len(captured["args"]) == 1
    assert captured["kwargs"] == params


def test_handle_clsm_image_prefers_ref_id_over_uri(monkeypatch, tmp_path: Path) -> None:
    fake_tttr = object()
    calls: list[tuple[str, str]] = []

    def fake_load_tttr_cached(key: str):
        calls.append(("cached", key))
        if key == "tttr-1":
            return fake_tttr
        raise KeyError(f"TTTR object not found: {key}")

    def fake_load_tttr(_key: str):
        calls.append(("load", _key))
        raise AssertionError("URI fallback should not run when ref_id cache hit exists")

    monkeypatch.setattr(entrypoint, "_load_tttr_cached", fake_load_tttr_cached)
    monkeypatch.setattr(entrypoint, "_load_tttr", fake_load_tttr)

    loaded = entrypoint._load_tttr_from_input(
        {"ref_id": "tttr-1", "uri": "file:///tmp/uri-fallback.spc"}
    )

    assert loaded is fake_tttr
    assert calls == [("cached", "tttr-1")]


def test_load_tttr_from_input_does_not_open_ref_id_file_uri(monkeypatch) -> None:
    fake_tttr = object()
    calls: list[tuple[str, str]] = []

    def fake_load_tttr_cached(key: str):
        calls.append(("cached", key))
        raise KeyError(f"TTTR object not found: {key}")

    def fake_load_tttr(key: str):
        calls.append(("load", key))
        if key == "file:///tmp/good.spc":
            return fake_tttr
        raise AssertionError(f"Unexpected uri load key: {key}")

    monkeypatch.setattr(entrypoint, "_load_tttr_cached", fake_load_tttr_cached)
    monkeypatch.setattr(entrypoint, "_load_tttr", fake_load_tttr)

    loaded = entrypoint._load_tttr_from_input(
        {"ref_id": "file:///tmp/bad.spc", "uri": "file:///tmp/good.spc"}
    )

    assert loaded is fake_tttr
    assert calls == [
        ("cached", "file:///tmp/bad.spc"),
        ("load", "file:///tmp/good.spc"),
    ]


def test_load_tttr_missing_file_uri_raises_key_error(tmp_path: Path) -> None:
    missing_uri = f"file://{tmp_path / 'missing.spc'}"

    with pytest.raises(KeyError, match="TTTR file not found"):
        entrypoint._load_tttr(missing_uri)
