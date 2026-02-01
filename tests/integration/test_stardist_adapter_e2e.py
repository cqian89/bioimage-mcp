"""End-to-end integration test for StarDist integration.

This test validates StarDist execution via the persistent worker subprocess
interface, running from the core server environment (Py3.13) without
direct imports of StarDist or tool entrypoints.

The bioimage-mcp-stardist environment must be installed for this test to pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from bioio.writers import OmeTiffWriter

from bioimage_mcp.api.execution import execute_step


@pytest.mark.requires_env("bioimage-mcp-stardist")
class TestStarDistIntegrationE2E:
    """End-to-end tests for StarDist tool pack execution via persistent worker."""

    @pytest.fixture
    def sample_image(self, tmp_path):
        """Create a deterministic OME-TIFF input image."""
        path = tmp_path / "stardist_input.ome.tif"
        # 2D image for StarDist2D: (T, C, Z, Y, X)
        # We'll use 128x128 to keep it small
        data = np.zeros((1, 1, 1, 128, 128), dtype=np.uint8)

        # Add some "nuclei" (blobs)
        for i in range(5):
            y, x = 30 + i * 20, 30 + i * 20
            # Create a 10x10 blob
            data[0, 0, 0, y - 5 : y + 5, x - 5 : x + 5] = 200

        OmeTiffWriter.save(data, path, dim_order="TCZYX")
        return path

    def test_stardist_full_workflow_e2e(self, mcp_services, sample_image):
        """Test StarDist execution path from core server to tool env subprocess.

        This validates:
        1. Function execution via PersistentWorkerManager
        2. ObjectRef handoff between steps in the same worker/session
        3. Real StarDist inference (labels + details)
        """
        config = mcp_services["config"]
        # Reuse worker manager from ExecutionService to ensure session isolation
        worker_manager = mcp_services["execution"]._worker_manager
        session_id = "stardist-e2e-session"
        env_id = "bioimage-mcp-stardist"

        work_dir = mcp_services["tmp_path"] / "stardist_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: Initialize Model ---
        # stardist.models.StarDist2D.from_pretrained
        init_res, init_log, init_exit = execute_step(
            config=config,
            fn_id="stardist.models.StarDist2D.from_pretrained",
            params={"name": "2D_versatile_fluo"},
            inputs={},
            work_dir=work_dir,
            timeout_seconds=300,  # Downloading model can be slow
            worker_manager=worker_manager,
            session_id=session_id,
        )

        assert init_res.get("ok") is True, f"Model init failed: {init_res.get('error')}"
        model_ref = init_res["outputs"]["model"]
        assert model_ref["type"] == "ObjectRef"
        assert "uri" in model_ref

        # Task 2: Assert worker is alive and capture PID
        assert worker_manager.is_worker_alive(session_id, env_id) is True
        worker = worker_manager.get_worker(session_id, env_id)
        worker_pid = worker.process_id
        assert worker_pid > 0

        # --- Step 2: Run Inference ---
        # stardist.models.StarDist2D.predict_instances
        predict_res, predict_log, predict_exit = execute_step(
            config=config,
            fn_id="stardist.models.StarDist2D.predict_instances",
            inputs={
                "model": model_ref,
                "image": {
                    "uri": f"file://{sample_image.absolute()}",
                    "type": "BioImageRef",
                    "format": "OME-TIFF",
                },
            },
            params={"prob_thresh": 0.5},
            work_dir=work_dir,
            timeout_seconds=300,
            worker_manager=worker_manager,
            session_id=session_id,
        )

        assert predict_res.get("ok") is True, (
            f"Prediction failed: {predict_res.get('error')}\nLog: {predict_log}"
        )

        # Task 2: Assert PID reuse
        current_worker = worker_manager.get_worker(session_id, env_id)
        assert current_worker.process_id == worker_pid, "Worker PID should be reused across steps"

        # --- Verification ---
        outputs = predict_res["outputs"]
        assert "labels" in outputs
        assert "details" in outputs

        # Labels should be OME-Zarr LabelImageRef
        assert outputs["labels"]["type"] == "LabelImageRef"
        assert outputs["labels"]["format"] == "OME-Zarr"
        assert Path(outputs["labels"]["path"]).exists()

        # Details should be NativeOutputRef containing coord/points/etc
        assert outputs["details"]["type"] == "NativeOutputRef"
        assert Path(outputs["details"]["path"]).exists()
        with open(outputs["details"]["path"]) as f:
            details = json.load(f)
            assert isinstance(details, dict)
            assert "coord" in details
            assert "points" in details
            # We added 5 blobs, should see some points
            assert len(details["points"]) >= 5
