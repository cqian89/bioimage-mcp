from unittest.mock import patch

from tools.microsam.bioimage_mcp_microsam.entrypoint import process_execute_request


def test_entrypoint_headless_error_mapping():
    request = {
        "command": "execute",
        "id": "micro_sam.sam_annotator.annotator_2d",
        "inputs": {},
        "params": {},
        "tool_config": {"microsam": {"device": "cpu"}},
    }

    # Mock select_device to avoid actually checking hardware
    with (
        patch("tools.microsam.bioimage_mcp_microsam.entrypoint.select_device"),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter.execute"
        ) as mock_exec,
    ):
        from bioimage_mcp.registry.dynamic.adapters.microsam import HeadlessDisplayRequiredError

        mock_exec.side_effect = HeadlessDisplayRequiredError("No display found")

        response = process_execute_request(request)

        assert response["ok"] is False
        assert response["error"]["code"] == "HEADLESS_DISPLAY_REQUIRED"
        assert "No display found" in response["error"]["message"]


def test_entrypoint_interactive_warnings():
    request = {
        "command": "execute",
        "id": "micro_sam.sam_annotator.annotator_2d",
        "inputs": {},
        "params": {},
        "tool_config": {"microsam": {"device": "cpu"}},
    }

    with (
        patch("tools.microsam.bioimage_mcp_microsam.entrypoint.select_device"),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter"
        ) as mock_adapter_class,
    ):
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.execute.return_value = []
        mock_adapter.warnings = ["MICROSAM_NO_CHANGES"]

        response = process_execute_request(request)

        assert response["ok"] is True
        assert "warnings" in response
        assert "MICROSAM_NO_CHANGES" in response["warnings"]


def test_entrypoint_device_hint_propagation():
    request = {
        "command": "execute",
        "id": "micro_sam.sam_annotator.annotator_2d",
        "inputs": {},
        "params": {},
        "tool_config": {"microsam": {"device": "cuda"}},
    }

    with (
        patch("tools.microsam.bioimage_mcp_microsam.entrypoint.select_device"),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter.execute"
        ) as mock_exec,
    ):
        mock_exec.return_value = []
        process_execute_request(request)

        # Verify hints passed to adapter.execute
        kwargs = mock_exec.call_args[1]
        assert kwargs["hints"]["device"] == "cuda"


def test_entrypoint_cache_hit_warning():
    request = {
        "command": "execute",
        "id": "micro_sam.sam_annotator.annotator_2d",
        "inputs": {"image": {"type": "BioImageRef", "uri": "file:///tmp/test.tif"}},
        "params": {},
        "tool_config": {"microsam": {"device": "cpu"}},
    }

    with (
        patch("tools.microsam.bioimage_mcp_microsam.entrypoint.select_device"),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter"
        ) as mock_adapter_class,
    ):
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.execute.return_value = []
        mock_adapter.warnings = ["MICROSAM_CACHE_HIT"]

        response = process_execute_request(request)

        assert response["ok"] is True
        assert "MICROSAM_CACHE_HIT" in response["warnings"]


def test_entrypoint_cache_reset_warning():
    request = {
        "command": "execute",
        "id": "micro_sam.sam_annotator.annotator_2d",
        "inputs": {"image": {"type": "BioImageRef", "uri": "file:///tmp/test.tif"}},
        "params": {"force_fresh": True},
        "tool_config": {"microsam": {"device": "cpu"}},
    }

    with (
        patch("tools.microsam.bioimage_mcp_microsam.entrypoint.select_device"),
        patch(
            "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter"
        ) as mock_adapter_class,
    ):
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.execute.return_value = []
        mock_adapter.warnings = ["MICROSAM_CACHE_RESET"]

        response = process_execute_request(request)

        assert response["ok"] is True
        assert "MICROSAM_CACHE_RESET" in response["warnings"]
