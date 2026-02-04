from __future__ import annotations

import base64
import time
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_smoke_bioimage_preview(live_server, sample_image):
    # Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(sample_image)},
        },
    )
    img_ref = load_result["outputs"]["image"]
    ref_id = img_ref["ref_id"]

    # Get info
    info = await live_server.call_tool(
        "artifact_info", {"ref_id": ref_id, "include_image_preview": True}
    )

    assert "image_preview" in info
    preview = info["image_preview"]
    assert "base64" in preview

    img_data = base64.b64decode(preview["base64"])
    img = Image.open(BytesIO(img_data))
    assert max(img.size) <= 256


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_smoke_label_preview(live_server, sample_image):
    # Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(sample_image)},
        },
    )
    img_ref = load_result["outputs"]["image"]

    # Label the image (works on any array)
    label_result = await live_server.call_tool(
        "run",
        {
            "id": "base.skimage.measure.label",
            "inputs": {"image": img_ref},
        },
    )
    if "error" in label_result:
        pytest.fail(f"Label run failed: {label_result['error']}")

    # Try different possible output keys
    label_ref = (
        label_result["outputs"].get("labels")
        or label_result["outputs"].get("output")
        or label_result["outputs"].get("image")
    )
    if not label_ref:
        pytest.fail(
            f"Label run result missing expected output keys. Keys found: {list(label_result['outputs'].keys())}"
        )

    assert label_ref["type"] == "LabelImageRef", f"Expected LabelImageRef, got {label_ref['type']}"

    info = await live_server.call_tool(
        "artifact_info", {"ref_id": label_ref["ref_id"], "include_image_preview": True}
    )

    assert "image_preview" in info
    preview = info["image_preview"]
    assert "region_count" in preview
    assert "centroids" in preview

    img_data = base64.b64decode(preview["base64"])
    img = Image.open(BytesIO(img_data))
    assert img.mode == "RGBA"


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_smoke_table_preview(live_server):
    repo_root = Path(__file__).resolve().parents[2]
    csv_path = repo_root / "datasets" / "sample_measurements.csv"
    if not csv_path.exists():
        pytest.skip(f"Dataset missing: {csv_path}")

    # Load table
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.table.load",
            "inputs": {},
            "params": {"path": str(csv_path)},
        },
    )
    table_ref = load_result["outputs"]["table"]

    info = await live_server.call_tool(
        "artifact_info", {"ref_id": table_ref["ref_id"], "include_table_preview": True}
    )

    assert "table_preview" in info
    assert "|" in info["table_preview"]
    assert "dtypes" in info


@pytest.mark.smoke_extended
@pytest.mark.anyio
async def test_smoke_preview_performance(live_server, sample_image):
    # Load image
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(sample_image)},
        },
    )
    ref_id = load_result["outputs"]["image"]["ref_id"]

    start = time.time()
    await live_server.call_tool("artifact_info", {"ref_id": ref_id, "include_image_preview": True})
    duration = time.time() - start

    assert duration < 5.0
