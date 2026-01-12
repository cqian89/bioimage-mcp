# Research Findings: Matplotlib API Integration

This document outlines the research and design decisions for integrating Matplotlib into the bioimage-mcp ecosystem as a first-class tool for scientific visualization.

## 1. Headless Rendering with Agg Backend

- **Decision**: Use `matplotlib.use('Agg')` programmatically before any `pyplot` imports, enforced during adapter initialization. Prioritize the Object-Oriented (OO) interface (`matplotlib.figure.Figure` and `FigureCanvasAgg`) over the `pyplot` state-machine for internal operations.
- **Rationale**: 
    - The `pyplot` module maintains a global state and a registry of figures that causes memory leaks in long-running processes if figures are not explicitly closed via `plt.close()`.
    - The OO interface bypasses the global registry, allowing the Python garbage collector to manage figure memory naturally.
    - This approach is critical for the stability of a long-running MCP server and is safe for Python 3.13's experimental free-threaded mode.
- **Alternatives considered**:
    - **Environment Variable (`MPLBACKEND=Agg`)**: Less portable and harder to guarantee in all execution environments compared to programmatic initialization.
    - **`matplotlibrc` file**: Not portable across different tool environments and installation paths.
    - **Standard `pyplot` with explicit `plt.close()`**: Functional, but carries a high risk of memory leaks if an error occurs before the close command is reached.

## 2. FigureRef and AxesRef Implementation

- **Decision**: Implement `FigureRef` and `AxesRef` as specialized subclasses of `ObjectRef` (following the `GroupByRef` pattern) with dedicated metadata models.
- **Rationale**:
    - Provides semantic guidance to AI agents, allowing them to distinguish between figure-level methods (e.g., `savefig`, `suptitle`) and axes-level methods (e.g., `plot`, `imshow`).
    - Enables robust lifecycle management, such as automatically closing the underlying figure after a `savefig` operation materializes a `PlotRef`.
    - Pydantic validation ensures metadata consistency across the MCP boundary.
- **Alternatives considered**:
    - **Generic `ObjectRef` with `python_class` field**: Loses type safety and the ability to provide specific semantic hints to the LLM.
    - **Auto-materializing to `PlotRef` every step**: Inefficient for complex plots requiring multiple method calls and loses the ability to perform stateful updates.

## 3. Dynamic Adapter Architecture

- **Decision**: Implement an allowlist-based dynamic adapter (`MatplotlibAdapter`) that categorizes and dispatches methods.
- **Rationale**:
    - The Matplotlib API is massive (200+ functions and methods); maintaining a static manifest would be brittle and labor-intensive.
    - Method chaining is handled via `ObjectRef` and the internal `OBJECT_CACHE`.
    - A strict denylist blocks interactive/GUI methods (`show`, `ginput`, `pause`, `connect`) that would hang the server.
    - Using a `fn_id` format like `base.matplotlib.{ClassName}.{MethodName}` enables clean polymorphic dispatch.
- **Alternatives considered**:
    - **Static Manifest Entries**: Not maintainable for the scale of the Matplotlib library.
    - **Exposing all functions without filtering**: Poses a significant security and stability risk, especially regarding interactive GUI methods.

## 4. Memory Management Strategy

- **Decision**: Implement an "auto-close" mechanism triggered after `savefig` operations and registered session cleanup hooks.
- **Rationale**:
    - Figures quickly accumulate in Matplotlib's internal registry, leading to significant memory pressure.
    - Observability is maintained by monitoring `plt.get_fignums()` in diagnostic logs.
    - Auto-closing when materializing to a `PlotRef` prevents "orphan" figures from persisting after their useful life.
- **Alternatives considered**:
    - **Manual closing by the agent**: High probability of failure or omission, leading to eventual server instability.

## 5. Artifact Type Design

- **Decision**: Defined specific metadata requirements for Matplotlib-related artifacts to ensure the AI agent can "see" the state of the plot.
- **Rationale**:
    - **FigureRef Metadata**: `figsize`, `dpi`, `facecolor`, `edgecolor`, `layout`, `axes_count`.
    - **AxesRef Metadata**: `title`, `xlabel`, `ylabel`, `xlim`, `ylim`, `xscale`, `yscale`, `aspect`, `is_axis_off`, `parent_figure_ref_id`.
    - **AxesImageRef Metadata**: `cmap`, `vmin`, `vmax`, `origin`, `interpolation`, `parent_axes_ref_id`.
- **Alternatives considered**:
    - **Minimal metadata**: Forces the agent to work "blind," leading to redundant calls to set labels or limits that are already established.

## 6. PlotRef Format Extension

- **Decision**: Extend `PlotRef.format` to explicitly include `PDF` and `JPG` in addition to the existing `PNG` and `SVG` support.
- **Rationale**: Scientific publishing and presentation require a variety of output formats. PDF is standard for print-ready vector graphics, while JPG provides high compatibility for quick previews where transparency (PNG) is not required.
- **Alternatives considered**:
    - **Sticking to PNG/SVG only**: Limits the utility of the tool for researchers preparing publication-quality figures.
