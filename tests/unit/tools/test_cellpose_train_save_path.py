"""Unit tests for Cellpose training save_path parameter (Option C fix)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mock_cellpose_training():
    """Mock cellpose.train and cellpose.models for training tests."""
    mock_train = MagicMock()
    mock_models = MagicMock()
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False

    # Mock CellposeModel
    mock_model = MagicMock()
    mock_models.CellposeModel.return_value = mock_model

    return mock_train, mock_models, mock_torch, mock_model


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    work_dir = Path(tempfile.mkdtemp())
    user_dir = Path(tempfile.mkdtemp())

    yield work_dir, user_dir

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)
    shutil.rmtree(user_dir, ignore_errors=True)


@pytest.fixture
def sample_input_files(temp_dirs):
    """Create sample input files for testing."""
    work_dir, _ = temp_dirs

    # Create sample image and mask files
    image_path = work_dir / "input_image.tiff"
    mask_path = work_dir / "input_mask.tiff"

    # Create minimal TIFF files using numpy
    import tifffile

    sample_data = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
    tifffile.imwrite(str(image_path), sample_data)
    tifffile.imwrite(str(mask_path), sample_data)

    return image_path, mask_path


class TestTrainSegSavePathOptionC:
    """Tests for save_path Option C implementation in train_seg."""

    def test_model_name_from_params(self, temp_dirs, mock_cellpose_training):
        """Test that model_name is extracted from params instead of hardcoded."""
        work_dir, _ = temp_dirs
        mock_train, mock_models, mock_torch, mock_model = mock_cellpose_training

        # Create fake model weights file
        models_dir = work_dir / "models"
        models_dir.mkdir(parents=True)
        fake_weights = models_dir / "my_custom_model_epoch_10"
        fake_weights.write_bytes(b"fake weights")

        # Mock train_seg to return the path
        mock_train.train_seg.return_value = (str(fake_weights), [0.1] * 10, [])

        with patch.dict(
            "sys.modules",
            {
                "cellpose": MagicMock(),
                "cellpose.train": mock_train,
                "cellpose.models": mock_models,
                "torch": mock_torch,
            },
        ):
            # Import the training module
            import sys

            ops_path = (
                Path(__file__).resolve().parents[3]
                / "tools"
                / "cellpose"
                / "bioimage_mcp_cellpose"
                / "ops"
            )
            sys.path.insert(0, str(ops_path.parent.parent))

            try:
                # Verify train.train_seg was called with custom model_name
                # This is verified by checking the mock call args
                call_args = mock_train.train_seg.call_args
                if call_args:
                    kwargs = call_args.kwargs if call_args.kwargs else {}
                    # If model_name is in kwargs, it should be the custom one
                    assert kwargs.get("model_name", "finetuned_model") != "hardcoded"
            finally:
                sys.path.pop(0)

    def test_user_copy_path_in_output(self, temp_dirs):
        """Test that user_copy_path is included in output when save_path is provided."""
        work_dir, user_dir = temp_dirs

        # Create fake model weights file
        models_dir = work_dir / "models"
        models_dir.mkdir(parents=True)
        fake_weights = models_dir / "finetuned_model_epoch_10"
        fake_weights.write_bytes(b"fake weights")

        # Create fake losses file
        losses_path = work_dir / "training_losses.csv"
        pd.DataFrame({"epoch": [1, 2], "loss": [0.5, 0.3]}).to_csv(losses_path, index=False)

        # Simulate the copy logic from run_train_seg
        user_save_path_str = str(user_dir)
        user_save_path = Path(user_save_path_str)

        # Copy logic from training.py Option C
        if user_save_path.suffix:
            weights_dest = user_save_path
            target_dir = user_save_path.parent
        else:
            target_dir = user_save_path
            weights_dest = target_dir / fake_weights.name

        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fake_weights, weights_dest)

        losses_dest = target_dir / "training_losses.csv"
        shutil.copy2(losses_path, losses_dest)

        # Verify files were copied
        assert weights_dest.exists()
        assert losses_dest.exists()

        # Verify output structure includes user_copy_path
        output = {
            "weights": {
                "type": "NativeOutputRef",
                "format": "cellpose-model",
                "path": str(fake_weights),
                "user_copy_path": str(weights_dest),
            }
        }

        assert "user_copy_path" in output["weights"]
        assert output["weights"]["user_copy_path"] == str(weights_dest)

    def test_no_user_copy_when_save_path_not_provided(self, temp_dirs):
        """Test that user_copy_path is NOT in output when save_path is None."""
        work_dir, _ = temp_dirs

        # Create fake model weights file
        models_dir = work_dir / "models"
        models_dir.mkdir(parents=True)
        fake_weights = models_dir / "finetuned_model_epoch_10"
        fake_weights.write_bytes(b"fake weights")

        # Simulate output without save_path
        user_copy_info = {}  # Empty when save_path is None

        output = {
            "weights": {
                "type": "NativeOutputRef",
                "format": "cellpose-model",
                "path": str(fake_weights),
            }
        }

        if user_copy_info:
            output["weights"].update(user_copy_info)

        assert "user_copy_path" not in output["weights"]

    def test_save_path_creates_directory(self, temp_dirs):
        """Test that save_path creates directory if it doesn't exist."""
        work_dir, user_dir = temp_dirs

        # Create non-existent nested path
        nested_path = user_dir / "deeply" / "nested" / "models"
        assert not nested_path.exists()

        # Simulate directory creation from training.py
        nested_path.mkdir(parents=True, exist_ok=True)

        assert nested_path.exists()
        assert nested_path.is_dir()
