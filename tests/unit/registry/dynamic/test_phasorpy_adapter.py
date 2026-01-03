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

    with patch.dict(
        sys.modules,
        {
            "phasorpy": mock_phasorpy,
            "phasorpy.plot": mock_plot,
            "matplotlib": MagicMock(),
            "matplotlib.pyplot": MagicMock(),
        },
    ):
        with (
            patch("inspect.signature") as mock_sig,
            patch("matplotlib.pyplot.gcf") as mock_gcf,
            patch("matplotlib.pyplot.close"),
            patch("bioimage_mcp.artifacts.store.write_plot") as mock_write_plot,
            patch("pathlib.Path.absolute") as mock_abs,
        ):
            # Setup mocks
            mock_target_fn = MagicMock()
            mock_plot.plot_phasor = mock_target_fn

            # Mock signature to accept anything
            mock_sig.return_value = MagicMock(parameters={})

            mock_fig = MagicMock()
            mock_gcf.return_value = mock_fig

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
            assert len(outputs) == 1
            output = outputs[0]

            # It SHOULD be a dict, but currently it is a PlotRef (this should FAIL)
            assert isinstance(output, dict), f"Expected dict, got {type(output)}"

            # It should have a "path" key for the server to import it
            assert "path" in output
            assert output["path"] == str(test_path)

            # It should be JSON serializable
            try:
                json_str = json.dumps(output)
                assert "PlotRef" in json_str
                assert "path" in json_str
            except TypeError as e:
                pytest.fail(f"Output is not JSON serializable: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
