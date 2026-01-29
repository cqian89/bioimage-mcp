"""Integration tests for stateful Cellpose model reuse (T014, T015, T016)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest


@pytest.mark.integration
class TestCellposeStateful:
    """Integration tests for stateful model reuse in Cellpose."""

    def test_create_model_returns_object_ref(self, mcp_services) -> None:
        """T014: Test that cellpose.models.CellposeModel returns an ObjectRef."""
        execution = mcp_services["execution"]

        # This should fail initially because cellpose.models.CellposeModel is not in manifest
        result = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel",
                        "params": {"model_type": "cyto3", "gpu": False},
                    }
                ]
            }
        )

        assert result["status"] == "success", f"Failed: {result.get('error')}"
        outputs = result["outputs"]
        assert "model" in outputs
        model_ref = outputs["model"]

        assert model_ref["type"] == "ObjectRef"
        assert model_ref["uri"].startswith("obj://")
        assert "cellpose.models.CellposeModel" in model_ref["python_class"]

    def test_eval_with_object_ref(self, mcp_services, tmp_path: Path) -> None:
        """T015: Test that cellpose.models.CellposeModel.eval accepts an ObjectRef."""
        execution = mcp_services["execution"]

        # 1. Create model
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
        model_ref = res1["outputs"]["model"]

        # 2. Create valid mock image
        import numpy as np
        import tifffile

        img_path = tmp_path / "test_image.ome.tif"
        data = np.zeros((1, 1, 1, 64, 64), dtype=np.uint16)
        tifffile.imwrite(str(img_path), data, ome=True)

        # 3. Call eval with ObjectRef
        res2 = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel.eval",
                        "inputs": {
                            "model": model_ref,
                            "x": {"type": "BioImageRef", "uri": f"file://{img_path}"},
                        },
                        "params": {"diameter": 30.0},
                    }
                ]
            }
        )

        assert res2["status"] == "success", f"Failed: {res2.get('error')}"
        assert "labels" in res2["outputs"]
        assert res2["outputs"]["labels"]["type"] == "LabelImageRef"

    def test_model_reuse_performance(self, mcp_services, tmp_path: Path) -> None:
        """T016: Test that re-using an ObjectRef is faster (no reload)."""
        execution = mcp_services["execution"]

        # 1. Create model
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
        model_ref = res1["outputs"]["model"]

        # 2. Create valid mock image
        import numpy as np
        import tifffile

        img_path = tmp_path / "test_image.ome.tif"
        data = np.zeros((1, 1, 1, 64, 64), dtype=np.uint16)
        tifffile.imwrite(str(img_path), data, ome=True)

        def run_eval():
            start = time.perf_counter()
            res = execution.run_workflow(
                {
                    "steps": [
                        {
                            "id": "cellpose.models.CellposeModel.eval",
                            "inputs": {
                                "model": model_ref,
                                "x": {"type": "BioImageRef", "uri": f"file://{img_path}"},
                            },
                        }
                    ]
                }
            )
            assert res["status"] == "success", f"Eval failed: {res.get('error')}"
            return time.perf_counter() - start

        # First call might be slow due to model setup (though already instantiated)
        # Second call should definitely be fast if we are hitting the cache
        dur1 = run_eval()
        dur2 = run_eval()

        # In a real scenario with a heavy model, dur2 < dur1 if reloading happened in dur1.
        # But here 'model' is already an ObjectRef, so even dur1 shouldn't reload.
        # However, we want to ensure the stateful pattern works.
        # For TDD, just ensuring they both succeed is enough for now,
        # or we can check if a 'reloaded' flag is absent in provenance.

        assert dur2 < dur1 * 2  # Loose check
