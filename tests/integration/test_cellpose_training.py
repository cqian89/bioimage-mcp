"""Integration tests for Cellpose training (T026)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile


@pytest.mark.integration
class TestCellposeTraining:
    """Integration tests for Cellpose training functions."""

    def test_train_seg_returns_weights_and_losses(self, mcp_services, tmp_path: Path) -> None:
        """T026: Test that cellpose.train.train_seg returns weights (NativeOutputRef) and losses (TableRef)."""
        execution = mcp_services["execution"]

        # 1. Create mock training data
        train_img_path = tmp_path / "train_img.ome.tif"
        train_mask_path = tmp_path / "train_mask.ome.tif"

        # 5D TCZYX data
        img_data = np.random.randint(0, 255, (1, 1, 1, 64, 64), dtype=np.uint8)
        mask_data = np.zeros((1, 1, 1, 64, 64), dtype=np.uint16)
        mask_data[0, 0, 0, 10:20, 10:20] = 1  # Mock a single cell

        tifffile.imwrite(str(train_img_path), img_data, ome=True)
        tifffile.imwrite(str(train_mask_path), mask_data, ome=True)

        # 2. Call train_seg
        # We expect weights (NativeOutputRef) and losses (TableRef)
        result = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.train.train_seg",
                        "inputs": {
                            "image": {"type": "BioImageRef", "uri": f"file://{train_img_path}"},
                            "mask": {"type": "LabelImageRef", "uri": f"file://{train_mask_path}"},
                        },
                        "params": {
                            "model_type": "cyto3",
                            "n_epochs": 1,
                            "batch_size": 1,
                        },
                    }
                ]
            }
        )

        # 3. Assertions
        # This is expected to fail initially because handle_train_seg returns ok=False
        # which results in status="failed" in run_workflow
        assert result["status"] == "success", f"Training failed: {result.get('error')}"
        outputs = result["outputs"]

        # Verify weights (NativeOutputRef)
        assert "weights" in outputs
        assert outputs["weights"]["type"] == "NativeOutputRef"

        # Verify losses (TableRef)
        assert "losses" in outputs
        assert outputs["losses"]["type"] == "TableRef"

    def test_trained_weights_can_initialize_model(self, mcp_services, tmp_path: Path) -> None:
        """T027: Test that weights from training can be used to initialize a new model."""
        execution = mcp_services["execution"]

        # 1. Prepare mock training data
        img_path = tmp_path / "train_img_2.ome.tif"
        mask_path = tmp_path / "train_mask_2.ome.tif"

        img_data = np.random.randint(0, 255, (1, 1, 1, 64, 64), dtype=np.uint8)
        mask_data = np.zeros((1, 1, 1, 64, 64), dtype=np.uint16)
        mask_data[0, 0, 0, 10:20, 10:20] = 1

        tifffile.imwrite(str(img_path), img_data, ome=True)
        tifffile.imwrite(str(mask_path), mask_data, ome=True)

        # 2. Run training
        train_res = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.train.train_seg",
                        "inputs": {
                            "image": {"type": "BioImageRef", "uri": f"file://{img_path}"},
                            "mask": {"type": "LabelImageRef", "uri": f"file://{mask_path}"},
                        },
                        "params": {
                            "model_type": "cyto3",
                            "n_epochs": 1,
                        },
                    }
                ]
            }
        )

        assert train_res["status"] == "success", f"Training failed: {train_res.get('error')}"
        weights_ref = train_res["outputs"]["weights"]

        # 3. Use weights to initialize a new model
        # Passing weights_ref to pretrained_model param
        init_res = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel",
                        "params": {
                            "pretrained_model": weights_ref,
                            "gpu": False,
                        },
                    }
                ]
            }
        )

        assert init_res["status"] == "success", (
            f"Model init with weights failed: {init_res.get('error')}"
        )
        model_ref = init_res["outputs"]["model"]
        assert model_ref["type"] == "ObjectRef"

        # 4. Verify model can be used for evaluation
        test_img_path = tmp_path / "test_image_2.ome.tif"
        test_data = np.random.randint(0, 255, (1, 1, 1, 64, 64), dtype=np.uint16)
        tifffile.imwrite(str(test_img_path), test_data, ome=True)

        eval_res = execution.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.models.CellposeModel.eval",
                        "inputs": {
                            "model": model_ref,
                            "x": {"type": "BioImageRef", "uri": f"file://{test_img_path}"},
                        },
                    }
                ]
            }
        )
        assert eval_res["status"] == "success", (
            f"Eval with fine-tuned model failed: {eval_res.get('error')}"
        )
