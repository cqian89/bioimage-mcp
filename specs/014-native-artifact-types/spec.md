# Feature Specification: Native Artifact Types and Dimension Preservation

**Feature Branch**: `014-native-artifact-types`  
**Created**: 2026-01-04  
**Status**: Draft  
**Input**: User description: "Native Artifact Types and Dimension Preservation - Shift to native artifact model where artifacts preserve their native dimensionality, data types, and metadata"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dimension-Reducing Pipeline Execution (Priority: P1)

As a bioimage analyst, I want to run a dimension-reducing pipeline (such as squeeze → threshold → region analysis) and have each step preserve the actual dimensionality of the output, so that downstream tools receive data in the shape they expect and the pipeline completes successfully.

**Why this priority**: This is the core problem. Currently, pipelines fail because dimension-reducing operations are nullified when the system re-expands all outputs to 5D, causing downstream tools like region property analysis to fail.

**Independent Test**: Can be fully tested by executing a squeeze operation on a 5D image and verifying the output artifact reports 2D dimensions. Delivers immediate value by unblocking broken pipelines.

**Acceptance Scenarios**:

1. **Given** a 5D microscopy image (T=1, C=1, Z=1, Y=512, X=512), **When** I apply a squeeze operation, **Then** the output artifact's metadata reports shape [512, 512] and ndim=2.
2. **Given** a squeezed 2D image artifact, **When** I apply threshold followed by region property extraction, **Then** the region analysis tool receives 2D data and returns a table of measurements.
3. **Given** a max projection operation on Z-stack (T=1, C=1, Z=50, Y=512, X=512), **When** the projection completes, **Then** the output artifact reports shape [1, 1, 512, 512] (T, C, Y, X) and ndim=4.

---

### User Story 2 - Rich Artifact Metadata Inspection (Priority: P2)

As an AI agent orchestrating a workflow, I want to inspect artifact metadata (shape, dimensions, data type) without downloading the full data, so I can make intelligent decisions about which tools to apply and whether transformations are needed.

**Why this priority**: Agents need to reason about dimensionality to select appropriate tools and avoid errors. This enables smarter orchestration without transferring large datasets.

**Independent Test**: Can be tested by creating an artifact and calling the metadata inspection endpoint, verifying all dimension information is present.

**Acceptance Scenarios**:

1. **Given** an artifact created from any image operation, **When** I request the artifact reference metadata, **Then** the response includes shape, ndim, dtype, dimension labels (e.g., ["Y", "X"]), and physical pixel sizes.
2. **Given** a 3D artifact (Z, Y, X), **When** I inspect its metadata, **Then** I can determine it's 3D without loading the image data.
3. **Given** a table artifact from region property extraction, **When** I inspect its metadata, **Then** the response includes column names and column data types.

---

### User Story 3 - Flexible Export Format Selection (Priority: P3)

As an analyst, I want to export artifacts to various standard formats (OME-TIFF, PNG, TIFF, CSV) based on my downstream needs, so I can share results with collaborators using different tools.

**Why this priority**: Users need interoperability with external tools. While internal processing uses optimized interchange formats, final outputs must be in widely-supported formats.

**Independent Test**: Can be tested by exporting a 2D image artifact to PNG and a table artifact to CSV, then verifying the files are valid.

**Acceptance Scenarios**:

1. **Given** a 2D grayscale image artifact, **When** I export with format="PNG", **Then** a valid PNG file is created.
2. **Given** a 5D microscopy image artifact with full metadata, **When** I export with format="OME-TIFF", **Then** a valid OME-TIFF file is created preserving all dimensions and metadata.
3. **Given** a table artifact, **When** I export with format="CSV", **Then** a valid CSV file is created with column headers.
4. **Given** a 2D image artifact with no format specified, **When** I export, **Then** the system infers an appropriate default format (PNG for 2D uint8 images, OME-TIFF for images with rich metadata).

---

### User Story 4 - Cross-Environment Tool Chaining (Priority: P4)

As a user running tools across different environments (e.g., base image processing followed by cellpose segmentation), I want artifacts to transfer between environments without losing dimensionality or metadata, so my pipelines work seamlessly.

**Why this priority**: Multi-environment workflows are essential for combining tools from different packages. The interchange format must preserve all artifact properties.

**Independent Test**: Can be tested by creating an artifact in one environment, passing it to a tool in another environment, and verifying the receiving tool gets the correct shape and metadata.

**Acceptance Scenarios**:

1. **Given** a 3D image artifact created in the base environment, **When** passed to the cellpose environment, **Then** the cellpose tool receives data with the same shape and dimension labels.
2. **Given** an artifact with physical pixel size metadata, **When** transferred across environment boundaries, **Then** the pixel size metadata is preserved.

---

### Edge Cases

- What happens when a tool expects 5D input but receives 2D? The receiving adapter should expand dimensions only if the tool manifest explicitly requires 5D.
- How does the system handle an artifact with missing metadata (e.g., a numpy array without dimension labels)? Default dimension labels are assigned based on shape conventions (last 2 dims = Y, X).
- What happens when exporting a 5D image to PNG (which only supports 2D)? The export should fail with a clear error message explaining the dimension mismatch, or offer to export a single slice.
- How are scalar outputs (e.g., a computed threshold value) represented? As a numeric artifact with type "ScalarRef" and appropriate metadata.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: The `describe_function` and `get_artifact` responses will include additional metadata fields (shape, ndim, dtype, dims). This is additive and backward-compatible. Existing clients can ignore new fields.
- **Version bump justification**: Adding shape, ndim, dtype, dims fields to MCP responses (`describe_function`, `get_artifact`) is an additive, backward-compatible change. Per Constitution I, this qualifies as a MINOR version bump (new fields, no breaking changes). Existing clients can ignore the new fields.
- **Artifact I/O**: 
  - Internal interchange: OME-Zarr for N-D arrays (supports arbitrary dimensions), CSV for tables
  - External export: User-selectable formats including OME-TIFF, OME-Zarr, PNG, CSV, NumPy (.npy). Additional formats (JPEG, TIFF, TSV) may be added in future iterations.
  - Input: All currently supported formats via BioImage readers
- **Isolation**: Changes affect adapters in base and cellpose tool environments. No new tool-pack dependencies required; uses existing zarr, bioio packages.
  Export operations execute in the tool environment (not the server), consistent with Constitution II isolation requirements.
- **Reproducibility**: Artifact metadata (shape, dims, dtype) recorded in workflow provenance. Export format selections logged as operation parameters.
- **Safety/observability**: Invalid dimension operations (e.g., squeeze on non-singleton dim) produce clear error messages. All metadata changes logged.

### Functional Requirements

- **FR-001**: Artifact references MUST include shape, ndim, and dtype fields in their metadata.
- **FR-002**: Artifact references MUST include dimension labels (e.g., ["T", "C", "Z", "Y", "X"]) that reflect the actual dimensions present.
- **FR-003**: Dimension-reducing operations (squeeze, max_projection, slice) MUST produce artifacts with reduced dimensionality matching the operation's semantic intent.
- **FR-004**: Adapters MUST NOT automatically expand dimensions to 5D unless the output format or receiving tool explicitly requires it.
- **FR-005**: Internal cross-environment artifact interchange MUST use OME-Zarr format for N-D array data, preserving arbitrary dimensionality.
- **FR-006**: Table artifacts MUST be stored with column name and column type metadata in the artifact reference.
- **FR-007**: The export function MUST accept a format parameter allowing users to choose from supported export formats.
- **FR-008**: When no export format is specified, the system MUST infer a sensible default based on data type and dimensionality.

#### Export Format Inference Rules (FR-008 detail)

When no export format is specified, the system infers the format using these deterministic rules (evaluated in order):

| Condition | Inferred Format | Rationale |
|-----------|-----------------|-----------|
| `artifact_type == "TableRef"` | CSV | Tabular data standard |
| `size_bytes > 4GB` | OME-Zarr | Chunked format for large files |
| `ndim == 2` AND `dtype in (uint8, uint16)` AND no `physical_pixel_sizes` | PNG | Simple 2D grayscale |
| `ndim >= 3` OR has `physical_pixel_sizes` OR has `channel_names` | OME-TIFF | Preserves microscopy metadata |
| Default | OME-TIFF | Safe default with metadata preservation |

- **FR-009**: Physical pixel size metadata MUST be preserved through all operations that don't change spatial resolution.
- **FR-010**: Tool manifests MUST support `dimension_requirements` fields indicating expected input dimensionality (e.g., `min_ndim: 2`, `max_ndim: 5`, `expected_axes: ["Y", "X"]`).

### Key Entities

- **ArtifactRef**: Reference to stored data including URI, type, and rich metadata. Extended with shape, ndim, dtype, dims, and physical_pixel_sizes fields.
- **BioImageRef**: Artifact reference type for image data of any dimensionality (replaces assumption of 5D-only).
- **TableRef**: Artifact reference type for tabular data with column metadata.
- **ScalarRef**: Artifact reference type for single numeric values (e.g., computed thresholds).
- **Dimension Requirements**: Manifest property indicating tool's expected input/output dimensionality constraints.

## Assumptions

- Existing tools that genuinely require 5D input will have their manifests updated with explicit dimension_requirements, allowing adapters to expand dimensions only when necessary.
- The OME-Zarr format supports all dimensionalities needed (1D through 5D+).
- Column type metadata for tables follows standard type names (int64, float64, string, bool).
- Physical pixel sizes are represented as a list in spatial axis order (Z, Y, X when present).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pipeline of squeeze → threshold → region_property_extraction executes successfully without manual dimension manipulation or adapter intervention, with 100% of test cases passing.
- **SC-002**: All artifact references for dimension-reduced outputs correctly report the actual ndim (verified by unit tests for squeeze, max_projection, and slice operations).
- **SC-003**: Table outputs from region property extraction are stored with column metadata accessible via artifact inspection (column names and types visible in artifact reference).
- **SC-004**: Agents can determine artifact dimensionality from metadata alone in under 100ms without downloading image data.
- **SC-005**: Export to at least 5 formats (OME-TIFF, OME-Zarr, PNG, CSV, NumPy) produces valid files as verified by external validation tools.
- **SC-006**: Cross-environment artifact transfers preserve shape, dims, and metadata with zero data loss (verified by round-trip tests).
