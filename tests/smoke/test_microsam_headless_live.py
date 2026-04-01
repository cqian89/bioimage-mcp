from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pytest
import tifffile
from bioio import BioImage


@pytest.mark.smoke_extended
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-microsam")
@pytest.mark.anyio
async def test_microsam_prompt_based_segmentation(live_server, smoke_tmp_dir):
    """Test prompt-based segmentation with micro_sam."""
    # 1. Create a tiny synthetic 2D image (bright disk on dark background)
    img_data = np.zeros((64, 64), dtype=np.uint8)
    y, x = np.ogrid[:64, :64]
    mask = (y - 32) ** 2 + (x - 32) ** 2 <= 10**2
    img_data[mask] = 255

    # Use an allowed path for input (FR-016)
    allowed_tmp = smoke_tmp_dir / "microsam"
    allowed_tmp.mkdir(parents=True, exist_ok=True)
    img_path = allowed_tmp / f"microsam_test_prompt_{uuid.uuid4().hex[:8]}.tif"
    tifffile.imwrite(img_path, img_data)

    try:
        # 2. Load via base.io.bioimage.load
        load_result = await live_server.call_tool(
            "run",
            {
                "id": "base.io.bioimage.load",
                "inputs": {},
                "params": {"path": str(img_path)},
            },
        )
        assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
        img_ref = load_result["outputs"]["image"]

        # 3. Call micro_sam.compute_embedding
        embed_result = await live_server.call_tool(
            "run",
            {
                "id": "micro_sam.compute_embedding",
                "inputs": {"image": img_ref},
                "params": {"model": "vit_b"},
            },
        )
        print(f"DEBUG: embed_result={embed_result}")
        assert embed_result.get("status") == "success", (
            f"Embedding failed: {embed_result.get('error')}"
        )
        assert "MICROSAM_MODEL_LOAD_START" in embed_result.get("warnings", [])
        assert "MICROSAM_EMBEDDING_COMPUTE_DONE" in embed_result.get("warnings", [])
        predictor_ref = embed_result["outputs"]["output"]

        # 3b. Call micro_sam.compute_embedding AGAIN (should hit cache)
        embed_result_2 = await live_server.call_tool(
            "run",
            {
                "id": "micro_sam.compute_embedding",
                "inputs": {"image": img_ref},
                "params": {"model": "vit_b"},
            },
        )
        assert embed_result_2.get("status") == "success"
        assert "MICROSAM_CACHE_HIT" in embed_result_2.get("warnings", [])
        # Markers should NOT be present on cache hit because we skip model load/set_image
        assert "MICROSAM_MODEL_LOAD_START" not in embed_result_2.get("warnings", [])

        # 4. Call micro_sam.prompt_based_segmentation.segment_from_points
        # Positive prompt at the center of the disk
        seg_result = await live_server.call_tool(
            "run",
            {
                "id": "micro_sam.prompt_based_segmentation.segment_from_points",
                "inputs": {"predictor": predictor_ref, "image": img_ref},
                "params": {"points": [[32, 32]], "labels": [1]},
            },
        )
        assert seg_result["status"] == "success", f"Segmentation failed: {seg_result.get('error')}"
        labels_ref = seg_result["outputs"]["output"]

        # 5. Assertions
        assert labels_ref["type"] == "LabelImageRef"

        # Verify files exist
        uri = labels_ref["uri"]
        assert uri.startswith("file://")
        labels_path = Path(uri.replace("file://", ""))
        # Simple fix for Windows absolute paths in URI
        if labels_path.as_posix().startswith("/C:"):
            labels_path = Path(labels_path.as_posix()[1:])

        assert labels_path.exists()

        # Check label image content
        mcp_img = BioImage(labels_path)
        mcp_data = np.asarray(mcp_img.data).squeeze()
        assert np.max(mcp_data) >= 1

    finally:
        if img_path.exists():
            img_path.unlink()


@pytest.mark.smoke_extended
@pytest.mark.requires_env("bioimage-mcp-microsam")
@pytest.mark.anyio
async def test_microsam_instance_segmentation(live_server, smoke_tmp_dir):
    """Test automatic/instance segmentation with micro_sam."""
    # Create tiny synthetic image
    img_data = np.zeros((16, 16), dtype=np.uint8)
    y, x = np.ogrid[:16, :16]
    mask = (y - 8) ** 2 + (x - 8) ** 2 <= 3**2
    img_data[mask] = 255

    allowed_tmp = smoke_tmp_dir / "microsam"
    allowed_tmp.mkdir(parents=True, exist_ok=True)
    img_path = allowed_tmp / f"microsam_test_inst_{uuid.uuid4().hex[:8]}.tif"
    tifffile.imwrite(img_path, img_data)

    try:
        # Load image
        load_result = await live_server.call_tool(
            "run",
            {
                "id": "base.io.bioimage.load",
                "inputs": {},
                "params": {"path": str(img_path)},
            },
        )
        img_ref = load_result["outputs"]["image"]

        # Call micro_sam.instance_segmentation.automatic_mask_generator
        # Use precomputed predictor to save time and ensure consistency
        embed_result = await live_server.call_tool(
            "run",
            {
                "id": "micro_sam.compute_embedding",
                "inputs": {"image": img_ref},
                "params": {"model": "vit_b"},
            },
        )
        predictor_ref = embed_result["outputs"]["output"]

        seg_result = await live_server.call_tool(
            "run",
            {
                "id": "micro_sam.instance_segmentation.automatic_mask_generator",
                "inputs": {"image": img_ref, "predictor": predictor_ref},
                "params": {"points_per_side": 1},
            },
        )
        assert seg_result.get("status") == "success", f"AMG failed: {seg_result.get('error')}"
        assert seg_result["outputs"]["output"]["type"] == "LabelImageRef"

    finally:
        if img_path.exists():
            img_path.unlink()


@pytest.mark.smoke_extended
@pytest.mark.requires_env("bioimage-mcp-microsam")
@pytest.mark.anyio
async def test_microsam_list_inclusion(live_server):
    """Verify that sam_annotator entrypoints are exposed in list."""
    flattened_list = await live_server.call_tool(
        "list", {"path": "micro_sam", "flatten": True, "limit": 200}
    )
    ids = [item["id"] for item in flattened_list["items"]]
    assert any("sam_annotator.annotator_2d" in item_id for item_id in ids)
