import sys
from pathlib import Path

from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

# Add base tool to path for dynamic dispatch to find bioimage_mcp_base
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "base") not in sys.path:
    sys.path.append(str(REPO_ROOT / "tools" / "base"))


def test_multi_format_export(tmp_path):
    """T031: Test multi-format export (PNG, SVG, PDF, JPG)."""
    adapter = MatplotlibAdapter()

    # Save in different formats
    formats = ["png", "svg", "pdf", "jpg"]
    for fmt in formats:
        # Recreate figure for each format since savefig closes it
        results = adapter.execute(
            "base.matplotlib.pyplot.subplots", inputs=[], params={"figsize": (5, 5)}
        )
        fig_ref = next(r for r in results if r["metadata"]["output_name"] == "figure")
        ax_ref = next(r for r in results if r["metadata"]["output_name"] == "axes")

        adapter.execute(
            "base.matplotlib.Axes.hist",
            inputs=[("axes", ax_ref), ("x", [1, 2, 2, 3, 3, 3])],
            params={},
        )

        save_results = adapter.execute(
            "base.matplotlib.Figure.savefig",
            inputs=[("figure", fig_ref)],
            params={"format": fmt, "dpi": 150},
            work_dir=tmp_path,
        )

        plot_ref = save_results[0]
        assert plot_ref["type"] == "PlotRef"
        assert plot_ref["format"] == (fmt.upper() if fmt != "jpg" else "JPG")

        path = Path(plot_ref["path"])
        assert path.exists()
        assert path.suffix.lower() == (f".{fmt}" if fmt != "jpg" else ".jpeg")

        # Verify metadata
        meta = plot_ref["metadata"]
        assert meta["dpi"] == 150
        assert meta["width_px"] == 5 * 150
        assert meta["height_px"] == 5 * 150


def test_transparent_export(tmp_path):
    """T033: Test transparent parameter."""
    adapter = MatplotlibAdapter()

    results = adapter.execute(
        "base.matplotlib.pyplot.subplots", inputs=[], params={"figsize": (2, 2)}
    )
    fig_ref = results[0]

    save_results = adapter.execute(
        "base.matplotlib.Figure.savefig",
        inputs=[("figure", fig_ref)],
        params={"format": "png", "transparent": True},
        work_dir=tmp_path,
    )


def test_bbox_inches_export(tmp_path):
    """T033: Test bbox_inches='tight' parameter."""
    adapter = MatplotlibAdapter()

    results = adapter.execute(
        "base.matplotlib.pyplot.subplots", inputs=[], params={"figsize": (2, 2)}
    )
    fig_ref = results[0]

    save_results = adapter.execute(
        "base.matplotlib.Figure.savefig",
        inputs=[("figure", fig_ref)],
        params={"format": "png", "bbox_inches": "tight"},
        work_dir=tmp_path,
    )

    path = Path(save_results[0]["path"])
    assert path.exists()
