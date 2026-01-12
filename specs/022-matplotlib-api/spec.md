# Feature Specification: Matplotlib API for Bioimage-MCP

**Feature Branch**: `022-matplotlib-api`  
**Created**: 2026-01-12  
**Status**: Draft  
**Input**: User description: "Integrate Matplotlib API into Bioimage-MCP as a first-class citizen for visualization, plotting, and ROI annotation with headless rendering support."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Intensity Histograms (Priority: P1)

As a bioimage analyst, I want to visualize pixel intensity distributions from microscopy images so that I can determine optimal threshold values for segmentation.

**Why this priority**: Histogram analysis is the most fundamental visualization task for any bioimage workflow. It directly supports threshold selection, quality control, and population analysis.

**Independent Test**: Can be fully tested by loading a sample image, calling histogram plot function, and verifying the output artifact contains a valid PNG/SVG file with the expected intensity distribution.

**Acceptance Scenarios**:

1. **Given** a loaded BioImageRef from a microscopy image, **When** I request a histogram plot of pixel intensities, **Then** the system produces a PlotRef artifact containing a histogram image with labeled axes.
2. **Given** a histogram plot request with custom bin count, **When** I specify 100 bins, **Then** the generated histogram displays 100 bins.
3. **Given** a TableRef with extracted measurements, **When** I request a histogram of a specific column, **Then** the system plots the distribution of that column's values.

---

### User Story 2 - Overlay ROIs on Microscopy Images (Priority: P1)

As a bioimage analyst, I want to draw detected regions of interest (nuclei, cells, boundaries) as graphical overlays on top of my original microscopy images so that I can verify segmentation results visually.

**Why this priority**: Visual verification of automated segmentation is critical for quality control. Without overlay capability, users cannot confirm that detected objects match the underlying image data.

**Independent Test**: Can be tested by loading an image and a set of centroid coordinates, rendering circles at those locations, and verifying the output artifact shows the overlays at correct pixel positions.

**Acceptance Scenarios**:

1. **Given** a BioImageRef and a list of centroid coordinates, **When** I request circle overlays at those positions, **Then** the system renders circles positioned accurately on the image.
2. **Given** bounding box coordinates (x, y, width, height), **When** I request rectangle overlays, **Then** the system renders rectangles at the specified locations.
3. **Given** an overlay request, **When** I specify overlay color and transparency, **Then** the generated image respects these styling parameters.

---

### User Story 3 - Create Multi-Panel Comparison Figures (Priority: P1)

As a bioimage analyst, I want to display multiple images or plots side-by-side (e.g., "Raw vs Segmented") so that I can compare processing stages and generate publication-quality figures.

**Why this priority**: Multi-panel figures are essential for scientific communication, quality review, and comparing treatment conditions. This is a core requirement for reproducible bioimage workflows.

**Independent Test**: Can be tested by creating a 2-panel figure with a raw image on the left and a segmentation mask on the right, saving the result, and verifying both panels appear correctly.

**Acceptance Scenarios**:

1. **Given** two BioImageRefs (raw and segmented), **When** I request a 1×2 panel figure, **Then** the system produces a figure with both images displayed side-by-side.
2. **Given** a multi-panel request with specified dimensions, **When** I request a 2×3 grid, **Then** the system creates a figure with 6 panel positions.
3. **Given** panel-specific styling, **When** I set different colormaps for each panel, **Then** each panel renders with its assigned colormap.

---

### User Story 4 - Plot Feature Relationships (Priority: P2)

As a bioimage analyst, I want to create scatter plots showing relationships between extracted cell features (e.g., Area vs Circularity) so that I can identify correlations and population subgroups.

**Why this priority**: After segmentation and feature extraction, understanding feature relationships is the next analytical step. Scatter plots enable discovery of morphological patterns.

**Independent Test**: Can be tested by loading a feature table, requesting a scatter plot of two columns, and verifying the output shows correctly positioned points.

**Acceptance Scenarios**:

1. **Given** a TableRef with "Area" and "Circularity" columns, **When** I request a scatter plot, **Then** the system renders points with Area on X-axis and Circularity on Y-axis.
2. **Given** a scatter request with color mapping, **When** I specify "Intensity_Mean" for point coloring, **Then** points are colored according to their intensity values with a colorbar.
3. **Given** large datasets (10,000+ points), **When** I request a scatter plot with transparency, **Then** the system renders the plot with overlapping points visible.

---

### User Story 5 - Visualize Time-Series Data (Priority: P2)

As a live-cell imaging researcher, I want to plot mean intensity over time so that I can visualize kinetic responses and cellular dynamics.

**Why this priority**: Time-series analysis is fundamental for live-cell experiments. Line plots with proper axis labeling are required for interpreting temporal dynamics.

**Independent Test**: Can be tested by loading a time-series table with "Time" and "MeanIntensity" columns, requesting a line plot, and verifying the output shows a continuous trace.

**Acceptance Scenarios**:

1. **Given** a TableRef with time-series measurements, **When** I request a line plot of Time vs MeanIntensity, **Then** the system renders a line connecting data points.
2. **Given** a time-series plot request, **When** I specify axis labels and title, **Then** the generated plot includes the specified text labels.
3. **Given** multiple measurement series, **When** I plot them on the same axes, **Then** the system renders multiple lines with a legend.

---

### User Story 6 - Export Publication-Quality Figures (Priority: P2)

As a researcher, I want to save my visualizations as high-resolution images in multiple formats (PNG, SVG, PDF, JPG) so that I can include them in publications and presentations.

**Why this priority**: The final output format matters for reproducibility and publication. Supporting vector formats (SVG, PDF) ensures figures remain crisp at any resolution.

**Independent Test**: Can be tested by creating any figure and saving it in PNG, SVG, PDF, and JPG formats, then verifying each file is valid and opens correctly.

**Acceptance Scenarios**:

1. **Given** a completed figure, **When** I request export as PNG at 300 DPI, **Then** the system produces a high-resolution PNG artifact.
2. **Given** a completed figure, **When** I request export as SVG, **Then** the system produces a vector graphics file.
3. **Given** export parameters for transparency, **When** I request transparent background, **Then** the exported image has a transparent background (PNG/SVG).

---

### User Story 7 - Display Statistical Distributions (Priority: P3)

As a bioimage analyst, I want to create box plots and violin plots to compare feature distributions across treatment groups so that I can assess biological variability.

**Why this priority**: Statistical distribution plots are important for multi-condition experiments but are a more advanced visualization need after basic plotting is established.

**Independent Test**: Can be tested by loading a feature table grouped by treatment, requesting a boxplot, and verifying the output shows correct median, quartiles, and outliers.

**Acceptance Scenarios**:

1. **Given** a TableRef with grouped data, **When** I request a boxplot by treatment group, **Then** the system renders box-and-whisker plots for each group.
2. **Given** a violin plot request, **When** I provide measurement data, **Then** the system renders smooth distribution density curves.

---

### User Story 8 - Visualize Z-Stack Profiles (Priority: P3)

As a microscopy researcher, I want to plot intensity profiles across focal planes (Z-stack) so that I can analyze axial distribution of signals.

**Why this priority**: Z-profile analysis is common for 3D microscopy but is a specialized use case after core 2D plotting is established.

**Independent Test**: Can be tested by loading a Z-stack, computing mean intensity per Z-slice, and plotting as a line chart.

**Acceptance Scenarios**:

1. **Given** a TableRef with Z-slice indices and intensity values, **When** I request a Z-profile line plot, **Then** the system renders intensity as a function of Z-position.

---

### Edge Cases

- **Constant image histogram**: Render a single-bin histogram without error; still returns a valid PlotRef with labeled axes.
- **Empty TableRef plots**: Produce an empty plot (axes + labels) and emit a warning in run logs; do not error.
- **Out-of-bounds overlays**: Clip overlay geometry to the image bounds and emit a warning; do not crash.
- **Very large images**: Downsample for display using a configurable `max_display_size` (preserve aspect ratio) and emit a warning when downsampling occurs.
- **Orphaned figures/axes**: If no `savefig` occurs, ensure cleanup on session end to avoid memory leaks.
- **Coordinate conventions**: Interpret overlay coordinates in pixel space with upper-left origin; physical-unit coordinates require explicit conversion using BioImage metadata.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No changes to the MCP tool surface (still the constitution-defined 8 tools). Plotting is exposed as callable functions under the `base.matplotlib.*` namespace and executed via `run`.
- **Artifact I/O**: Inputs may include BioImageRef, LabelImageRef, TableRef. Outputs are PlotRef (PNG/SVG/PDF/JPG files) and intermediate ObjectRefs (FigureRef, AxesRef) for stateful chaining.
- **Isolation**: Runs in the `bioimage-mcp-base` conda environment. Matplotlib added as dependency to base environment.
- **Reproducibility**: Workflow logs capture every plotting step, parameters, and artifact references. Sessions can be replayed to regenerate identical plots.
- **Safety/observability**: Interactive backends blocked; headless `Agg` backend enforced. Interactive methods (show, draw, pause) are denied. All rendering errors logged. Orphaned figure objects cleaned up to prevent memory leaks (see FR-002, FR-008, FR-011).

### Functional Requirements

- **FR-001**: System MUST discover and expose Matplotlib functions via `list` and `describe` tools under the `base.matplotlib.*` namespace.
- **FR-002**: System MUST enforce headless rendering by using the `Agg` backend exclusively; interactive backend methods MUST be blocked.
- **FR-003**: System MUST support creation of Figure and Axes objects that persist across multiple `run` calls within a session using specialized artifact references.
- **FR-004**: System MUST support FigureRef, AxesRef, AxesImageRef, and PlotRef artifact types to manage the Matplotlib object lifecycle.
- **FR-005**: System MUST support `imshow` that accepts BioImageRef as input and automatically handles slice/channel selection.
- **FR-006**: System MUST support geometric patches (Circle, Rectangle, Ellipse, Polygon) for ROI overlay annotations.
- **FR-007**: System MUST support `savefig` to materialize in-memory figures to file-backed PlotRef artifacts in PNG, SVG, PDF, and JPG formats.
- **FR-008**: System MUST automatically close figure objects after `savefig` to prevent memory exhaustion.
- **FR-009**: System MUST support plotting from TableRef by accepting column names for x, y, color, and size parameters.
- **FR-010**: System MUST support multi-panel figures via `subplots` returning arrays of AxesRef for grid layouts.
- **FR-011**: System MUST provide curated allowlists of safe methods and denylists of blocked interactive/system methods.
- **FR-012**: System MUST support axis labeling (set_title, set_xlabel, set_ylabel), limits (set_xlim, set_ylim), and styling (grid, tick_params).
- **FR-013**: System MUST support colorbar creation to provide quantitative scale references for pseudocolored images.
- **FR-014**: System MUST support annotation and text rendering for labeling specific features in plots.
- **FR-015**: System MUST expose at least 200 curated Matplotlib functions organized by category (pyplot, Figure, Axes, patches, colors).
- **FR-016**: System MUST handle constant-valued images by generating a valid single-bin histogram without errors.
- **FR-017**: System MUST handle empty TableRefs by generating an empty (but valid) plot and emitting a warning in run logs.
- **FR-018**: System MUST clip out-of-bounds overlay geometry to image bounds and emit a warning.
- **FR-019**: System MUST support display downsampling for very large images via a configurable `max_display_size` parameter.
- **FR-020**: System MUST apply consistent coordinate conventions (pixel-space, upper-left origin) and require explicit opt-in for physical-unit conversions.
- **FR-021**: System MUST record each plotting step (fn_id + params + artifact refs + matplotlib version/backend) in the workflow run record so the session can be replayed deterministically.

### Key Entities

- **FigureRef**: Reference to an in-memory Matplotlib Figure object. Contains metadata about figure size, DPI, and current state. Enables multi-step figure construction across `run` calls.
- **AxesRef**: Reference to an in-memory Matplotlib Axes object. Contains parent FigureRef association and current plot state (title, labels, limits).
- **AxesImageRef**: Reference to an AxesImage object returned by `imshow`. Used for colorbar association and image property queries.
- **PlotRef**: File-backed artifact representing a rendered visualization (PNG, SVG, PDF, JPG). Final output from `savefig`. Immutable once created.
- **PlotMetadata**: Metadata associated with PlotRef including dimensions, format, DPI, and provenance information.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can discover 200+ visualization functions through the list/describe tools within a single session.
- **SC-002**: Users can create and render a multi-panel figure with ROI overlays in under 10 sequential tool calls.
- **SC-003**: System successfully renders figures to PNG, SVG, PDF, and JPG formats without any GUI-related errors in headless environments.
- **SC-004**: Overlays (circles, rectangles) are positioned within ±1 pixel accuracy of specified coordinates.
- **SC-005**: Sessions can be replayed to regenerate identical plot artifacts (deterministic output given same inputs).
- **SC-006**: Memory usage remains stable when creating and saving 100+ figures in a single session (no figure object leaks).
- **SC-007**: All integration tests pass in CI pipeline covering core workflows: histogram, scatter, imshow, overlay, multi-panel, export.
