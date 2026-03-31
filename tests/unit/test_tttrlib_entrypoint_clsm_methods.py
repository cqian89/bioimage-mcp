from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).parent.parent.parent
TOOLS_TTTRLIB = REPO_ROOT / "tools" / "tttrlib"
if str(TOOLS_TTTRLIB) not in sys.path:
    sys.path.insert(0, str(TOOLS_TTTRLIB))

import bioimage_mcp_tttrlib.entrypoint as entrypoint  # noqa: E402


class _FakeCLSMImage:
    def get_image_info(self) -> dict[str, int]:
        return {"n_frames": 2, "n_lines": 4, "n_pixel_per_line": 8}

    def get_settings(self):
        return _FakeCLSMSettings()


class _FakeVector:
    def __init__(self, values: list[int]) -> None:
        self._values = values

    def __iter__(self):
        return iter(self._values)


class _FakeScalarWrapper:
    def __init__(self, value: int) -> None:
        self._value = value

    def item(self) -> int:
        return self._value


class _FakeNestedSettings:
    def __init__(self) -> None:
        self.channel = _FakeScalarWrapper(3)
        self.marker_line_stop = _FakeScalarWrapper(9)
        self.this = "nested-swig-handle"
        self.thisown = False


class _FakeCLSMSettings:
    def __init__(self) -> None:
        self.n_lines = 4
        self.n_pixel_per_line = 8
        self.marker_line_start = 2
        self.marker_frame_start = _FakeVector([4, 6])
        self.channel_settings = _FakeNestedSettings()
        self.this = "swig-handle"
        self.thisown = True


class _FakeImageInfo:
    def __init__(self) -> None:
        self.n_frames = 2
        self.n_lines = 4
        self.n_pixel_per_line = 8
        self.this = "swig-handle"
        self.thisown = True


class _FakeCorrelator:
    x = [1.0, 2.0, 4.0]
    y = [0.5, 0.25, 0.125]

    def get_curve(self):
        return _FakeCorrelatorCurve(self.x, self.y)

    def get_x_axis(self):
        return self.x

    def get_corr(self):
        return self.y


class _FakeCorrelatorCurve:
    def __init__(self, x: list[float], y: list[float]) -> None:
        self.x = x
        self.y = y


def test_handle_clsm_get_image_info_returns_native_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_object", lambda _key: _FakeCLSMImage())

    result = entrypoint.handle_clsm_get_image_info(
        inputs={"clsm": {"ref_id": "clsm-1"}},
        params={},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    output = result["outputs"]["image_info"]
    assert output["type"] == "NativeOutputRef"
    with open(output["path"], encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["n_frames"] == 2


def test_handle_clsm_get_image_info_serializes_swig_like_payload(
    monkeypatch, tmp_path: Path
) -> None:
    class _FakeCLSMImageInfoObject:
        def get_image_info(self):
            return _FakeImageInfo()

    monkeypatch.setattr(entrypoint, "_load_object", lambda _key: _FakeCLSMImageInfoObject())

    result = entrypoint.handle_clsm_get_image_info(
        inputs={"clsm": {"ref_id": "clsm-1"}},
        params={},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    output = result["outputs"]["image_info"]
    with open(output["path"], encoding="utf-8") as f:
        payload = json.load(f)

    assert payload == {
        "n_frames": 2,
        "n_lines": 4,
        "n_pixel_per_line": 8,
    }


def test_handle_clsm_get_settings_serializes_json_object(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_object", lambda _key: _FakeCLSMImage())

    result = entrypoint.handle_clsm_get_settings(
        inputs={"clsm": {"ref_id": "clsm-1"}},
        params={},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    output = result["outputs"]["settings"]
    assert output["type"] == "NativeOutputRef"
    with open(output["path"], encoding="utf-8") as f:
        payload = json.load(f)

    assert payload == {
        "channel_settings": {
            "channel": 3,
            "marker_line_stop": 9,
        },
        "marker_frame_start": [4, 6],
        "marker_line_start": 2,
        "n_lines": 4,
        "n_pixel_per_line": 8,
    }
    assert "this" not in payload
    assert "thisown" not in payload
    assert "this" not in payload["channel_settings"]
    assert "thisown" not in payload["channel_settings"]


def test_handle_correlator_get_curve_returns_table_ref(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: object())
    monkeypatch.setitem(
        sys.modules, "tttrlib", SimpleNamespace(Correlator=lambda **_kwargs: _FakeCorrelator())
    )

    result = entrypoint.handle_correlator_get_curve(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"channels": [[0], [8]], "n_bins": 7, "n_casc": 12},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    output = result["outputs"]["curve"]
    assert output["type"] == "TableRef"
    with open(output["path"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert set(rows[0].keys()) == {"tau", "correlation"}
    assert output["metadata"]["columns"] == [
        {"name": "tau", "dtype": "float64"},
        {"name": "correlation", "dtype": "float64"},
    ]


def test_handle_correlator_get_x_axis_returns_consistent_table_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: object())
    monkeypatch.setitem(
        sys.modules, "tttrlib", SimpleNamespace(Correlator=lambda **_kwargs: _FakeCorrelator())
    )

    result = entrypoint.handle_correlator_get_x_axis(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"channels": [[0], [8]], "n_bins": 7, "n_casc": 12},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    output = result["outputs"]["tau"]
    with open(output["path"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [row["tau"] for row in rows] == [
        "1.000000000000000000e+00",
        "2.000000000000000000e+00",
        "4.000000000000000000e+00",
    ]
    assert output["metadata"]["columns"] == [{"name": "tau", "dtype": "float64"}]


def test_handle_correlator_get_corr_returns_consistent_table_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: object())
    monkeypatch.setitem(
        sys.modules, "tttrlib", SimpleNamespace(Correlator=lambda **_kwargs: _FakeCorrelator())
    )

    result = entrypoint.handle_correlator_get_corr(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"channels": [[0], [8]], "n_bins": 7, "n_casc": 12},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    output = result["outputs"]["correlation"]
    with open(output["path"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [row["correlation"] for row in rows] == [
        "5.000000000000000000e-01",
        "2.500000000000000000e-01",
        "1.250000000000000000e-01",
    ]
    assert output["metadata"]["columns"] == [{"name": "correlation", "dtype": "float64"}]


def test_correlator_get_curve_rejects_unsupported_params(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: object())

    result = entrypoint.handle_correlator_get_curve(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"channels": [[0], [8]], "normalize": True},
        work_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN"
