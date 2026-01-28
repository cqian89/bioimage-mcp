"""End-to-end integration test for CellposeAdapter.

This test requires the bioimage-mcp-cellpose environment to be installed.
Run with: conda run -n bioimage-mcp-cellpose pytest tests/integration/test_cellpose_adapter_e2e.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Skip entire module if cellpose not available
cellpose = pytest.importorskip("cellpose")
if isinstance(cellpose, MagicMock):
    pytest.skip("Cellpose is mocked; skipping integration test", allow_module_level=True)


class TestCellposeAdapterE2E:
    """End-to-end tests for CellposeAdapter execution."""

    @pytest.fixture
    def sample_image_path(self):
        """Get path to a sample image for testing."""
        # Use a small image from datasets
        sample = Path("datasets/FLUTE_FLIM_data_tif/hMSC control.tif")
        if not sample.exists():
            pytest.skip(f"Sample image not found: {sample}")
        try:
            from bioio import BioImage

            BioImage(sample)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"Sample image could not be read: {exc}")
        return sample

    @pytest.fixture
    def work_dir(self, tmp_path):
        """Create a temporary work directory."""
        return tmp_path / "cellpose_test"

    def test_cellpose_adapter_discover_with_real_cellpose(self):
        """CellposeAdapter discovers eval function with real cellpose."""
        from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

        adapter = CellposeAdapter()
        metadata = adapter.discover({"modules": ["cellpose.models"]})

        assert len(metadata) > 0

        eval_meta = next((m for m in metadata if "eval" in m.name.lower()), None)
        assert eval_meta is not None
        assert eval_meta.io_pattern.value == "image_to_labels"

    def test_cellpose_adapter_execute_eval(self, sample_image_path, work_dir):
        """CellposeAdapter can execute eval on real image."""
        from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

        adapter = CellposeAdapter()
        work_dir.mkdir(parents=True, exist_ok=True)

        # Create input artifact reference
        input_artifact = {
            "uri": f"file://{sample_image_path.absolute()}",
            "type": "BioImageRef",
            "format": "OME-TIFF",
        }

        # Execute eval with minimal params
        # Note: CellposeAdapter.execute currently calls run_segment regardless of fn_id
        outputs = adapter.execute(
            fn_id="cellpose.models.CellposeModel.eval",
            inputs=[input_artifact],
            params={"model_type": "cyto3", "diameter": 30.0},
            work_dir=work_dir,
        )

        # Verify outputs
        assert len(outputs) >= 1
        labels_output = outputs[0]
        assert labels_output["type"] == "LabelImageRef"
        assert Path(labels_output["path"]).exists()

    def test_cellpose_adapter_dimension_hints(self):
        """CellposeAdapter returns dimension hints for eval."""
        from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter

        adapter = CellposeAdapter()
        hints = adapter.generate_dimension_hints("cellpose.models", "eval")

        assert hints is not None
        assert hints.max_ndim == 3
        assert hints.preprocessing_instructions is not None
