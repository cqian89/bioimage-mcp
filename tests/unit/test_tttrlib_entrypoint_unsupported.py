from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
TOOLS_TTTRLIB = REPO_ROOT / "tools" / "tttrlib"
if str(TOOLS_TTTRLIB) not in sys.path:
    sys.path.insert(0, str(TOOLS_TTTRLIB))

import bioimage_mcp_tttrlib.entrypoint as entrypoint


def test_deferred_or_denied_id_returns_stable_unsupported_error(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        entrypoint,
        "_get_coverage_entry",
        lambda _fn_id: {
            "status": "deferred",
            "revisit_trigger": "Use tttrlib.TTTR.get_time_window_ranges until coverage is added.",
        },
    )

    response = entrypoint.process_execute_request(
        {
            "id": "tttrlib.TTTR.get_intensity_trace",
            "inputs": {},
            "params": {},
            "work_dir": str(tmp_path),
        }
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "TTTRLIB_UNSUPPORTED_METHOD"
    assert "tttrlib.TTTR.get_intensity_trace" in response["error"]["message"]
    assert response["error"]["remediation"].strip()


def test_unknown_function_path_is_preserved(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(entrypoint, "_get_coverage_entry", lambda _fn_id: None)

    response = entrypoint.process_execute_request(
        {
            "id": "tttrlib.Unknown.missing",
            "inputs": {},
            "params": {},
            "work_dir": str(tmp_path),
        }
    )

    assert response["ok"] is False
    assert response["error"] == {"message": "Unknown function: tttrlib.Unknown.missing"}
