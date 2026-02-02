from __future__ import annotations

from unittest.mock import patch

from bioimage_mcp_trackpy.entrypoint import handle_meta_describe, handle_meta_list

from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


def test_handle_meta_list_shape():
    """Verify meta.list returns the canonical result shape."""
    mock_functions = [
        FunctionMetadata(
            name="fn",
            module="trackpy",
            qualified_name="trackpy.fn",
            fn_id="trackpy.fn",
            source_adapter="trackpy",
            description="sum",
            io_pattern=IOPattern.GENERIC,
        )
    ]

    with (
        patch(
            "bioimage_mcp_trackpy.dynamic_discovery.TrackpyAdapter.discover",
            return_value=mock_functions,
        ),
        patch("bioimage_mcp_trackpy.entrypoint.get_trackpy_version", return_value="1.2.3"),
    ):
        res = handle_meta_list({})

        assert res["ok"] is True
        assert "result" in res
        result = res["result"]
        assert "functions" in result
        assert len(result["functions"]) > 0
        assert result["tool_version"] == "1.2.3"
        assert result["introspection_source"] == "dynamic_discovery"


def test_handle_meta_describe_missing_target():
    """Verify meta.describe handles missing target_fn with string error."""
    res = handle_meta_describe({})

    assert res["ok"] is False
    assert res["error"] == "target_fn required"
    assert isinstance(res["error"], str)


def test_handle_meta_describe_success_shape():
    """Verify meta.describe returns the canonical result shape."""
    mock_describe = {
        "params_schema": {"type": "object", "properties": {}},
        "tool_version": "1.2.3",
        "introspection_source": "numpydoc",
    }

    with patch("bioimage_mcp_trackpy.entrypoint.introspect_function", return_value=mock_describe):
        res = handle_meta_describe({"target_fn": "trackpy.locate"})

        assert res["ok"] is True
        assert "result" in res
        result = res["result"]
        assert result["params_schema"]["type"] == "object"
        assert result["tool_version"] == "1.2.3"
        assert result["introspection_source"] == "numpydoc"


def test_handle_meta_describe_failure():
    """Verify meta.describe handles introspection failure with string error."""
    with patch(
        "bioimage_mcp_trackpy.entrypoint.introspect_function",
        side_effect=RuntimeError("Introspection failed"),
    ):
        res = handle_meta_describe({"target_fn": "trackpy.locate"})

        assert res["ok"] is False
        assert "Introspection failed" in res["error"]
        assert isinstance(res["error"], str)
