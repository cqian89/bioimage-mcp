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
    def get_intensity_trace(self, time_window: float):
        return [[0.0, 10.0], [time_window, 12.5]]

    def get_count_rate(self) -> float:
        return 42.5

    def get_selection_by_channel(self, channels: list[int]):
        return [True, False, True] if channels else []


def test_handle_get_intensity_trace_returns_table_ref(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(entrypoint, "_load_tttr", lambda _key: _FakeTTTR())

    result = entrypoint.handle_get_intensity_trace(
        inputs={"tttr": {"ref_id": "tttr-1"}},
        params={"time_window": 0.25},
        work_dir=tmp_path,
    )

    assert result["ok"] is True
    table = result["outputs"]["trace"]
    assert table["type"] == "TableRef"
    assert table["columns"] == ["time", "count_rate"]

    csv_path = Path(table["path"])
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["time"] == "0.0"
    assert rows[0]["count_rate"] == "10.0"


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
        params={"channels": [0], "invert": True},
        work_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN"
