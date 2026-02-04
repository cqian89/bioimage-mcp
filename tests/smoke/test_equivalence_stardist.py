from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np
import pytest
from bioio import BioImage

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def native_executor():
    return NativeExecutor()


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-stardist")
@pytest.mark.requires_stardist
@pytest.mark.anyio
async def test_stardist_equivalence(live_server, helper, native_executor, tmp_path):
    """Test that MCP StarDist matches native StarDist (IoU > 0.95)."""
    model_name = "2D_versatile_fluo"

    # 1. Run Native Baseline to produce input and reference labels
    baseline_script = Path(__file__).parent / "reference_scripts" / "stardist_baseline.py"
    # StarDist baseline generates its own input image from stardist.data
    # Use an allowed path for input (FR-016)
    allowed_tmp = Path.cwd() / "datasets" / "smoke_tmp"
    allowed_tmp.mkdir(parents=True, exist_ok=True)
    import uuid

    unique_id = uuid.uuid4().hex[:8]
    native_input_path = allowed_tmp / f"stardist_input_{unique_id}.ome.tiff"
    native_output_path = tmp_path / "native_labels.ome.tiff"

    try:
        baseline_result = native_executor.run_script(
            env_name="bioimage-mcp-stardist",
            script_path=baseline_script,
            args=[
                "--input",
                str(native_input_path),
                "--output",
                str(native_output_path),
                "--model_name",
                model_name,
            ],
        )
        assert baseline_result["status"] == "success", f"Baseline failed: {baseline_result}"

        # 2. Run MCP StarDist
        # Load the EXACT SAME image via MCP to get a BioImageRef
        load_result = await live_server.call_tool(
            "run",
            {
                "id": "base.io.bioimage.load",
                "inputs": {},
                "params": {"path": str(native_input_path)},
            },
        )
        assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
        img_ref = load_result["outputs"]["image"]

        # Initialize model with retry
        model_ref = None
        model_init_result = None
        for attempt in range(3):
            try:
                model_init_result = await live_server.call_tool(
                    "run",
                    {
                        "id": "stardist.models.StarDist2D.from_pretrained",
                        "inputs": {},
                        "params": {"name": model_name},
                    },
                )
                if model_init_result["status"] == "success":
                    model_ref = model_init_result["outputs"]["model"]
                    break
            except Exception:
                pass

            if attempt < 2:
                await asyncio.sleep(5 * (attempt + 1))

        assert model_ref is not None, f"Model init failed after 3 attempts: {model_init_result}"

        # Run prediction
        mcp_result = await live_server.call_tool(
            "run",
            {
                "id": "stardist.models.StarDist2D.predict_instances",
                "inputs": {"model": model_ref, "image": img_ref},
                # Use defaults for params
            },
        )
        assert mcp_result.get("status") == "success", f"MCP run failed: {mcp_result}"

        # 3. Structural assertions
        outputs = mcp_result["outputs"]
        assert "labels" in outputs
        assert "details" in outputs

        mcp_labels_ref = outputs["labels"]
        mcp_details_ref = outputs["details"]

        assert mcp_labels_ref["type"] == "LabelImageRef"
        assert mcp_labels_ref["format"] == "OME-Zarr"

        assert mcp_details_ref["type"] == "NativeOutputRef"
        assert mcp_details_ref["format"] == "stardist-details-json"

        # Verify files exist
        mcp_labels_uri = mcp_labels_ref["uri"]
        assert mcp_labels_uri.startswith("file://")
        mcp_labels_path = Path(mcp_labels_uri.replace("file://", ""))
        assert mcp_labels_path.exists()

        mcp_details_uri = mcp_details_ref["uri"]
        assert mcp_details_uri.startswith("file://")
        mcp_details_path = Path(mcp_details_uri.replace("file://", ""))
        assert mcp_details_path.exists()

        # Check details content
        with open(mcp_details_path) as f:
            details = json.load(f)
        assert "coord" in details
        assert "points" in details

        # Check labels shape/dtype
        mcp_img = BioImage(mcp_labels_path)
        # Native input was YX, so labels should be YX (might be wrapped in TCZYX depending on bioio)
        mcp_data = np.asarray(mcp_img.data).squeeze()
        assert mcp_data.ndim == 2
        assert mcp_data.dtype in (np.uint16, np.uint32)

        label_count = int(np.max(mcp_data))
        assert 50 < label_count < 200  # Nuclei test image usually has around 100-150

        # 4. Equivalence assertion
        native_img = BioImage(native_output_path)
        native_data = np.asarray(native_img.data).squeeze()

        helper.assert_labels_equivalent(mcp_data, native_data, iou_threshold=0.95)
    finally:
        if native_input_path.exists():
            native_input_path.unlink()
