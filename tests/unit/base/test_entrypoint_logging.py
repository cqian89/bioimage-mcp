import sys
from pathlib import Path

# Add tools/base to sys.path so we can import bioimage_mcp_base.entrypoint
TOOLS_BASE = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(TOOLS_BASE) not in sys.path:
    sys.path.insert(0, str(TOOLS_BASE))

from bioimage_mcp_base import entrypoint  # noqa: E402


def test_execute_request_traceback_on_error():
    """Test that a traceback is included in the log when a function fails."""
    request = {
        "fn_id": "base.io.bioimage.load",
        "params": {"path": "non-existent.tif"},
        "ordinal": 1,
    }

    # This will raise PathNotAllowedError which should be caught and logged with traceback
    response = entrypoint.process_execute_request(request)

    assert response["ok"] is False
    assert "not allowed for read" in response["error"]["message"]
    # This should fail before the fix (it will be "failed")
    assert response["log"] != "failed"
    assert "Traceback" in response["log"]


def test_meta_describe_unknown_function_log():
    """Test log content for meta.describe with unknown function."""
    request = {"fn_id": "meta.describe", "params": {"target_fn": "unknown.fn"}, "ordinal": 2}
    response = entrypoint.process_execute_request(request)
    assert response["ok"] is False
    assert response["error"]["message"] == "Unknown function: unknown.fn"
    # It should not be "failed", but since no exception occurred,
    # traceback.format_exc() will return 'NoneType: None\n' or similar
    assert response["log"] != "failed"
