# Feature Specification: Comprehensive Phasorpy Adapter

**Feature Branch**: `013-phasorpy-adaptor`  
**Created**: 2026-01-02  
**Status**: Draft  
**Input**: User description: "Expose full Phasorpy v0.9+ API through dynamic discovery"

## User Scenarios & Testing

### User Story 1 - Calibrated FLIM Analysis (Priority: P1)
**Story**: As a FLIM researcher, I want to load a Becker & Hickl (.sdt) file, calculate phasors from the raw decay signal, and calibrate them using a known Fluorescein standard so that I can obtain absolute lifetime measurements.
**Why this priority**: This is the fundamental workflow for any quantitative fluorescence lifetime analysis. Without calibration, the phasor coordinates are instrument-dependent and cannot be compared across sessions.
**Independent Test**: Provide an SDT file and a reference lifetime value. The system must return a calibrated Phasor artifact (G and S components) where the known standard aligns with the expected universal circle position.
**Acceptance Scenarios**:
- Successfully read .sdt files from the filesystem.
- Transform time-domain signals into (G, S) phasor coordinates.
- Apply `phasorpy.lifetime.phasor_calibrate` using a reference lifetime.
- Verify that the resulting artifact contains valid numerical data in the expected range [0, 1].

### User Story 2 - Visualizing Metabolic State (Priority: P2)
**Story**: As a biologist studying embryo development, I want to generate a phasor plot and a lifetime map from my FLIM data to visually identify regions with high oxidative stress.
**Why this priority**: Visual inspection is critical for interpreting spatial distribution of lifetimes in complex biological samples.
**Independent Test**: Run a plotting tool on a pre-calculated Phasor artifact and verify that a PNG image artifact is generated and accessible.
**Acceptance Scenarios**:
- Capture Matplotlib output from `plot_phasor` as a PNG artifact.
- Map phasor coordinates back to image space to create a "pseudo-colored" lifetime map.
- The resulting plot must correctly display the universal circle and the distribution of the sample's phasors.

### User Story 3 - Multi-Format Data Normalization (Priority: P3)
**Story**: As a data scientist in a core facility, I want to process datasets from multiple vendors (PicoQuant .ptu, Leica .lif) into a standardized signal format so that I can use a single analysis pipeline regardless of the microscope used.
**Why this priority**: Ensures interoperability and reduces the need for vendor-specific software for the bulk of the analysis.
**Independent Test**: Load a PTU file and a LIF file, and verify that both result in a standardized `BioImageRef` containing the time-resolved signal. Vendor-specific files (SDT, PTU, LIF) are represented as `FileRef` artifacts before being read into `BioImageRef`.
**Acceptance Scenarios**:
- Support for reading SDT, PTU, and LIF via bioio plugins (bioio-bioformats for SDT/PTU, bioio-lif for LIF).
- Acquisition parameters (harmonics, frequency) are extracted and preserved within a `PhasorMetadata` entity.
- Large vendor files are handled without crashing the core server (process isolation).

### Edge Cases
- **Missing Metadata**: Handling vendor files where the laser repetition rate or frequency is not explicitly defined in the header.
- **Low Photon Counts**: Behavior of phasor transformations when pixels have near-zero signal (noise sensitivity).
- **Multi-harmonic Analysis**: Requesting harmonics beyond the fundamental frequency and ensuring the adapter handles the increased dimensionality.
- **Non-Square Images**: Ensuring the coordinate transformations and plotting functions correctly handle non-uniform pixel dimensions.

## Requirements

### Constitution Constraints
- **MCP API impact**: 
    - Function discovery must be dynamic to avoid hardcoding the 75+ Phasorpy functions.
    - Discovery responses must use the `list_tools` / `describe_function` pattern to prevent context bloat.
- **Artifact I/O**:
    - Raw signals, G/S components, and lifetime maps must be handled as `BioImageRef` (OME-TIFF).
    - Plots are returned as a new `PlotRef` artifact type (PNG format) with explicit semantics for visualization outputs.
    - Calibration parameters and scalars should use `TableRef` or simple parameter schemas.
    - All file I/O for vendor formats (SDT, PTU, LIF, CZI, etc.) is performed via bioio and its plugins, ensuring consistent 5D TCZYX data access. The `phasorpy.io` module is explicitly excluded from the adapter.
- **Isolation**:
    - Phasorpy and its heavy dependencies (matplotlib, vendor I/O libraries) must run in the tool-specific environment (`bioimage-mcp-base` or equivalent), not the core server.
- **Reproducibility**:
    - Every Phasorpy function call must record its parameters, input artifact hashes, and the specific version of Phasorpy used.
- **Safety/observability**:
    - Errors from the underlying C-extensions in Phasorpy must be captured and logged as `LogRef`.
    - Filesystem access for vendor readers must respect the `allowed_read` allowlist.

### Functional Requirements
- **FR-001**: Dynamic mapping of `phasorpy` modules (`phasor`, `lifetime`, `plot`, `filter`, `cursor`, `component`) to MCP tools. Scope is the v0.9+ public API. Note: `phasorpy.io` is explicitly excluded; all file I/O is handled via bioio plugins to ensure 5D TCZYX normalization.
- **FR-002**: Support for multi-output functions (e.g., functions returning `(mean_lifetime, amplitude)` tuples) by mapping them to multiple artifact outputs.
- **FR-003**: Vendor format support via bioio plugins: bioio-bioformats for SDT/PTU (via Bio-Formats Java), bioio-lif for Leica LIF files.
- **FR-004**: Automated capture of Matplotlib figures generated by Phasorpy plotting functions.
- **FR-005**: Support for "Phasor Transform" operations that convert 5D TCZYX signal images into (G, S) coordinate images.
- **FR-006 (Documentation)**: Update the FLIM phasor tutorial and quickstart guide to reflect the new dynamic adapter capabilities and vendor format support (Task T029/T036 mapping).

### Non-Functional Requirements

- **NFR-001 (Performance)**: End-to-end execution of a "Load -> Transform -> Calibrate -> Plot" workflow MUST complete in under 30 seconds for a standard 512x512 FLIM image on baseline hardware.
- **NFR-002 (Safety)**: Filesystem access MUST be restricted to the `allowed_read` and `allowed_write` allowlists.
- **NFR-003 (Observability)**: Tool execution logs (stdout/stderr) and errors from underlying C-extensions MUST be captured and persisted as `LogRef` artifacts.
- **NFR-004 (Reproducibility)**: Every tool execution MUST record full provenance: input hashes, parameter values, environment lockfile hash, and tool version.
- **NFR-005 (Isolation)**: Tool execution MUST occur in a separate subprocess. Tool crashes or segmentation faults MUST NOT crash the core MCP server.

### Key Entities
- **Signal**: A 5D or 6D array (adding a lifetime/time-gate dimension) representing the fluorescence decay at each pixel.
- **Phasor (G, S)**: The transformation of the signal into the frequency domain, where 'G' is the real component (cosine transform) and 'S' is the imaginary component (sine transform).
- **PhasorMetadata**: A structured entity containing acquisition parameters necessary for analysis, such as laser repetition frequency (`frequency`), harmonic number, and calibration offsets. Required for consistent lifetime estimation across datasets.
- **Universal Circle**: The theoretical locus of all single-exponential lifetimes in the phasor plot, used as a reference for calibration and analysis.
- **Lifetime Map**: A spatial image where pixel values represent estimated fluorescence lifetimes calculated from phasor coordinates.

## Success Criteria

### Measurable Outcomes
- **SC-001**: Successful discovery and registration of at least 50 Phasorpy functions (MVP threshold), with an optional target of 75+ functions in the MCP tool registry.
- **SC-002**: End-to-end execution of a "Load -> Transform -> Calibrate -> Plot" workflow in under 30 seconds for a standard 512x512 FLIM image.
- **SC-003**: Zero core server crashes when loading malformed or unsupported vendor files (proper subprocess isolation).
- **SC-004**: 100% of plotted artifacts are accessible via the `get_artifact` tool and contain valid PNG data.

## Assumptions
- Phasorpy v0.9+ is available in the target conda environment.
- The environment has sufficient memory to hold raw 5D FLIM signals (typically 100MB - 1GB per image).
- Users have basic knowledge of FLIM terminology (harmonics, calibration references).
- `bioio-bioformats` plugin is installed and functional (provides SDT, PTU support via Bio-Formats Java).
- `bioio-lif` plugin is installed for Leica LIF file support.

## Test Datasets

The following open-licensed datasets are available for testing FLIM workflow functionality:

### Becker & Hickl SDT Dataset
- **Path**: `datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt`
- **Format**: Becker & Hickl SDT (TCSPC)
- **Size**: ~9.4 MB
- **License**: BSD 3-Clause
- **Source**: [napari-flim-phasor-plotter](https://github.com/zoccoler/napari-flim-phasor-plotter)
- **Use Case**: Testing SDT file loading via bioio-bioformats plugin (US1, US3)

### PicoQuant PTU Dataset
- **Path**: `datasets/ptu_hazelnut_flim/hazelnut_FLIM_single_image.ptu`
- **Format**: PicoQuant PTU (TTTR)
- **Size**: ~23.1 MB
- **License**: BSD 3-Clause
- **Source**: [napari-flim-phasor-plotter](https://github.com/zoccoler/napari-flim-phasor-plotter)
- **Use Case**: Testing PTU file loading via bioio-bioformats plugin (US3)

### Leica LIF Dataset
- **Path**: `datasets/lif_flim_testdata/FLIM_testdata.lif`
- **Format**: Leica Image Format (LIF)
- **Size**: ~34.7 MB
- **License**: CC-BY 4.0
- **Source**: [PhasorPy Data](https://github.com/phasorpy/phasorpy-data) / [Figshare DOI](https://doi.org/10.6084/m9.figshare.22336594.v1)
- **Use Case**: Testing LIF file loading via bioio-lif plugin (US3)

### Existing FLIM Datasets
- **Path**: `datasets/FLUTE_FLIM_data_tif/Embryo.tif` (and other TIF files)
- **Format**: TIFF
- **Use Case**: Testing phasor transformations and calibration (US1, US2)
