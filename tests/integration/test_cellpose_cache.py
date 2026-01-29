"""Integration tests for Cellpose cache management (T051)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile


@pytest.mark.integration
class TestCellposeCache:
    """Integration tests for cellpose.cache.clear."""

    def test_cache_clear_removes_all_objects(self, mcp_services, tmp_path: Path) -> None:
        """T051: Test that cellpose.cache.clear removes all objects from the cache."""
        execution = mcp_services["execution"]

        # 1. Create multiple models (ObjectRefs)
        res1 = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel",
                        "params": {"model_type": "cyto3"},
                    }
                ]
            }
        )
        assert res1["status"] == "success"
        model_ref1 = res1["outputs"]["model"]

        res2 = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel",
                        "params": {"model_type": "nuclei"},
                    }
                ]
            }
        )
        assert res2["status"] == "success"
        res2["outputs"]["model"]

        # 2. Verify we can use at least one of them
        img_path = tmp_path / "test_image.ome.tif"
        data = np.zeros((1, 1, 1, 64, 64), dtype=np.uint16)
        tifffile.imwrite(str(img_path), data, ome=True)

        res3 = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel.eval",
                        "inputs": {
                            "model": model_ref1,
                            "x": {"type": "BioImageRef", "uri": f"file://{img_path}"},
                        },
                    }
                ]
            }
        )
        assert res3["status"] == "success"

        # 3. Call cellpose.cache.clear
        res4 = execution.run_workflow({"steps": [{"id": "cellpose.cache.clear", "params": {}}]})
        assert res4["status"] == "success", f"cellpose.cache.clear failed: {res4.get('error')}"

        # 4. Verify cached objects are gone
        # Trying to use model_ref1 should now fail
        res5 = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel.eval",
                        "inputs": {
                            "model": model_ref1,
                            "x": {"type": "BioImageRef", "uri": f"file://{img_path}"},
                        },
                    }
                ]
            }
        )
        assert res5["status"] == "failed"
        assert "Object not found" in str(res5.get("error"))
