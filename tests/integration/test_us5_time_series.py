import sys
from pathlib import Path

import pandas as pd

from bioimage_mcp.registry.dynamic.adapters.matplotlib import MatplotlibAdapter

# Add base tool to path for dynamic dispatch to find bioimage_mcp_base
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "base") not in sys.path:
    sys.path.append(str(REPO_ROOT / "tools" / "base"))


def test_time_series_line_plot(tmp_path):
    """T027: Integration test for time-series line plot from TableRef."""
    adapter = MatplotlibAdapter()

    # 1. Create a temporary CSV with time-series data
    csv_path = tmp_path / "time_series.csv"
    data = {"time_sec": [0, 1, 2, 3, 4, 5], "mean_intensity": [10.5, 12.2, 15.1, 14.8, 18.3, 22.0]}
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    # 2. Mock TableRef
    table_ref = {
        "type": "TableRef",
        "path": str(csv_path),
        "uri": csv_path.absolute().as_uri(),
        "metadata": {"columns": list(df.columns)},
    }

    # 3. Create figure and axes
    results = adapter.execute(
        "base.matplotlib.pyplot.subplots", inputs=[], params={"figsize": (8, 4)}
    )
    fig_ref = next(r for r in results if r["type"] == "FigureRef")
    ax_ref = next(r for r in results if r["type"] == "AxesRef")

    # 4. Create line plot with markers and styling
    # US5: x=time_sec, y=mean_intensity
    adapter.execute(
        "base.matplotlib.Axes.plot",
        inputs=[("axes", ax_ref), ("data", table_ref)],
        params={
            "x": "time_sec",
            "y": "mean_intensity",
            "fmt": "-o",
            "label": "Mean Intensity Over Time",
            "linewidth": 2,
            "color": "blue",
            "marker": "s",
        },
    )

    # 5. Add labels (T029)
    adapter.execute(
        "base.matplotlib.Axes.set_xlabel",
        inputs=[("axes", ax_ref)],
        params={"xlabel": "Time (sec)"},
    )
    adapter.execute(
        "base.matplotlib.Axes.set_ylabel",
        inputs=[("axes", ax_ref)],
        params={"ylabel": "Mean Intensity (A.U.)"},
    )
    adapter.execute(
        "base.matplotlib.Axes.set_title",
        inputs=[("axes", ax_ref)],
        params={"label": "Time-Series Analysis"},
    )

    # 6. Save figure
    save_results = adapter.execute(
        "base.matplotlib.Figure.savefig",
        inputs=[("figure", fig_ref)],
        params={"format": "png"},
        work_dir=tmp_path,
    )

    plot_ref = save_results[0]
    assert plot_ref["type"] == "PlotRef"
    assert Path(plot_ref["path"]).exists()

    # Verify the plot exists and has some content (non-zero size)
    assert Path(plot_ref["path"]).stat().st_size > 0
