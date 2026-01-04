# Feature Specification: Bioimage I/O Functions

**Feature Branch**: `015-bioio-functions`  
**Created**: 2026-01-04  
**Status**: Draft  
**Input**: User description: "Provide 6 curated bioimage I/O functions (load, inspect, slice, validate, get_supported_formats, export) under `base.io.bioimage.*` namespace for AI agents to perform common image I/O tasks"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load and Inspect Image Metadata (Priority: P1)

An AI agent needs to load a microscopy image and understand its structure before deciding how to process it. The agent loads a CZI file from the user's filesystem, inspects the metadata to learn the dimensions (T, C, Z, Y, X), channel names, and pixel sizes, then uses this information to decide on the appropriate analysis strategy.

**Why this priority**: This is the foundational workflow. Without loading and understanding image structure, no other processing is possible. Every image analysis session starts here.

**Independent Test**: Can be fully tested by loading any supported image file and verifying returned metadata matches expected values. Delivers immediate value by providing image structure information to the agent.

**Acceptance Scenarios**:

1. **Given** an image file exists at an allowed path, **When** the agent calls `base.io.bioimage.load` with that path, **Then** the system returns a `BioImageRef` artifact with basic metadata (shape, dtype, ndim).
2. **Given** a `BioImageRef` or file path, **When** the agent calls `base.io.bioimage.inspect`, **Then** the system returns detailed metadata (dimensions, pixel sizes, channel names) without loading full pixel data.
3. **Given** a path outside allowed read directories, **When** the agent calls `base.io.bioimage.load`, **Then** the system returns an error indicating path access is not permitted.

---

### User Story 2 - Validate and Check Format Support (Priority: P2)

Before starting a long analysis pipeline, an AI agent needs to verify that the input files are readable and in a supported format. The agent checks which formats are supported in the current environment, validates the input file is uncorrupted, and reports any potential issues before committing to processing.

**Why this priority**: Pre-flight validation prevents wasted time on failed pipelines. Essential for reliable workflows but secondary to basic load/inspect capability.

**Independent Test**: Can be tested by calling `get_supported_formats` and verifying known formats are listed, and by calling `validate` on both valid and corrupted files.

**Acceptance Scenarios**:

1. **Given** the base tool environment is available, **When** the agent calls `base.io.bioimage.get_supported_formats`, **Then** the system returns a list of supported format strings (e.g., "OME-TIFF", "CZI", "LIF").
2. **Given** a valid image file, **When** the agent calls `base.io.bioimage.validate`, **Then** the system returns a report indicating the file is readable and which reader was selected.
3. **Given** a corrupted or invalid image file, **When** the agent calls `base.io.bioimage.validate`, **Then** the system returns a report detailing the specific issues found.

---

### User Story 3 - Slice Multi-dimensional Images (Priority: P2)

An AI agent is working with a large 5D image (TCZYX) and needs to extract specific subsets for processing. The agent selects a specific channel, timepoint, or Z-range and creates a new artifact containing only that subset, preserving physical metadata.

**Why this priority**: Multi-dimensional data handling is critical for microscopy workflows. Slicing enables memory-efficient processing and targeted analysis of specific image regions.

**Independent Test**: Can be tested by loading a 5D image, slicing specific dimensions, and verifying the output has expected reduced dimensions and preserved metadata.

**Acceptance Scenarios**:

1. **Given** a `BioImageRef` with multiple channels, **When** the agent calls `base.io.bioimage.slice` with `{"C": 0}`, **Then** the system returns a new `BioImageRef` with only the first channel.
2. **Given** a `BioImageRef` with multiple timepoints, **When** the agent calls `base.io.bioimage.slice` with `{"T": {"start": 0, "stop": 5}}`, **Then** the system returns a new `BioImageRef` containing timepoints 0-4.
3. **Given** a sliced image, **When** the agent inspects its metadata, **Then** the physical pixel sizes (microns) from the original are preserved.

---

### User Story 4 - Export Results to Standard Formats (Priority: P1)

After processing an image, an AI agent needs to export results in a format the user can view or share. The agent exports processed images to OME-TIFF for compatibility with standard viewers, PNG for quick sharing, or OME-Zarr for efficient cloud storage.

**Why this priority**: Export is essential for delivering results to users. Without export, no analysis outputs can be shared or persisted in standard formats.

**Independent Test**: Can be tested by loading an image, exporting to each supported format, and verifying the output files are valid and readable.

**Acceptance Scenarios**:

1. **Given** a `BioImageRef` artifact, **When** the agent calls `base.io.bioimage.export` with format "OME-TIFF", **Then** the system creates a valid OME-TIFF file and returns a new `BioImageRef` pointing to it.
2. **Given** a `TableRef` artifact, **When** the agent calls `base.io.bioimage.export` with format "CSV", **Then** the system creates a valid CSV file and returns a `TableRef` pointing to it.
3. **Given** a `BioImageRef` and no format specified, **When** the agent calls `base.io.bioimage.export`, **Then** the system infers an appropriate format based on the data type.

---

### Edge Cases

- What happens when a file has no readable metadata? The system should return minimal metadata (shape, dtype) and flag missing fields in the inspect response.
- How does the system handle multi-scene files (e.g., plate acquisitions)? The load function returns the first scene by default; scene selection may be added in future iterations.
- What happens when slice indices are out of bounds? The system should return an error with the valid range for that dimension.
- How does export handle images larger than available memory? The export function should use lazy/chunked writing for OME-Zarr format.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No changes to existing MCP endpoints. Adds 6 new functions to base toolkit. Removes deprecated `base.bioio.export` function entirely (breaking change acceptable at this project stage).
- **Artifact I/O**: 
  - Inputs: File paths (strings), `BioImageRef`, `TableRef`
  - Outputs: `BioImageRef`, `TableRef`, JSON metadata
  - Formats: OME-TIFF (primary), OME-Zarr (for large data), PNG (for visualization), CSV (for tables)
- **Isolation**: All functions run in the `bioimage-mcp-base` environment. No new environment requirements.
- **Reproducibility**: Function calls record: input path/artifact reference, parameters (format, slices), output artifact reference. Standard workflow replay applies.
- **Safety/observability**: 
  - Path validation against `filesystem.allowed_read` and `filesystem.allowed_write` config
  - Structured error responses for invalid paths, unsupported formats, corrupt files
  - All operations logged with artifact provenance

### Functional Requirements

- **FR-001**: System MUST provide a `base.io.bioimage.load` function that loads an image file into the artifact system as a `BioImageRef`.
- **FR-002**: System MUST validate file paths against the configured `filesystem.allowed_read` allowlist before loading.
- **FR-003**: System MUST provide a `base.io.bioimage.inspect` function that returns image metadata without loading full pixel data.
- **FR-004**: The inspect function MUST return at minimum: dimensions (shape), data type, dimension labels (e.g., TCZYX), and physical pixel sizes when available.
- **FR-005**: System MUST provide a `base.io.bioimage.slice` function that extracts a subset of a multi-dimensional image.
- **FR-006**: The slice function MUST accept dimension labels (T, C, Z, Y, X) mapped to either single indices or range objects (start, stop, step).
- **FR-007**: The slice function MUST preserve physical metadata (pixel sizes) in the output artifact.
- **FR-008**: System MUST provide a `base.io.bioimage.get_supported_formats` function that lists available image format readers.
- **FR-009**: System MUST provide a `base.io.bioimage.validate` function that checks file readability and reports issues.
- **FR-010**: The validate function MUST report: whether the file is readable, which reader was selected, and any metadata issues (e.g., missing dimensions).
- **FR-011**: System MUST provide a `base.io.bioimage.export` function that writes artifacts to standard formats.
- **FR-012**: The export function MUST support at minimum: OME-TIFF, OME-Zarr, PNG for images and CSV for tables.
- **FR-013**: System MUST remove the deprecated `base.bioio.export` function from the manifest.
- **FR-014**: All 6 functions MUST be discoverable via `list_tools` and `describe_function` MCP endpoints.
- **FR-015**: All functions MUST use `bioio.BioImage` internally to ensure consistent dimension handling.

### Key Entities

- **BioImageRef**: Reference to a microscopy image artifact with metadata (shape, dtype, ndim, physical_pixel_sizes). Represents image data stored in the artifact system.
- **TableRef**: Reference to a tabular data artifact (e.g., measurements, feature tables). Exportable to CSV format.
- **ImageMetadata**: Structured response from inspect/validate containing dimension info, pixel sizes, channel names, and validation status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 6 functions (load, inspect, slice, get_supported_formats, validate, export) are discoverable via `list_tools` and `describe_function` MCP calls.
- **SC-002**: An agent can successfully complete the workflow: load a CZI file → inspect dimensions → slice one Z-plane → export as PNG — with all steps returning valid artifacts.
- **SC-003**: The deprecated `base.bioio.export` function is completely removed from the codebase and manifest.
- **SC-004**: The `inspect` function returns metadata in under 2 seconds for files up to 10GB without loading pixel data into memory.
- **SC-005**: All function schemas include complete parameter documentation sufficient for an AI agent to use without additional context.
- **SC-006**: All contract tests pass validating the function schemas match declared signatures.
- **SC-007**: Integration tests cover the primary load→slice→export workflow with at least 3 different input formats (OME-TIFF, CZI, LIF).

## Assumptions

- The project is at an early stage where breaking changes (removing `base.bioio.export`) are acceptable.
- Multi-scene file support (plate acquisitions) is deferred to a future iteration; loading returns the first scene.
- The `bioimage-mcp-base` environment already includes all required dependencies (bioio, bioio-ome-tiff, bioio-ome-zarr).
- Physical metadata (pixel sizes) may not be available in all files; the system gracefully handles missing metadata.
- The existing artifact storage infrastructure supports the new artifact types without modification.
