import pytest
from pydantic import ValidationError

from bioimage_mcp.artifacts.models import (
    AxesImageMetadata,
    AxesImageRef,
    AxesMetadata,
    AxesRef,
    FigureMetadata,
    FigureRef,
    PlotMetadata,
    PlotRef,
)


def test_figure_ref_instantiation():
    meta = FigureMetadata(figsize=(8.0, 6.0), dpi=100, axes_count=1)
    fig_ref = FigureRef(
        ref_id="fig1", uri="obj://session/fig1", storage_type="memory", metadata=meta
    )
    assert fig_ref.type == "FigureRef"
    assert fig_ref.metadata.figsize == (8.0, 6.0)
    assert fig_ref.python_class == "matplotlib.figure.Figure"
    assert fig_ref.storage_type == "memory"


def test_axes_ref_instantiation():
    meta = AxesMetadata(title="Test Plot", parent_figure_ref_id="fig1")
    ax_ref = AxesRef(ref_id="ax1", uri="obj://session/ax1", storage_type="memory", metadata=meta)
    assert ax_ref.type == "AxesRef"
    assert ax_ref.metadata.title == "Test Plot"
    assert ax_ref.python_class == "matplotlib.axes._axes.Axes"
    assert ax_ref.storage_type == "memory"


def test_axes_image_ref_instantiation():
    meta = AxesImageMetadata(cmap="viridis", parent_axes_ref_id="ax1")
    img_ref = AxesImageRef(
        ref_id="img1", uri="obj://session/img1", storage_type="memory", metadata=meta
    )
    assert img_ref.type == "AxesImageRef"
    assert img_ref.metadata.cmap == "viridis"
    assert img_ref.python_class == "matplotlib.image.AxesImage"
    assert img_ref.storage_type == "memory"


def test_matplotlib_ref_validation_failures():
    # Missing required field in FigureMetadata (figsize)
    with pytest.raises(ValidationError):
        FigureMetadata(dpi=100)

    # Missing parent_figure_ref_id in AxesMetadata
    with pytest.raises(ValidationError):
        AxesMetadata(title="Oops")

    # Missing parent_axes_ref_id in AxesImageMetadata
    with pytest.raises(ValidationError):
        AxesImageMetadata(cmap="magma")


def test_matplotlib_uri_validation():
    # FigureRef must have obj:// URI for memory storage
    meta = FigureMetadata(figsize=(8.0, 6.0), dpi=100)
    with pytest.raises(ValidationError):
        FigureRef(ref_id="fig1", uri="file:///path/to/fig", storage_type="memory", metadata=meta)

    # Invalid obj:// format
    with pytest.raises(ValidationError):
        FigureRef(ref_id="fig1", uri="obj://invalid", storage_type="memory", metadata=meta)


def test_plot_ref_extended_formats():
    meta = PlotMetadata(width_px=800, height_px=600)

    # PDF format
    pdf_plot = PlotRef(ref_id="p1", uri="file:///tmp/plot.pdf", format="PDF", metadata=meta)
    assert pdf_plot.format == "PDF"

    # JPG format
    jpg_plot = PlotRef(ref_id="p2", uri="file:///tmp/plot.jpg", format="JPG", metadata=meta)
    assert jpg_plot.format == "JPG"
