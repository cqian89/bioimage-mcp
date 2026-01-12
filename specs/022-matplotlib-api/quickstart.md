# Matplotlib API Quickstart

The Matplotlib API in `bioimage-mcp` provides a first-class integration for visualization, plotting, and ROI annotation within your bioimage analysis workflows. It enables headless rendering of high-quality figures directly from `BioImageRef`, `LabelImageRef`, and `TableRef` artifacts.

## Prerequisites

- **Environment**: Ensure the `bioimage-mcp-base` tool pack is installed.
- **Backend**: The system automatically enforces the headless `Agg` backend. Interactive methods like `plt.show()` or `plt.pause()` are disabled.
- **Persistence**: Figure and Axes objects are managed as `ObjectRef` artifacts (`FigureRef`, `AxesRef`), allowing you to build complex visualizations across multiple tool calls.

---

## 1. Basic Histogram Workflow
Load an image, create a histogram of pixel intensities, and save as PNG.

```python
# 1. Load image
img = run("base.io.bioimage.load", params={"path": "/data/sample.tif"})

# 2. Create figure and axes
result = run("base.matplotlib.pyplot.subplots", params={"figsize": [8, 6]})
fig_ref = result["outputs"]["figure"]
ax_ref = result["outputs"]["axes"]

# 3. Extract intensities (assuming a helper or direct table input)
# In this example, we assume we have a TableRef 'intensity_table' with an 'intensity' column
run("base.matplotlib.Axes.hist", 
    inputs={"axes": ax_ref, "data": intensity_table},
    params={"x": "intensity", "bins": 100, "color": "blue"})

# 4. Set labels and title
run("base.matplotlib.Axes.set_xlabel", inputs={"axes": ax_ref}, params={"xlabel": "Intensity"})
run("base.matplotlib.Axes.set_ylabel", inputs={"axes": ax_ref}, params={"ylabel": "Count"})
run("base.matplotlib.Axes.set_title", inputs={"axes": ax_ref}, params={"label": "Pixel Intensity Distribution"})

# 5. Save figure
plot_ref = run("base.matplotlib.Figure.savefig", 
               inputs={"figure": fig_ref}, 
               params={"path": "histogram.png", "dpi": 300})
```

---

## 2. Image with ROI Overlay Workflow
Display a microscopy image and overlay detected regions (e.g., cell centroids) using geometric patches.

```python
# 1. Load image and create subplots
img = run("base.io.bioimage.load", params={"path": "/data/cells.tif"})
res = run("base.matplotlib.pyplot.subplots")
fig, ax = res["outputs"]["figure"], res["outputs"]["axes"]

# 2. Display the image
run("base.matplotlib.Axes.imshow", inputs={"axes": ax, "image": img}, params={"cmap": "gray"})

# 3. Add ROI overlays (Circles for detected centroids)
# Patches are added via the add_patch tool with geometric parameters
run("base.matplotlib.Axes.add_patch", 
    inputs={"axes": ax}, 
    params={
        "patch_type": "Circle", 
        "xy": [150, 200], 
        "radius": 15, 
        "edgecolor": "lime", 
        "facecolor": "none", 
        "linewidth": 2
    })

# 4. Finalize and save
run("base.matplotlib.Figure.savefig", inputs={"figure": fig}, params={"path": "cell_overlay.png"})
```

---

## 3. Multi-Panel Comparison Figure
Create a side-by-side comparison of a raw image and its segmentation mask.

```python
# 1. Load artifacts
raw = run("base.io.bioimage.load", params={"path": "raw.tif"})
mask = run("base.io.bioimage.load", params={"path": "segmentation.tif"})

# 2. Create 1x2 grid layout
res = run("base.matplotlib.pyplot.subplots", params={"nrows": 1, "ncols": 2, "figsize": [12, 6]})
fig = res["outputs"]["figure"]
axs = res["outputs"]["axes"] # Array of AxesRef

# 3. Render raw image in the first panel
run("base.matplotlib.Axes.imshow", inputs={"axes": axs[0], "image": raw}, params={"cmap": "magma"})
run("base.matplotlib.Axes.set_title", inputs={"axes": axs[0]}, params={"label": "Raw Signal"})

# 4. Render mask in the second panel
run("base.matplotlib.Axes.imshow", inputs={"axes": axs[1], "image": mask}, params={"cmap": "nipy_spectral"})
run("base.matplotlib.Axes.set_title", inputs={"axes": axs[1]}, params={"label": "Segmentation Mask"})

# 5. Save comparison
run("base.matplotlib.Figure.tight_layout", inputs={"figure": fig})
run("base.matplotlib.Figure.savefig", inputs={"figure": fig}, params={"path": "comparison.png"})
```

---

## 4. Scatter Plot from Feature Table
Analyze relationships between extracted morphological features.

```python
# 1. Load measurement table
table = run("base.io.table.load", params={"path": "cell_features.csv"})

# 2. Setup plot
res = run("base.matplotlib.pyplot.subplots")
fig, ax = res["outputs"]["figure"], res["outputs"]["axes"]

# 3. Plot Area vs Circularity, colored by Mean Intensity
run("base.matplotlib.Axes.scatter", 
    inputs={"axes": ax, "data": table}, 
    params={
        "x": "area", 
        "y": "circularity", 
        "c": "intensity_mean", 
        "cmap": "viridis", 
        "alpha": 0.7,
        "edgecolors": "white"
    })

# 4. Labeling
run("base.matplotlib.Axes.set_xlabel", inputs={"axes": ax}, params={"xlabel": "Area (μm²)"})
run("base.matplotlib.Axes.set_ylabel", inputs={"axes": ax}, params={"ylabel": "Circularity Index"})
run("base.matplotlib.Figure.savefig", inputs={"figure": fig}, params={"path": "morphology_scatter.png"})
```

---

## 5. Time-Series Line Plot
Visualize intensity dynamics over time from a kinetic experiment.

```python
# 1. Load time-series data
ts_table = run("base.io.table.load", params={"path": "kinetics.csv"})

# 2. Setup plot
res = run("base.matplotlib.pyplot.subplots")
fig, ax = res["outputs"]["figure"], res["outputs"]["axes"]

# 3. Plot mean intensity trace
run("base.matplotlib.Axes.plot", 
    inputs={"axes": ax, "data": ts_table}, 
    params={
        "x": "time_sec", 
        "y": "mean_intensity", 
        "marker": "s", 
        "color": "crimson", 
        "label": "Channel 1"
    })

# 4. Add legend and grid
run("base.matplotlib.Axes.legend", inputs={"axes": ax})
run("base.matplotlib.Axes.grid", inputs={"axes": ax}, params={"visible": True, "linestyle": "--"})

# 5. Export as PDF for publication
run("base.matplotlib.Figure.savefig", inputs={"figure": fig}, params={"path": "kinetics_plot.pdf"})
```

---

## Common Patterns and Tips

- **Stateful Chaining**: Use the `figure` and `axes` outputs from `subplots` to keep track of your plot state.
- **Coordinate Systems**: The `imshow` tool uses pixel coordinates with `(0,0)` at the top-left by default.
- **Object Cleanup**: Figures are automatically closed after `savefig` to prevent memory leaks in long sessions.
- **Table Integration**: Many plotting tools (hist, scatter, plot) accept a `TableRef` in `inputs` and column names in `params`.

## Error Handling

- **Headless Constraints**: If you attempt to call `plt.show()`, the tool will return a `400 Bad Request` or an error message indicating the method is blocked.
- **Invalid Data**: Ensure column names passed to `params` exist in the provided `TableRef`.
- **Coordinate Clipping**: ROI overlays outside the image dimensions will be clipped by Matplotlib but won't crash the server.

## Reference

To see all available visualization tools, use:
```python
# List all matplotlib tools
tools = list(path="base.matplotlib")

# Get detailed schema for a specific tool
schema = describe(id="base.matplotlib.Axes.imshow")
```
