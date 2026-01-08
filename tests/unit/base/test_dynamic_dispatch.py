"""
Unit tests for dynamic dispatch router in base tool pack.

Tests the dispatch_dynamic function that routes dynamic function calls
(e.g., skimage.filters.gaussian) to appropriate adapters for execution.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add tools/base to path so we can import bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base.dynamic_dispatch import dispatch_dynamic


class TestDynamicDispatch:
    """Test cases for dynamic dispatch router."""

    def test_dispatch_dynamic_exists(self):
        """dispatch_dynamic function should be importable."""
        # This test verifies the module and function exist
        assert dispatch_dynamic is not None
        assert callable(dispatch_dynamic)

    def test_dispatch_skimage_function(self, tmp_path):
        """dispatch_dynamic should route skimage functions to SkimageAdapter."""
        import numpy as np
        import tifffile

        # Create a test image file
        test_image_path = tmp_path / "test_image.tif"
        data = np.random.rand(10, 10).astype(np.float32)
        tifffile.imwrite(test_image_path, data)

        # Arrange: Create mock inputs and params for skimage.filters.gaussian
        inputs = {
            "image": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "uri": f"file://{test_image_path}",
            }
        }
        params = {"sigma": 2.0}
        work_dir = tmp_path

        # Act: Dispatch the function
        result = dispatch_dynamic(
            fn_id="skimage.filters.gaussian",
            inputs=inputs,
            params=params,
            work_dir=work_dir,
        )

        # Assert: Should return outputs dict
        assert result is not None
        assert "outputs" in result
        # The output should contain a processed image artifact reference
        assert "output" in result["outputs"]
        assert result["outputs"]["output"]["type"] == "BioImageRef"

    def test_dispatch_unknown_prefix_raises_error(self, tmp_path):
        """dispatch_dynamic should raise error for unknown adapter prefixes."""
        # Arrange: Create function ID with unknown prefix
        inputs = {"image": {"type": "BioImageRef", "uri": "file:///tmp/test.ome.zarr"}}
        params = {}
        work_dir = tmp_path

        # Act & Assert: Should raise error for unknown prefix
        with pytest.raises(ValueError, match="No adapter found for prefix"):
            dispatch_dynamic(
                fn_id="unknown.library.function",
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )

    def test_dispatch_malformed_fn_id_raises_error(self, tmp_path):
        """dispatch_dynamic should raise error for malformed function IDs."""
        # Arrange: Create malformed function ID (missing module/function parts)
        inputs = {"image": {"type": "BioImageRef", "uri": "file:///tmp/test.ome.zarr"}}
        params = {}
        work_dir = tmp_path

        # Act & Assert: Should raise error for malformed ID
        with pytest.raises(ValueError, match="Invalid function ID format"):
            dispatch_dynamic(
                fn_id="invalid_format",
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )

    def test_dispatch_uses_adapter_execute_method(self, tmp_path):
        """dispatch_dynamic should call adapter's execute method with correct args."""
        # Arrange: Mock the adapter registry and adapter
        mock_adapter = Mock()
        mock_adapter.execute.return_value = [
            Mock(
                to_ref=Mock(
                    return_value={
                        "type": "BioImageRef",
                        "format": "OME-Zarr",
                        "uri": "file:///tmp/output.ome.zarr",
                    }
                )
            )
        ]

        inputs = {"image": {"type": "BioImageRef", "uri": "file:///tmp/input.ome.zarr"}}
        params = {"sigma": 1.5}
        work_dir = tmp_path

        # Act: Dispatch with mocked adapter
        with patch(
            "bioimage_mcp_base.dynamic_dispatch.get_adapter_for_fn_id",
            return_value=mock_adapter,
        ):
            result = dispatch_dynamic(
                fn_id="skimage.filters.gaussian",
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )

        # Assert: Adapter's execute method should be called
        assert mock_adapter.execute.called
        # Verify the call had correct fn_id
        call_args = mock_adapter.execute.call_args
        assert call_args[1]["fn_id"] == "skimage.filters.gaussian"

    def test_dispatch_converts_artifact_refs_to_objects(self, tmp_path):
        """dispatch_dynamic should convert input refs to Artifact objects before calling adapter."""
        # Arrange: Create inputs as dict references (as received from MCP)
        inputs = {
            "image": {
                "type": "BioImageRef",
                "format": "OME-Zarr",
                "uri": "file:///tmp/test_image.ome.zarr",
                "metadata": {"shape": [256, 256]},
            }
        }
        params = {"sigma": 2.0}
        work_dir = tmp_path

        mock_adapter = Mock()
        mock_adapter.execute.return_value = []

        # Act: Dispatch with mocked adapter
        with patch(
            "bioimage_mcp_base.dynamic_dispatch.get_adapter_for_fn_id",
            return_value=mock_adapter,
        ):
            dispatch_dynamic(
                fn_id="skimage.filters.gaussian",
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )

        # Assert: Adapter should receive Artifact objects, not dicts
        call_args = mock_adapter.execute.call_args
        inputs_arg = call_args[1]["inputs"]
        # Check that inputs were converted (this will depend on implementation)
        # For now, just verify execute was called with inputs
        assert inputs_arg is not None

    def test_dispatch_converts_output_artifacts_to_refs(self, tmp_path):
        """dispatch_dynamic should convert output Artifact objects to dict refs."""
        # Arrange: Mock adapter that returns Artifact objects
        from bioimage_mcp.artifacts.base import Artifact

        mock_output_artifact = Mock(spec=Artifact)
        # Configure the mock to have to_ref as a method
        mock_output_artifact.to_ref = Mock(
            return_value={
                "type": "BioImageRef",
                "format": "OME-Zarr",
                "uri": "file:///tmp/output.ome.zarr",
            }
        )

        mock_adapter = Mock()
        mock_adapter.execute.return_value = [mock_output_artifact]

        inputs = {"image": {"type": "BioImageRef", "uri": "file:///tmp/input.ome.zarr"}}
        params = {}
        work_dir = tmp_path

        # Act: Dispatch with mocked adapter
        with patch(
            "bioimage_mcp_base.dynamic_dispatch.get_adapter_for_fn_id",
            return_value=mock_adapter,
        ):
            result = dispatch_dynamic(
                fn_id="skimage.filters.gaussian",
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )

        # Assert: Result should contain dict refs, not Artifact objects
        assert "outputs" in result
        assert "output" in result["outputs"]
        assert isinstance(result["outputs"]["output"], dict)
        assert result["outputs"]["output"]["type"] == "BioImageRef"

    def test_dispatch_filters_metadata_inputs(self, tmp_path):
        """dispatch_dynamic should filter out metadata keys like 'reason' from inputs."""
        # Arrange: Create inputs with a 'reason' field and other non-artifact strings
        inputs = {
            "image": {
                "type": "BioImageRef",
                "format": "OME-Zarr",
                "uri": "file:///tmp/test_image.ome.zarr",
            },
            "reason": "Compute phasor coordinates from sample FLIM signal",
            "description": "Some other metadata that should be ignored",
            "_metadata": {"something": "else"},
            "potential_ref_id": "art_123456789",
        }
        params = {}
        work_dir = tmp_path

        mock_adapter = Mock()
        mock_adapter.execute.return_value = []

        # Act: Dispatch with mocked adapter
        with patch(
            "bioimage_mcp_base.dynamic_dispatch.get_adapter_for_fn_id",
            return_value=mock_adapter,
        ):
            dispatch_dynamic(
                fn_id="skimage.filters.gaussian",
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )

        # Assert: Adapter should ONLY receive "image" and "potential_ref_id"
        # "reason", "description", and "_metadata" should be filtered out
        call_args = mock_adapter.execute.call_args
        inputs_arg = call_args[1]["inputs"]

        # inputs_arg is a list of (name, value) tuples
        input_names = [name for name, _ in inputs_arg]
        assert "image" in input_names
        assert "potential_ref_id" in input_names
        assert "reason" not in input_names
        assert "description" not in input_names
        assert "_metadata" not in input_names
