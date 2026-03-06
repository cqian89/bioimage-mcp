from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
TOOLS_TTTRLIB = REPO_ROOT / "tools" / "tttrlib"
if str(TOOLS_TTTRLIB) not in sys.path:
    sys.path.insert(0, str(TOOLS_TTTRLIB))

import bioimage_mcp_tttrlib.entrypoint as entrypoint


class _FakeTTTR:
    def get_intensity_trace(self, time_window_length: float = 0.001):
        return [[0.0, 10.0], [time_window_length, 12.5]]

    def get_count_rate(self) -> float:
        return 42.5

    def get_selection_by_channel(self, input: list[int]):
        return [True, False, True] if input else []

    def get_selection_by_count_rate(
        self,
        time_window: float,
        n_ph_max: int,
        invert: bool = False,
        make_mask: bool = False,
    ):
        if make_mask:
            return [True, False, False, True]
        return [1, 3] if not invert else [0, 2]

    def get_tttr_by_selection(self, selection: list[int]):
        subset = _FakeTTTRWriter()
        subset.selection = selection
        return subset


def test_handle_get_intensity_trace_returns_table_ref(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_intensity_trace(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"time_window_length": 0.25},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    table = result["outputs"]["trace"]
    assert table["type"] == "TableRef"
    assert table["columns"] == ["time", "count_rate"]

    csv_path = Path(table["path"])
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert float(rows[0]["time"]) == 0.0
    assert float(rows[0]["count_rate"]) == 10.0


def test_handle_get_count_rate_returns_native_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_count_rate(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    payload = result["outputs"]["count_rate"]
    assert payload["type"] == "NativeOutputRef"
    with open(payload["path"]) as f:
        decoded = json.load(f)
    assert decoded == {"count_rate": 42.5}


def test_supported_subset_rejects_selection_argument_patterns(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_selection_by_channel(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"input": [0], "invert": True},
        work_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN"


class _FakeTTTRWriter:
    def __init__(self) -> None:
        self.paths: list[str] = []
        self.writer_calls: list[tuple[str, str]] = []

    def write(self, path: str) -> None:
        self.paths.append(path)
        Path(path).write_text("tttr")

    def write_header(self, path: str) -> None:
        self.paths.append(path)
        Path(path).write_text("header")

    def write_hht3v2_events(self, path: str, tttr: object) -> None:
        self.paths.append(path)
        self.writer_calls.append((path, getattr(tttr, "__class__", type(tttr)).__name__))
        Path(path).write_text("hht3")

    def write_spc132_events(self, path: str, tttr: object) -> None:
        self.paths.append(path)
        self.writer_calls.append((path, getattr(tttr, "__class__", type(tttr)).__name__))
        Path(path).write_text("spc")


def test_handle_get_selection_by_channel_accepts_live_input_shape(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_selection_by_channel(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"input": [0, 8]},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    table = result["outputs"]["selection"]
    assert table["type"] == "TableRef"
    assert table["columns"] == ["index"]


def test_handle_get_selection_by_count_rate_accepts_live_subset_and_returns_table(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_selection_by_count_rate(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"time_window": 0.5, "n_ph_max": 3, "invert": True},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    table = result["outputs"]["selection"]
    assert table["type"] == "TableRef"
    assert table["columns"] == ["index"]


def test_handle_get_tttr_by_selection_returns_file_backed_tttr_ref(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_tttr_by_selection(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"selection": [1, 3]},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    tttr_ref = result["outputs"]["tttr"]
    assert tttr_ref["type"] == "TTTRRef"
    assert tttr_ref["storage_type"] == "file"
    assert Path(tttr_ref["path"]).exists()


def test_handle_get_tttr_by_selection_preserves_source_format(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_tttr_by_selection(
        inputs={"tttr": {"ref_id": "tttr-1", "format": "SPC-130"}},
        params={"selection": [1, 3]},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    tttr_ref = result["outputs"]["tttr"]
    assert tttr_ref["format"] == "SPC-130"
    assert tttr_ref["path"].endswith(".spc")


def test_handle_get_selection_by_count_rate_rejects_unsupported_flags(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_selection_by_count_rate(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"time_window": 0.5, "n_ph_max": 3, "unexpected": True},
        work_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN"


def test_write_spc132_events_passes_tttr_explicitly(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeTTTRWriter()
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: fake)

    result = entrypoint.handle_tttr_write_spc132_events(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"filename": "exports/result.spc"},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    assert fake.writer_calls == [
        (str((tmp_path / "exports" / "result.spc").resolve()), "_FakeTTTRWriter")
    ]


def test_write_variants_resolve_relative_paths_under_work_dir(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeTTTRWriter()
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: fake)

    result = entrypoint.handle_tttr_write_hht3v2_events(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"filename": "exports/result.ht3"},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    assert fake.paths
    assert Path(fake.paths[0]).is_absolute()
    assert str(tmp_path.resolve()) in fake.paths[0]


def test_write_rejects_unsafe_output_path(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeTTTRWriter()
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: fake)

    result = entrypoint.handle_tttr_write(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"filename": "../escape.ptu"},
        work_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TTTRLIB_UNSAFE_OUTPUT_PATH"


def test_write_variants_reject_unsupported_format_combinations(monkeypatch, tmp_path: Path) -> None:
    fake = _FakeTTTRWriter()
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: fake)

    result = entrypoint.handle_tttr_write_hht3v2_events(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"filename": "exports/result.spc"},
        work_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN"
