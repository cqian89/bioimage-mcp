import pytest
from pydantic import ValidationError

from bioimage_mcp.artifacts.models import PlotMetadata, PlotRef


def test_plot_metadata_validation():
    # Valid metadata
    meta = PlotMetadata(width_px=800, height_px=600, dpi=100, plot_type="phasor", title="Test Plot")
    assert meta.width_px == 800
    assert meta.dpi == 100

    # Missing required field
    with pytest.raises(ValidationError):
        PlotMetadata(height_px=600)


def test_plot_ref_validation():
    meta = PlotMetadata(width_px=800, height_px=600)

    ref = PlotRef(
        ref_id="test-plot-1",
        uri="file:///tmp/plot.png",
        format="PNG",
        mime_type="image/png",
        size_bytes=1024,
        created_at="2023-01-01T00:00:00Z",
        metadata=meta,
    )

    assert ref.type == "PlotRef"
    assert ref.format == "PNG"
    assert ref.metadata.width_px == 800


def test_plot_ref_serialization():
    meta = PlotMetadata(width_px=800, height_px=600)
    ref = PlotRef(
        ref_id="test-plot-1",
        uri="file:///tmp/plot.png",
        format="PNG",
        mime_type="image/png",
        size_bytes=1024,
        created_at="2023-01-01T00:00:00Z",
        metadata=meta,
    )

    data = ref.model_dump()
    assert data["type"] == "PlotRef"
    assert data["metadata"]["width_px"] == 800
