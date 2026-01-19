import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioimage_mcp.artifacts.models import ArtifactRef, PlotMetadata, PlotRef
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter


def test_plot_phasor_serialization():
    """
    Test that plot_phasor execution returns a JSON-serializable dict, not a Pydantic object.
    Reproduction for: base.phasorpy.plot.plot_phasor crashes due to PlotRef serialization.
    """
    adapter = PhasorPyAdapter()

    # Mock dependencies in sys.modules
    mock_phasorpy = MagicMock()
    mock_phasorpy.__version__ = "0.1.0"
    mock_plot = MagicMock()

    mock_plt = MagicMock(name="plt")
    mock_plt.gcf.return_value.get_size_inches.return_value.tolist.return_value = [8.0, 6.0]
    mock_plt.gcf.return_value.get_dpi.return_value = 100

    with patch.dict(
        sys.modules,
        {
            "phasorpy": mock_phasorpy,
            "phasorpy.plot": mock_plot,
            "matplotlib": MagicMock(),
            "matplotlib.pyplot": mock_plt,
        },
    ):
        with (
            patch("inspect.signature") as mock_sig,
            patch("matplotlib.pyplot.close"),
            patch("bioimage_mcp.artifacts.store.write_plot") as mock_write_plot,
            patch("pathlib.Path.absolute") as mock_abs,
        ):
            # Setup mocks
            mock_target_fn = MagicMock()
            mock_plot.plot_phasor = mock_target_fn

            # Mock signature to accept anything
            mock_sig.return_value = MagicMock(parameters={})

            test_path = Path("/tmp/test-plot.png")
            mock_abs.return_value = test_path

            # Create a PlotRef object like the one returned by write_plot
            plot_ref = PlotRef(
                ref_id="test-plot-1",
                type="PlotRef",
                format="PNG",
                uri="file:///tmp/test-plot.png",
                mime_type="image/png",
                size_bytes=1024,
                created_at=ArtifactRef.now(),
                metadata=PlotMetadata(
                    width_px=800, height_px=600, dpi=100, plot_type="plot_phasor"
                ),
            )
            mock_write_plot.return_value = plot_ref

            # Execute a plot function
            outputs = adapter.execute(
                fn_id="phasorpy.plot.plot_phasor", inputs=[], params={}, work_dir=Path("/tmp")
            )

            # Assertions
            assert len(outputs) == 2  # PlotRef + FigureRef (fix for gcf() context loss)

            # Check PlotRef (first output)
            plot_output = outputs[0]
            assert isinstance(plot_output, dict), f"Expected dict, got {type(plot_output)}"
            assert plot_output.get("type") == "PlotRef"
            assert "path" in plot_output
            assert plot_output["path"] == str(test_path)

            # Check FigureRef (second output)
            fig_output = outputs[1]
            assert isinstance(fig_output, dict), f"Expected dict, got {type(fig_output)}"
            assert fig_output.get("type") == "FigureRef"

            # Check JSON serializability of PlotRef (as requested)
            try:
                json_str = json.dumps(plot_output)
                assert "PlotRef" in json_str
                assert "path" in json_str
            except TypeError as e:
                pytest.fail(f"PlotRef is not JSON serializable: {e}")

            # FigureRef might have mocks in metadata if not configured perfectly,
            # but we've verified its presence and type.


def test_load_image_fallback():
    """Test that _load_image falls back to auto-detection when specified reader fails."""
    adapter = PhasorPyAdapter()

    # Path to the problematic file
    test_file = Path("datasets/FLUTE_FLIM_data_tif/Fluorescein_Embryo.tif")
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")

    # Mock artifact with OME-TIFF format
    artifact = {"uri": f"file://{test_file.absolute()}", "format": "OME-TIFF", "metadata": {}}

    # This should succeed now with the fallback
    try:
        data = adapter._load_image(artifact)
        assert data is not None
        assert data.ndim >= 2  # Native dimensions, at least 2D
    except Exception as e:
        pytest.fail(f"_load_image failed even with fallback: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
