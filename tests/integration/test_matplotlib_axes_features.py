from pathlib import Path

import numpy as np
import pytest

from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter


@pytest.fixture
def adapter():
    return MatplotlibAdapter()


@pytest.fixture
def sample_image_ref(tmp_path):
    import tifffile

    path = tmp_path / "sample.tif"
    data = np.random.rand(1, 1, 1, 100, 100).astype(np.float32)
    tifffile.imwrite(str(path), data)
    return {"type": "BioImageRef", "path": str(path), "uri": path.as_uri()}


def test_axes_styling_workflow(adapter, tmp_path):
    """T043: Integration test for axes styling and colorbar."""
    # 1. Create subplots
    results = adapter.execute(
        "base.matplotlib.pyplot.subplots", inputs=[], params={"nrows": 1, "ncols": 1}
    )
    fig_ref = next(r for r in results if r["type"] == "FigureRef")
    ax_ref = next(r for r in results if r["type"] == "AxesRef")

    # 2. Set labels and title
    adapter.execute(
        "base.matplotlib.Axes.set_title", inputs=[("axes", ax_ref)], params={"label": "Test Title"}
    )
    adapter.execute(
        "base.matplotlib.Axes.set_xlabel", inputs=[("axes", ax_ref)], params={"xlabel": "X Label"}
    )
    adapter.execute(
        "base.matplotlib.Axes.set_ylabel", inputs=[("axes", ax_ref)], params={"ylabel": "Y Label"}
    )

    # 3. Grid and limits
    adapter.execute(
        "base.matplotlib.Axes.grid", inputs=[("axes", ax_ref)], params={"visible": True}
    )
    adapter.execute(
        "base.matplotlib.Axes.set_xlim", inputs=[("axes", ax_ref)], params={"left": 0, "right": 10}
    )

    # 4. Colorbar (this might fail until implemented)
    # We need something to show first to have a mappable
    data = np.random.rand(10, 10)
    adapter.execute("base.matplotlib.Axes.imshow", inputs=[("axes", ax_ref)], params={"X": data})

    # Now add colorbar
    adapter.execute("base.matplotlib.Axes.colorbar", inputs=[("axes", ax_ref)], params={})

    # 5. Save and verify
    save_results = adapter.execute(
        "base.matplotlib.Figure.savefig",
        inputs=[("figure", fig_ref)],
        params={"format": "png"},
        work_dir=tmp_path,
    )
    assert len(save_results) == 1
    assert save_results[0]["type"] == "PlotRef"
    assert Path(save_results[0]["path"]).exists()


def test_annotation_and_legend(adapter, tmp_path):
    """T043: Integration test for annotations and legend."""
    results = adapter.execute("base.matplotlib.pyplot.subplots", inputs=[], params={})
    fig_ref = next(r for r in results if r["type"] == "FigureRef")
    ax_ref = next(r for r in results if r["type"] == "AxesRef")

    # Plot something with a label
    adapter.execute(
        "base.matplotlib.Axes.plot",
        inputs=[("axes", ax_ref)],
        params={"x": [1, 2, 3], "y": [1, 4, 9], "label": "Squared"},
    )

    # Legend
    adapter.execute("base.matplotlib.Axes.legend", inputs=[("axes", ax_ref)], params={})

    # Annotation
    adapter.execute(
        "base.matplotlib.Axes.annotate",
        inputs=[("axes", ax_ref)],
        params={"text": "Peak", "xy": [2, 4], "xytext": [3, 5]},
    )

    # Text
    adapter.execute(
        "base.matplotlib.Axes.text",
        inputs=[("axes", ax_ref)],
        params={"x": 1, "y": 8, "s": "Hello"},
    )

    # Save
    save_results = adapter.execute(
        "base.matplotlib.Figure.savefig",
        inputs=[("figure", fig_ref)],
        params={"format": "png"},
        work_dir=tmp_path,
    )
    assert Path(save_results[0]["path"]).exists()
