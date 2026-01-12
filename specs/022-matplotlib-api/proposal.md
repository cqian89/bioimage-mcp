# Proposal: Matplotlib API for Bioimage-MCP

**Spec ID**: 022-matplotlib-api  
**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2026-01-12  
**Target Version**: 0.4.0

---

## 1. Executive Summary

This proposal integrates the **Matplotlib API** into Bioimage-MCP as a first-class citizen for visualization, plotting, and ROI annotation. By leveraging the dynamic adapter architecture, we enable AI agents to programmatically create complex figures, multi-panel plots, and annotated overlays directly within the bioimage-mcp environment.

The integration focuses on **headless rendering** using the `Agg` backend, ensuring compatibility with server environments. We introduce specialized `FigureRef` and `AxesRef` artifact types to guide agents through the stateful Matplotlib hierarchy. This enables high-quality, reproducible scientific visualizations for bioimage analysis workflows.

---

## 2. Motivation

### 2.1 Use Cases in Bioimage Analysis

Matplotlib is essential for transforming raw pixel data and measurements into scientific insights.

| Category | Use Case | Description |
| :--- | :--- | :--- |
| **Quantification** | Histogram of Intensities | Plotting pixel value distributions for threshold selection. |
| **Morphometry** | Scatter Plots | Visualizing relationships between cell features (e.g., Area vs. Circularity). |
| **Spatial Analysis** | ROI Overlays | Drawing detected nuclei or cell boundaries on top of original microscopy images. |
| **Time-Series** | Kinetic Plots | Plotting mean intensity over time for live-cell imaging experiments. |
| **Z-Profiles** | Axial Distribution | Visualizing intensity changes across focal planes (Z-stack analysis). |
| **FLIM/Phasor** | Phasor Plots | Visualizing lifetime distributions in the phasor domain. |
| **Verification** | Segmentation Review | Displaying multi-panel "Original vs Mask" figures for manual check. |

### 2.2 Why Matplotlib (vs alternatives)

| Criterion | Matplotlib | Plotly | Seaborn |
| :--- | :--- | :--- | :--- |
| **Bioimage Ecosystem** | Native support in Scikit-Image, Cellpose, etc. | Limited | Built on Matplotlib |
| **Stateful Chaining** | Perfect for `ObjectRef` pattern | JSON-based, less object-oriented | Limited |
| **Output Formats** | Production-quality PNG, SVG, PDF | HTML-first | PNG, SVG |
| **Dependency Cost** | Moderate (already transitive in many envs) | High (JS bundle) | Low (requires Matplotlib) |
| **Headless Support** | Robust `Agg` backend | Requires `kaleido` | Robust |

---

## 3. Constitution Compliance

Bioimage-MCP's architecture constraints demand isolation and stability. Matplotlib integration respects these through:

| Principle | Status | Implementation Detail |
| :--- | :--- | :--- |
| **I. Stable MCP Surface** | ✅ Compliant | No new MCP tools; uses existing `run`, `list`, `describe`. |
| **II. Isolated Tool Execution** | ✅ Compliant | Matplotlib runs in the `bioimage-mcp-base` conda environment. |
| **III. Artifact References Only** | ✅ Compliant | Uses `FigureRef`, `AxesRef`, and `PlotRef`. No raw data transfer. |
| **IV. Reproducibility** | ✅ Compliant | Workflow logs capture every plotting step and parameter. |
| **V. Safety & Observability** | ✅ Compliant | Interactive backends blocked; non-GUI `Agg` backend enforced. |
| **VI. Test-Driven Development** | ✅ Planned | Tests for rendering, coordinate alignment, and lifecycle. |

---

## 4. Technical Design

### 4.1 Architecture Overview

The integration follows the standard adapter pattern for dynamic libraries:

1.  **MatplotlibAdapter**: Discovers and dispatches calls to the Matplotlib library.
2.  **MatplotlibAllowlists**: Curated list of safe, headless-compatible methods.
3.  **Specialized Refs**: `FigureRef` and `AxesRef` manage the in-memory object lifecycle.
4.  **PlotRef Materialization**: The `Figure.savefig()` method triggers conversion from in-memory object to a file-backed artifact.

### 4.2 FigureRef/AxesRef vs ObjectRef (Decision)

**Recommendation: Option A: Specialized FigureRef and AxesRef Types.**

**Justification:**
While `ObjectRef` is sufficient for generic objects, Matplotlib's hierarchy is unique and stateful. Specialized types provide:
1.  **Semantic Guidance**: Agents are prone to calling `plot()` on a Figure or `savefig()` on an Axes. Specialized types allow the `describe` tool to show different available methods for each.
2.  **Lifecycle Management**: Figures are global in Matplotlib. Using `FigureRef` allows the server to automatically call `plt.close(fig)` once the figure is rendered to a `PlotRef`, preventing memory bloat.
3.  **Metadata Capture**: We can store the current plot state (title, labels, limits) in the Ref metadata, allowing the agent to "see" the plot's state without expensive re-rendering.

---

## 5. Comprehensive API Coverage

We use a **category-based allowlist** with a **denylist** for interactive/dangerous methods.

### 5.1 Category Mapping

```python
# src/bioimage_mcp/registry/dynamic/matplotlib_allowlists.py

from enum import Enum
from typing import Any

class MatplotlibCategory(Enum):
    PYPLOT = "pyplot"           # Top-level factory functions
    FIGURE = "figure"           # Figure-level layout and output
    AXES_PLOT = "axes_plot"     # Core plotting (lines, scatter, bar)
    AXES_IMAGE = "axes_image"   # Imaging (imshow, contour)
    AXES_ATTR = "axes_attr"     # Titles, labels, limits, scales
    PATCHES = "patches"         # ROI shapes (Circle, Rectangle)
    ARTISTS = "artists"         # Low-level artists (Text, Legend)
    COLORS = "colors"           # Colormaps and normalization
    CM = "cm"                   # Colormaps

MATPLOTLIB_ALLOWED_CATEGORIES = {
    MatplotlibCategory.PYPLOT,
    MatplotlibCategory.FIGURE,
    MatplotlibCategory.AXES_PLOT,
    MatplotlibCategory.AXES_IMAGE,
    MatplotlibCategory.AXES_ATTR,
    MatplotlibCategory.PATCHES,
    MatplotlibCategory.ARTISTS,
    MatplotlibCategory.COLORS,
    MatplotlibCategory.CM,
}

# ============================================================================
# DENYLIST - Methods blocked to ensure headless safety and stability
# ============================================================================
MATPLOTLIB_DENYLIST = frozenset({
    # === Interactive / GUI ===
    "show", "draw", "pause", "connect", "disconnect", "waitforbuttonpress",
    "ginput", "switch_backend", "ion", "ioff", "isinteractive",
    "get_current_fig_manager", "get_fignums", "new_figure_manager",
    
    # === System / Environment ===
    "rc_context", "use", "get_backend", "set_loglevel", "rcParams", "rcParamsDefault",
    
    # === Animation (complex lifecycle) ===
    "ArtistAnimation", "FuncAnimation", "TimedAnimation", "MovieWriter",
    
    # === Widgets (Interactive UI) ===
    "Button", "Slider", "CheckButtons", "RadioButtons", "TextBox", "Cursor",
    "MultiCursor", "SpanSelector", "RectangleSelector", "LassoSelector",
    
    # === Deprecated / Internal ===
    "hold", "draw_if_interactive", "install_repl_displayhook", "uninstall_repl_displayhook",
})

# ============================================================================
# CATEGORY → METHODS MAPPING
# ============================================================================
MATPLOTLIB_CATEGORY_METHODS: dict[MatplotlibCategory, list[str]] = {
    MatplotlibCategory.PYPLOT: [
        "figure", "subplots", "subplot", "subplot2grid", "gca", "gcf", "close",
        "clf", "cla", "set_cmap", "sci", "get_cmap", "register_cmap",
        "tight_layout", "suptitle", "text", "annotate", "legend", "table",
        "margins", "autoscale", "axis", "grid", "title", "xlabel", "ylabel",
        "xlim", "ylim", "xticks", "yticks", "xscale", "yscale",
        "minorticks_on", "minorticks_off", "tick_params", "box", "box_aspect",
    ],
    MatplotlibCategory.FIGURE: [
        "add_subplot", "add_axes", "subplots", "savefig", "tight_layout",
        "suptitle", "set_size_inches", "set_dpi", "clear", "legend",
        "add_gridspec", "subfigure", "align_labels", "align_xlabels",
        "align_ylabels", "subplots_adjust", "set_facecolor", "set_edgecolor",
        "get_axes", "get_children", "set_alpha", "set_tight_layout",
        "set_constrained_layout", "set_constrained_layout_pads",
    ],
    MatplotlibCategory.AXES_PLOT: [
        "plot", "scatter", "bar", "barh", "stem", "step", "fill", "fill_between",
        "stackplot", "errorbar", "eventplot", "hist", "boxplot", "violinplot",
        "hexbin", "pie", "stairs", "quiver", "streamplot", "vlines", "hlines",
        "angle_spectrum", "magnitude_spectrum", "phase_spectrum", "psd",
        "specgram", "cohere", "csd", "xcorr", "acorr", "broken_barh",
        "vspan", "hspan", "axvline", "axhline", "axvspan", "axhspan",
    ],
    MatplotlibCategory.AXES_IMAGE: [
        "imshow", "pcolormesh", "contour", "contourf", "clabel", "colorbar",
        "spy", "matshow", "imsave", "pcolor", "pcolorfast", "tripcolor",
        "tricontour", "tricontourf", "set_navigate", "get_navigate",
    ],
    MatplotlibCategory.AXES_ATTR: [
        "set_title", "set_xlabel", "set_ylabel", "set_xlim", "set_ylim",
        "set_xscale", "set_yscale", "set_xticks", "set_yticks", "set_xticklabels",
        "set_yticklabels", "set_aspect", "grid", "set_axis_off", "set_axis_on",
        "tick_params", "axis", "invert_xaxis", "invert_yaxis", "twinx", "twiny",
        "set_box_aspect", "set_facecolor", "set_prop_cycle", "set_position",
        "get_title", "get_xlabel", "get_ylabel", "get_xlim", "get_ylim",
        "get_xscale", "get_yscale", "get_aspect", "get_legend", "get_legend_handles_labels",
    ],
    MatplotlibCategory.PATCHES: [
        "add_patch", "add_collection", "Circle", "Rectangle", "Ellipse",
        "Polygon", "RegularPolygon", "PathPatch", "FancyArrowPatch", "BoxStyle",
        "ConnectionPatch", "Arrow", "Wedge", "Shadow", "FancyBboxPatch",
        "StepPatch", "AnnotationBbox",
    ],
    MatplotlibCategory.ARTISTS: [
        "text", "annotate", "legend", "table", "add_artist", "set_visible",
        "set_alpha", "set_zorder", "set_label", "get_visible", "get_alpha",
        "get_zorder", "get_label", "remove",
    ],
    MatplotlibCategory.COLORS: [
        "get_cmap", "register_cmap", "Normalize", "LogNorm", "PowerNorm",
        "BoundaryNorm", "Colormap", "LinearSegmentedColormap", "ListedColormap",
        "to_hex", "to_rgb", "to_rgba", "CenteredNorm", "SymLogNorm", "TwoSlopeNorm",
        "LightSource", "AsinhNorm", "FuncNorm",
    ],
    MatplotlibCategory.CM: [
        "get_cmap", "register_cmap", "ScalarMappable",
    ]
}

# ============================================================================
# SPECIAL METHODS - Detailed Parameter Specifications
# ============================================================================
MATPLOTLIB_SPECIAL_METHODS: dict[str, dict[str, Any]] = {
    # --- figure(): Factory for FigureRef ---
    "figure": {
        "category": MatplotlibCategory.PYPLOT,
        "returns": "FigureRef",
        "summary": "Create a new figure",
        "params": {
            "figsize": {"type": "array", "items": {"type": "float"}, "description": "Width, height in inches"},
            "dpi": {"type": "integer", "default": 100},
            "facecolor": {"type": "string"},
            "edgecolor": {"type": "string"},
            "linewidth": {"type": "float"},
            "frameon": {"type": "boolean", "default": True},
            "layout": {"type": "string", "enum": ["constrained", "compressed", "tight", None]},
        },
        "bioimage_use": "Start a new multi-panel visualization or high-res export.",
    },

    # --- subplots(): Grid factory ---
    "subplots": {
        "category": MatplotlibCategory.PYPLOT,
        "returns": "array[FigureRef, AxesRef | array[AxesRef]]",
        "summary": "Create a figure and a set of subplots",
        "params": {
            "nrows": {"type": "integer", "default": 1},
            "ncols": {"type": "integer", "default": 1},
            "sharex": {"type": "boolean | string", "default": False},
            "sharey": {"type": "boolean | string", "default": False},
            "figsize": {"type": "array", "items": {"type": "float"}},
            "subplot_kw": {"type": "object", "description": "Dict with keywords passed to add_subplot"},
            "gridspec_kw": {"type": "object", "description": "Dict with keywords passed to GridSpec constructor"},
        },
        "bioimage_use": "Compare multiple channels or 'Raw vs Segmented' side-by-side.",
    },

    # --- imshow(): specialized for BioImageRef ---
    "imshow": {
        "category": MatplotlibCategory.AXES_IMAGE,
        "returns": "AxesImageRef",
        "summary": "Display an image on an axes",
        "bioimage_support": "Automatically handles BioImageRef by selecting slice/channel",
        "params": {
            "X": {"type": "BioImageRef | array", "required": True},
            "cmap": {"type": "string", "description": "Colormap name"},
            "norm": {"type": "ObjectRef", "description": "Normalize instance"},
            "aspect": {"type": "string | float", "default": "equal"},
            "interpolation": {"type": "string", "default": "nearest"},
            "alpha": {"type": "float", "default": 1.0},
            "vmin": {"type": "float"},
            "vmax": {"type": "float"},
            "origin": {"type": "string", "enum": ["upper", "lower"], "default": "upper"},
            "z_slice": {"type": "integer", "description": "Slice index for 3D data"},
            "channel": {"type": "integer | string", "description": "Channel index or name"},
        },
        "bioimage_use": "Display microscopy images with correct spatial aspect and LUTs.",
    },

    # --- savefig(): triggers materialization ---
    "savefig": {
        "category": MatplotlibCategory.FIGURE,
        "returns": "PlotRef",
        "summary": "Save the current figure to an artifact",
        "params": {
            "fname": {"type": "string", "description": "Filename (path is auto-managed)"},
            "dpi": {"type": "integer", "default": 100},
            "format": {"type": "string", "enum": ["png", "pdf", "svg", "jpg"]},
            "transparent": {"type": "boolean", "default": False},
            "bbox_inches": {"type": "string", "enum": ["tight", None], "default": "tight"},
            "pad_inches": {"type": "float", "default": 0.1},
        },
        "bioimage_use": "Finalize visualization and create a shareable image file.",
    },

    # --- plot(): Line plotting from TableRef ---
    "plot": {
        "category": MatplotlibCategory.AXES_PLOT,
        "summary": "Plot lines and/or markers",
        "params": {
            "data": {"type": "TableRef", "description": "Source table for named columns"},
            "x": {"type": "string | array", "description": "Column name or array for X-axis"},
            "y": {"type": "string | array", "description": "Column name or array for Y-axis"},
            "fmt": {"type": "string", "description": "Plot format string (e.g. 'ro-')"},
            "label": {"type": "string"},
            "linewidth": {"type": "float"},
            "marker": {"type": "string"},
            "color": {"type": "string"},
        },
        "bioimage_use": "Visualize feature profiles or kinetic data.",
    },

    # --- scatter(): Scatter from TableRef ---
    "scatter": {
        "category": MatplotlibCategory.AXES_PLOT,
        "summary": "Create a scatter plot",
        "params": {
            "data": {"type": "TableRef"},
            "x": {"type": "string | array"},
            "y": {"type": "string | array"},
            "s": {"type": "float | string", "description": "Size (or column name for size)"},
            "c": {"type": "string | array", "description": "Color (or column name for color)"},
            "marker": {"type": "string"},
            "cmap": {"type": "string"},
            "alpha": {"type": "float"},
        },
        "bioimage_use": "Identify correlations between cell features (e.g. Area vs Intensity).",
    },

    # --- hist(): Histogram from TableRef ---
    "hist": {
        "category": MatplotlibCategory.AXES_PLOT,
        "summary": "Compute and plot a histogram",
        "params": {
            "data": {"type": "TableRef"},
            "x": {"type": "string | array"},
            "bins": {"type": "integer | array", "default": 10},
            "range": {"type": "array", "items": {"type": "float"}},
            "density": {"type": "boolean", "default": False},
            "cumulative": {"type": "boolean", "default": False},
            "color": {"type": "string"},
            "label": {"type": "string"},
        },
        "bioimage_use": "Analyze population distribution of intensities or sizes.",
    },

    # --- boxplot(): Distribution plotting ---
    "boxplot": {
        "category": MatplotlibCategory.AXES_PLOT,
        "summary": "Draw a box and whisker plot",
        "params": {
            "data": {"type": "TableRef"},
            "column": {"type": "string | array", "description": "Column name(s) to plot"},
            "notch": {"type": "boolean", "default": False},
            "vert": {"type": "boolean", "default": True},
            "patch_artist": {"type": "boolean", "default": False},
            "showmeans": {"type": "boolean", "default": False},
        },
        "bioimage_use": "Compare feature distributions across different treatment groups.",
    },

    # --- violinplot(): Advanced distribution ---
    "violinplot": {
        "category": MatplotlibCategory.AXES_PLOT,
        "summary": "Make a violin plot",
        "params": {
            "dataset": {"type": "TableRef | array"},
            "vert": {"type": "boolean", "default": True},
            "showmeans": {"type": "boolean", "default": False},
            "showextrema": {"type": "boolean", "default": True},
            "showmedians": {"type": "boolean", "default": False},
        },
        "bioimage_use": "Visualize complex distributions of measurements.",
    },

    # --- colorbar(): LUT scaling reference ---
    "colorbar": {
        "category": MatplotlibCategory.AXES_IMAGE,
        "summary": "Add a colorbar to a plot",
        "params": {
            "mappable": {"type": "ObjectRef", "description": "The ScalarMappable (usually returned by imshow)"},
            "ax": {"type": "AxesRef", "description": "Axes to add colorbar to"},
            "label": {"type": "string"},
            "orientation": {"type": "string", "enum": ["vertical", "horizontal"]},
            "shrink": {"type": "float", "default": 1.0},
        },
        "bioimage_use": "Provide a quantitative scale for pseudocolored images.",
    },

    # --- annotate(): Labeling features ---
    "annotate": {
        "category": MatplotlibCategory.ARTISTS,
        "summary": "Annotate a point with text and an optional arrow",
        "params": {
            "text": {"type": "string", "required": True},
            "xy": {"type": "array", "items": {"type": "float"}, "required": True, "description": "Point to annotate"},
            "xytext": {"type": "array", "items": {"type": "float"}, "description": "Position of text"},
            "arrowprops": {"type": "object", "description": "Dict defining arrow appearance"},
            "fontsize": {"type": "float"},
            "color": {"type": "string"},
        },
        "bioimage_use": "Point out specific cells or interesting morphological features.",
    },

    # --- Circle(): ROI shape ---
    "Circle": {
        "category": MatplotlibCategory.PATCHES,
        "returns": "ObjectRef",
        "summary": "Create a circle patch",
        "params": {
            "xy": {"type": "array", "items": {"type": "float"}, "required": True},
            "radius": {"type": "float", "required": True},
            "color": {"type": "string"},
            "fill": {"type": "boolean", "default": True},
            "alpha": {"type": "float"},
            "edgecolor": {"type": "string"},
            "facecolor": {"type": "string"},
            "linewidth": {"type": "float"},
        },
        "bioimage_use": "Mark detected nuclei or centroids.",
    },

    # --- Rectangle(): ROI shape ---
    "Rectangle": {
        "category": MatplotlibCategory.PATCHES,
        "returns": "ObjectRef",
        "summary": "Create a rectangle patch",
        "params": {
            "xy": {"type": "array", "items": {"type": "float"}, "required": True},
            "width": {"type": "float", "required": True},
            "height": {"type": "float", "required": True},
            "angle": {"type": "float", "default": 0.0},
            "color": {"type": "string"},
            "fill": {"type": "boolean", "default": True},
        },
        "bioimage_use": "Define bounding boxes for objects.",
    }
}
```

### 5.2 Detailed Function ID Namespace

All functions are exposed under the `base.matplotlib` prefix. The `fn_id` follows the pattern `base.matplotlib.<Module/Class>.<Method>`.

```text
# Top-level factory functions
base.matplotlib.pyplot.figure
base.matplotlib.pyplot.subplots
base.matplotlib.pyplot.subplot
base.matplotlib.pyplot.subplot2grid
base.matplotlib.pyplot.gca
base.matplotlib.pyplot.gcf
base.matplotlib.pyplot.close
base.matplotlib.pyplot.clf
base.matplotlib.pyplot.cla
base.matplotlib.pyplot.set_cmap
base.matplotlib.pyplot.sci
base.matplotlib.pyplot.get_cmap
base.matplotlib.pyplot.register_cmap
base.matplotlib.pyplot.tight_layout
base.matplotlib.pyplot.suptitle

# Figure methods (called on FigureRef)
base.matplotlib.Figure.add_subplot
base.matplotlib.Figure.add_axes
base.matplotlib.Figure.subplots
base.matplotlib.Figure.savefig
base.matplotlib.Figure.tight_layout
base.matplotlib.Figure.suptitle
base.matplotlib.Figure.set_size_inches
base.matplotlib.Figure.set_dpi
base.matplotlib.Figure.clear
base.matplotlib.Figure.legend
base.matplotlib.Figure.add_gridspec
base.matplotlib.Figure.subfigure
base.matplotlib.Figure.align_labels
base.matplotlib.Figure.align_xlabels
base.matplotlib.Figure.align_ylabels
base.matplotlib.Figure.subplots_adjust

# Axes methods (called on AxesRef)
base.matplotlib.Axes.plot
base.matplotlib.Axes.scatter
base.matplotlib.Axes.bar
base.matplotlib.Axes.barh
base.matplotlib.Axes.stem
base.matplotlib.Axes.step
base.matplotlib.Axes.fill
base.matplotlib.Axes.fill_between
base.matplotlib.Axes.stackplot
base.matplotlib.Axes.errorbar
base.matplotlib.Axes.eventplot
base.matplotlib.Axes.hist
base.matplotlib.Axes.boxplot
base.matplotlib.Axes.violinplot
base.matplotlib.Axes.hexbin
base.matplotlib.Axes.pie
base.matplotlib.Axes.stairs
base.matplotlib.Axes.imshow
base.matplotlib.Axes.pcolormesh
base.matplotlib.Axes.contour
base.matplotlib.Axes.contourf
base.matplotlib.Axes.clabel
base.matplotlib.Axes.colorbar
base.matplotlib.Axes.spy
base.matplotlib.Axes.matshow
base.matplotlib.Axes.imsave
base.matplotlib.Axes.set_title
base.matplotlib.Axes.set_xlabel
base.matplotlib.Axes.set_ylabel
base.matplotlib.Axes.set_xlim
base.matplotlib.Axes.set_ylim
base.matplotlib.Axes.set_xscale
base.matplotlib.Axes.set_yscale
base.matplotlib.Axes.set_xticks
base.matplotlib.Axes.set_yticks
base.matplotlib.Axes.set_xticklabels
base.matplotlib.Axes.set_yticklabels
base.matplotlib.Axes.set_aspect
base.matplotlib.Axes.grid
base.matplotlib.Axes.set_axis_off
base.matplotlib.Axes.set_axis_on
base.matplotlib.Axes.tick_params
base.matplotlib.Axes.axis
base.matplotlib.Axes.invert_xaxis
base.matplotlib.Axes.invert_yaxis
base.matplotlib.Axes.twinx
base.matplotlib.Axes.twiny
base.matplotlib.Axes.set_box_aspect
base.matplotlib.Axes.set_facecolor
base.matplotlib.Axes.add_patch
base.matplotlib.Axes.add_collection
base.matplotlib.Axes.text
base.matplotlib.Axes.annotate
base.matplotlib.Axes.legend
base.matplotlib.Axes.table

# Patch constructors
base.matplotlib.patches.Circle
base.matplotlib.patches.Rectangle
base.matplotlib.patches.Ellipse
base.matplotlib.patches.Polygon
base.matplotlib.patches.RegularPolygon
base.matplotlib.patches.PathPatch
base.matplotlib.patches.FancyArrowPatch
base.matplotlib.patches.ConnectionPatch
base.matplotlib.patches.Arrow
base.matplotlib.patches.Wedge

# Color/Colormap utilities
base.matplotlib.colors.Normalize
base.matplotlib.colors.LogNorm
base.matplotlib.colors.PowerNorm
base.matplotlib.colors.BoundaryNorm
base.matplotlib.colors.to_hex
base.matplotlib.colors.to_rgb
base.matplotlib.colors.to_rgba
base.matplotlib.cm.get_cmap
base.matplotlib.cm.register_cmap
```

### 5.3 Justification for Excluded Functions

The following categories/functions are explicitly excluded to maintain **Headless Stability** and **Isolation**:

1.  **Interactive Functions** (`show`, `draw`, `pause`, `ion`, `ioff`, `isinteractive`, `ginput`, `waitforbuttonpress`):
    - **Reason**: These attempt to open GUI windows or block execution for user input. In a server/MCP environment, there is no display attached. Using these would cause a crash or hang.
2.  **Widgets** (`Button`, `Slider`, `TextBox`, etc.):
    - **Reason**: These are designed for interactive GUI applications and require an event loop connected to a windowing system.
3.  **Animation** (`ArtistAnimation`, `FuncAnimation`):
    - **Reason**: Complex lifecycle management and requirement for external encoders (ffmpeg) make this out of scope for the initial rendering-focused release.
4.  **Backend Management** (`use`, `switch_backend`, `get_backend`):
    - **Reason**: The adapter enforces the `Agg` backend. Allowing agents to switch it could break the headless environment or attempt to load incompatible GUI backends.
5.  **Interactive Event Handling** (`connect`, `disconnect`):
    - **Reason**: No interactive events exist in the static rendering pipeline.
6.  **Internal/Low-level State** (`get_current_fig_manager`, `new_figure_manager`):
    - **Reason**: These expose details of the backend implementation that are not relevant to programmatic visualization.

---

## 6. Example Workflows

### 6.1 Basic Line Plot Workflow
Visualize mean intensity over time from a measurement table.

```python
# 1. Load measurement table (CSV)
table = run("base.io.table.load", params={"path": "/data/timeseries.csv"})

# 2. Create Figure and Axes
# Returns: [FigureRef, AxesRef]
fig_axes = run("base.matplotlib.pyplot.subplots", params={"figsize": [8, 6]})
fig, ax = fig_axes

# 3. Plot MeanIntensity column
# Uses pandas-integration where 'data' can be a TableRef
run("base.matplotlib.Axes.plot", 
    inputs={"ax": ax, "data": table}, 
    params={"x": "Time", "y": "MeanIntensity", "marker": "o", "color": "blue"})

# 4. Set Labels and Title
run("base.matplotlib.Axes.set_xlabel", inputs={"ax": ax}, params={"xlabel": "Time (min)"})
run("base.matplotlib.Axes.set_ylabel", inputs={"ax": ax}, params={"ylabel": "Intensity (A.U.)"})
run("base.matplotlib.Axes.set_title", inputs={"ax": ax}, params={"title": "Cell Growth Kinetics"})
run("base.matplotlib.Axes.grid", inputs={"ax": ax}, params={"visible": True})

# 5. Save Figure as Artifact
# Returns: PlotRef
plot = run("base.matplotlib.Figure.savefig", inputs={"fig": fig}, params={"fname": "kinetics.png", "dpi": 300})
```

### 6.2 Image with ROI Overlay Workflow
Overlay detected nuclei (Circles) on a raw microscopy image.

```python
# 1. Load Image and Nuclei Centroids
img = run("base.io.load", params={"path": "/data/nuclei.tif"})
centroids = run("base.io.table.load", params={"path": "/data/centroids.csv"})

# 2. Create Figure/Axes
fig, ax = run("base.matplotlib.pyplot.subplots")

# 3. Show Image (handles BioImageRef)
run("base.matplotlib.Axes.imshow", inputs={"ax": ax, "X": img}, params={"cmap": "gray"})

# 4. Add ROI Circles
for _, row in centroids.to_dict('records'):
    circle = run("base.matplotlib.patches.Circle", 
                 params={"xy": [row['x'], row['y']], "radius": 5, "color": "red", "fill": False})
    run("base.matplotlib.Axes.add_patch", inputs={"ax": ax, "p": circle})

# 5. Clean up and Save
run("base.matplotlib.Axes.set_axis_off", inputs={"ax": ax})
run("base.matplotlib.Axes.set_title", inputs={"ax": ax}, params={"title": "Detected Nuclei Overlays"})
plot = run("base.matplotlib.Figure.savefig", inputs={"fig": fig}, params={"fname": "overlays.png"})
```

### 6.3 Multi-panel Segmentation Review Workflow
Side-by-side comparison of original image and segmentation result.

```python
# 1. Load Data
raw = run("base.io.load", params={"path": "/data/raw.tif"})
mask = run("base.io.load", params={"path": "/data/mask.tif"})

# 2. Create 1x2 Grid
fig, axes = run("base.matplotlib.pyplot.subplots", params={"nrows": 1, "ncols": 2, "figsize": [12, 6]})
ax1, ax2 = axes

# 3. Panel 1: Raw Image
run("base.matplotlib.Axes.imshow", inputs={"ax": ax1, "X": raw}, params={"cmap": "magma"})
run("base.matplotlib.Axes.set_title", inputs={"ax": ax1}, params={"title": "Raw Image"})

# 4. Panel 2: Segmentation
run("base.matplotlib.Axes.imshow", inputs={"ax": ax2, "X": mask}, params={"cmap": "nipy_spectral"})
run("base.matplotlib.Axes.set_title", inputs={"ax": ax2}, params={"title": "Cellpose Segmentation"})

# 5. Finalize Layout and Save
run("base.matplotlib.Figure.tight_layout", inputs={"fig": fig})
plot = run("base.matplotlib.Figure.savefig", inputs={"fig": fig}, params={"fname": "review.png"})
```

### 6.4 Histogram/Scatter Plot from TableRef Workflow
Statistical analysis of extracted cell features.

```python
# 1. Load Table
table = run("base.io.table.load", params={"path": "/data/features.csv"})

# 2. Create 2x1 Grid
fig, (ax_hist, ax_scatter) = run("base.matplotlib.pyplot.subplots", params={"nrows": 2, "ncols": 1, "figsize": [8, 10]})

# 3. Top: Histogram of Area
run("base.matplotlib.Axes.hist", 
    inputs={"ax": ax_hist, "data": table}, 
    params={"x": "Area", "bins": 50, "color": "green", "alpha": 0.6})
run("base.matplotlib.Axes.set_title", inputs={"ax": ax_hist}, params={"title": "Distribution of Cell Areas"})

# 4. Bottom: Scatter Area vs Circularity
run("base.matplotlib.Axes.scatter", 
    inputs={"ax": ax_scatter, "data": table}, 
    params={"x": "Area", "y": "Circularity", "alpha": 0.4, "c": "Intensity_Mean", "cmap": "viridis"})
run("base.matplotlib.Axes.set_title", inputs={"ax": ax_scatter}, params={"title": "Morphology vs Intensity"})

# 5. Save
run("base.matplotlib.Figure.tight_layout", inputs={"fig": fig})
plot = run("base.matplotlib.Figure.savefig", inputs={"fig": fig}, params={"fname": "analysis.svg"})
```

---

## 7. Open Questions

1.  **Should we support 3D plotting (`mplot3d`)?**
    - **Pros**: Useful for Z-stack visualization, point clouds.
    - **Cons**: High complexity in camera/projection parameters; harder for LLM to debug without visual feedback.
    - **Recommendation**: Defer to v0.5.
2.  **How to handle colorbar association with axes?**
    - Matplotlib's `fig.colorbar(im, ax=ax)` is the standard but requires tracking the `ScalarMappable` (`im`) returned by `imshow`.
    - **Proposal**: Enhance the adapter to auto-track the last image plotted on an axes and allow `Axes.colorbar()` as a convenience tool.
3.  **Animation support scope?**
    - **Decision**: Out of scope for v0.4. Requires non-trivial environment additions (FFmpeg).
4.  **Integration with specialized bioimage plotting libs?**
    - Should we eventually add `microplot` or similar?
    - **Decision**: Focus on raw Matplotlib first as it is the foundation.

---

## 8. Environment Changes

### 8.1 Update `envs/bioimage-mcp-base.yaml`

```yaml
dependencies:
  - python=3.13
  - numpy
  - scipy
  - scikit-image
  - phasorpy
  - bioio
  - pandas
  - matplotlib>=3.8  # ADD THIS LINE
```

### 8.2 Regenerate Lockfile

```bash
conda-lock -f envs/bioimage-mcp-base.yaml -p linux-64 -p osx-arm64 -p win-64
```

---

## 9. Task Breakdown & Effort Estimates

| Phase | Task | Effort | Dependencies |
| :--- | :--- | :--- | :--- |
| **Setup** | Add `matplotlib` to `bioimage-mcp-base` and update lockfile. | 1h | - |
| **Models** | Define `FigureRef`, `AxesRef`, `PlotRef`, and `PlotMetadata`. | 2h | - |
| **Allowlist** | Complete `matplotlib_allowlists.py` with full method curation (150+ functions). | 8h | - |
| **Adapter** | Implement `MatplotlibAdapter` with `Agg` backend enforcement. | 10h | 3 |
| **Dispatch** | Implement `MatplotlibDispatcher` in `bioimage-mcp-base`. | 4h | 4 |
| **Imshow** | Add specialized `imshow` support for `BioImageRef`. | 4h | 4 |
| **Patches** | Implement `add_patch` support and Patch creation. | 4h | 4 |
| **Tests** | Write and pass all Contract, Unit, and Integration tests. | 12h | - |
| **Docs** | Update `AGENTS.md` with plotting examples and ROI patterns. | 4h | 9 |

**Total Estimated Effort**: ~49 hours.

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| **Memory Exhaustion** | Medium | High | Forgetting to `plt.close()` figures. **Mitigation**: Implement auto-close after `savefig` in the adapter. |
| **Coordinate Confusion** | High | Medium | Pixels vs Points vs Inches. **Mitigation**: Enforce upper-left origin and document pixel-to-coordinate mapping. |
| **Headless failures** | Medium | Medium | Some methods might trigger GUI calls. **Mitigation**: Aggressive denylisting and `matplotlib.use('Agg')` enforcement. |
| **Performance** | Low | Low | Complex plots might be slow to render. **Mitigation**: Add timeout to tool execution. |

---

## 11. Success Criteria

1.  ✅ Successful discovery of 200+ Matplotlib functions via `list` and `describe`.
2.  ✅ Ability to create and chain `FigureRef` and `AxesRef` in multi-step workflows.
3.  ✅ Successful rendering of multi-panel figures to PNG/SVG artifacts.
4.  ✅ Accurate overlay of `Patches` (ROI) onto bioimaging data (verified by coordinate check).
5.  ✅ Zero GUI-related errors in headless Linux/Windows environments.
6.  ✅ Pass all integration tests in the CI pipeline.

---

## 12. Appendix: Function Count Summary

| Namespace | Category | Target Count | Description |
| :--- | :--- | :--- | :--- |
| `base.matplotlib.pyplot` | Factory/Global | 35 | `figure`, `subplots`, `gca`, `close`, etc. |
| `base.matplotlib.Figure` | Layout/Output | 28 | `add_subplot`, `savefig`, `tight_layout`, etc. |
| `base.matplotlib.Axes` | Plotting (Data) | 55 | `plot`, `scatter`, `hist`, `violinplot`, etc. |
| `base.matplotlib.Axes` | Imaging | 18 | `imshow`, `contour`, `colorbar`, etc. |
| `base.matplotlib.Axes` | Attributes | 40 | `set_title`, `set_xlim`, `grid`, `axis`, etc. |
| `base.matplotlib.patches` | ROI Shapes | 18 | `Circle`, `Rectangle`, `Polygon`, etc. |
| `base.matplotlib.colors/cm`| LUT/Normalization| 20 | `get_cmap`, `Normalize`, `to_hex`, etc. |
| **Total** | | **214** | |

---

## 13. References

*   [Matplotlib API Overview](https://matplotlib.org/stable/api/index.html)
*   [Matplotlib Pyplot Guide](https://matplotlib.org/stable/tutorials/introductory/pyplot.html)
*   [Matplotlib Backends (Agg)](https://matplotlib.org/stable/users/explain/backends.html)
*   [Bioimage-MCP Constitution](../.specify/memory/constitution.md)
*   [Spec 021: Pandas Integration](../021-pandas-functions/proposal.md)

(End of file)
