from __future__ import annotations

from bioimage_mcp.runtimes.meta_protocol import (
    extract_result_payload,
    parse_meta_describe_result,
    parse_meta_list_result,
)


def test_extract_result_payload_direct():
    response = {"ok": True, "result": {"foo": "bar"}}
    assert extract_result_payload(response) == {"foo": "bar"}


def test_extract_result_payload_worker():
    response = {
        "ok": True,
        "outputs": {"result": {"foo": "bar"}},
    }
    assert extract_result_payload(response) == {"foo": "bar"}


def test_extract_result_payload_error():
    response = {"ok": False, "error": "something went wrong"}
    assert extract_result_payload(response) is None


def test_parse_meta_list_result_valid():
    response = {
        "ok": True,
        "result": {
            "functions": [
                {
                    "fn_id": "test.fn",
                    "name": "Test Function",
                    "summary": "A test function",
                    "module": "test_module",
                    "io_pattern": "image_to_image",
                }
            ]
        },
    }
    result = parse_meta_list_result(response)
    assert len(result) == 1
    assert result[0]["fn_id"] == "test.fn"
    assert result[0]["io_pattern"] == "image_to_image"


def test_parse_meta_list_result_missing_optional():
    response = {
        "ok": True,
        "result": {
            "functions": [
                {
                    "fn_id": "test.fn",
                    "name": "Test Function",
                    "summary": "A test function",
                }
            ]
        },
    }
    result = parse_meta_list_result(response)
    assert len(result) == 1
    assert result[0]["fn_id"] == "test.fn"
    assert result[0]["module"] is None
    assert result[0]["io_pattern"] == "generic"


def test_parse_meta_list_result_skips_invalid():
    response = {
        "ok": True,
        "result": {
            "functions": [
                {
                    "fn_id": "test.valid",
                    "name": "Valid",
                    "summary": "Summary",
                },
                {
                    "fn_id": "test.invalid",
                    # missing name and summary
                },
            ]
        },
    }
    result = parse_meta_list_result(response)
    assert len(result) == 1
    assert result[0]["fn_id"] == "test.valid"


def test_parse_meta_describe_result_valid():
    response = {
        "ok": True,
        "result": {
            "params_schema": {"type": "object"},
            "tool_version": "1.0.0",
            "introspection_source": "test",
        },
    }
    result = parse_meta_describe_result(response)
    assert result is not None
    assert result["params_schema"] == {"type": "object"}
    assert result["tool_version"] == "1.0.0"


def test_parse_meta_describe_result_invalid():
    response = {
        "ok": True,
        "result": {
            "params_schema": {"type": "object"},
            # missing tool_version and introspection_source
        },
    }
    assert parse_meta_describe_result(response) is None


def test_parse_meta_describe_result_error_shape():
    response = {"ok": False, "error": "not found"}
    assert parse_meta_describe_result(response) is None
