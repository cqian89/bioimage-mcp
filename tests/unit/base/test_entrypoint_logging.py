from unittest.mock import MagicMock, patch

from bioimage_mcp_base import entrypoint


def test_execute_request_traceback_on_error():
    """Test that a traceback is included in the log when a function fails."""
    # Refactor: Use a mock to force an exception in a controlled way.
    # This avoids relying on environment-specific filesystem allowlists.
    mock_func = MagicMock(side_effect=RuntimeError("Forced test error"))

    # FN_MAP is a dict mapping fn_id to (func, descriptions)
    with patch.dict(entrypoint.FN_MAP, {"test.fail": (mock_func, {})}, clear=False):
        request = {
            "id": "test.fail",
            "params": {},
            "ordinal": 1,
        }

        response = entrypoint.process_execute_request(request)

    assert response["ok"] is False
    assert response["error"]["message"] == "Forced test error"

    # Assert that the traceback contains meaningful information
    assert "Traceback" in response["log"]
    assert "RuntimeError: Forced test error" in response["log"]
    # We verify it went through the entrypoint's process_execute_request
    assert "process_execute_request" in response["log"]


def test_meta_describe_unknown_function_log():
    """Test log content for meta.describe with unknown function."""
    request = {"id": "meta.describe", "params": {"target_fn": "unknown.fn"}, "ordinal": 2}
    response = entrypoint.process_execute_request(request)

    assert response["ok"] is False
    assert response["error"]["message"] == "Unknown function: unknown.fn"

    # After the fix, this should be a descriptive message, not a misleading traceback
    assert response["log"] == "meta.describe failed: Unknown function: unknown.fn"


def test_handle_meta_describe_discovery_failure_logging(caplog):
    """Test that dynamic discovery failure in handle_meta_describe is logged at WARNING level."""
    import logging

    # Simpler approach: make manifest reading fail, which triggers the exception block
    with patch("pathlib.Path.read_bytes", side_effect=RuntimeError("Mocked file read failure")):
        with caplog.at_level(logging.WARNING):
            params = {"target_fn": "base.io.bioimage.load"}
            response = entrypoint.handle_meta_describe(params)

            # It should still succeed by falling back
            assert response["ok"] is True
            assert response["result"]["introspection_source"] == "python_api"

            # Verify the warning was logged
            assert (
                "Dynamic discovery for base.io.bioimage.load failed: Mocked file read failure"
                in caplog.text
            )
