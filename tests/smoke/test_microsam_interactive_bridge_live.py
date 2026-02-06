from __future__ import annotations

import pytest


@pytest.mark.smoke_extended
@pytest.mark.requires_env("bioimage-mcp-microsam")
@pytest.mark.anyio
async def test_microsam_annotator_discovery(live_server):
    """Confirm sam_annotator tools are discovered and described correctly."""
    # List tools
    list_result = await live_server.call_tool(
        "list", {"path": "micro_sam", "flatten": True, "limit": 200}
    )
    items = list_result["items"]
    ids = [item["id"] for item in items]

    # 2D, 3D and Tracking should be there
    assert "micro_sam.sam_annotator.annotator_2d" in ids
    assert "micro_sam.sam_annotator.annotator_3d" in ids
    assert "micro_sam.sam_annotator.annotator_tracking" in ids

    # Describe annotator_2d
    desc_result = await live_server.call_tool(
        "describe", {"id": "micro_sam.sam_annotator.annotator_2d"}
    )
    assert desc_result["id"] == "micro_sam.sam_annotator.annotator_2d"
    assert "params_schema" in desc_result

    # Check inputs match SAM_ANNOTATOR pattern
    inputs = desc_result["inputs"]
    assert "image" in inputs
    assert "embedding_path" in inputs
    assert "segmentation_result" in inputs
    assert inputs["image"]["type"] == "BioImageRef"


@pytest.mark.smoke_extended
@pytest.mark.requires_env("bioimage-mcp-microsam")
@pytest.mark.anyio
async def test_microsam_headless_failure(monkeypatch):
    """Confirm annotators fail deterministically in headless environments on Linux."""
    from tests.smoke.utils.mcp_client import TestMCPClient

    # Unset DISPLAY and set force headless to simulate headless Linux
    server_env = {
        "DISPLAY": "",
        "WAYLAND_DISPLAY": "",
        "BIOIMAGE_MCP_FORCE_HEADLESS": "1",
    }

    client = TestMCPClient(server_env=server_env)
    await client.start_with_timeout(30)
    try:
        # Attempt to run annotator_2d (with dummy inputs to get past validation)
        # We expect HEADLESS_DISPLAY_REQUIRED error
        result = await client.call_tool(
            "run",
            {
                "id": "micro_sam.sam_annotator.annotator_2d",
                "inputs": {"image": {"type": "BioImageRef", "uri": "file:///tmp/dummy.tif"}},
                "params": {},
            },
        )

        import sys

        if sys.platform == "linux":
            assert result["status"] == "failed"
            assert result["error"]["code"] == "HEADLESS_DISPLAY_REQUIRED"
        else:
            # On other platforms it might try to open napari and fail later or succeed if display exists
            pytest.skip("Headless failure test is Linux-specific in current implementation")
    finally:
        await client.stop()


@pytest.mark.smoke_extended
@pytest.mark.requires_env("bioimage-mcp-microsam")
@pytest.mark.anyio
async def test_microsam_responsive_during_concurrent_calls(live_server):
    """
    Independent MCP list/describe calls remain responsive even with concurrent activity.
    """
    import asyncio

    # Concurrent calls to metadata APIs
    tasks = [
        live_server.call_tool("list", {"path": "micro_sam"}),
        live_server.call_tool("describe", {"id": "micro_sam.sam_annotator.annotator_2d"}),
        live_server.call_tool("list", {"path": "base"}),
    ]

    results = await asyncio.gather(*tasks)

    # Verify results are valid (not errors)
    assert "items" in results[0]
    assert "params_schema" in results[1]
    assert "items" in results[2]
