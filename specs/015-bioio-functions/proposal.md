# Proposal: Spec 015: Bioimage I/O Functions (6 Curated Tools)

**Branch**: `015-bioio-functions` | **Date**: 2026-01-04 | **Spec**: `specs/015-bioio-functions/proposal.md`

## 1. Overview

### Problem Statement
Currently, the `bioimage-mcp` project primarily relies on `base.bioio.export` for image output, and image loading is often implicit or handled via low-level adapter logic. There is no standard, curated set of tools for agents to explicitly perform common bioimage I/O tasks like inspecting metadata without loading full data, slicing large multi-dimensional images, or validating file readability.

### Goal
Provide a comprehensive, high-level set of 6 image I/O functions that are easy for AI agents to discover and use. These functions will abstract the complexity of `bioio` and other underlying libraries into a consistent interface.

### Naming Convention Rationale
The proposed naming convention is `base.io.bioimage.*`. 
- `base`: Indicates these are part of the base toolkit.
- `io`: Clearly categorizes these as I/O operations.
- `bioimage`: Specifies that these are curated for bioimaging data, distinguishing them from generic file I/O or raw `bioio` API wrappers.

This naming makes it clear to both developers and AI agents that these are intentional, high-level functions rather than direct exposures of a library's internal API.

## 2. Naming Convention Standardization

### Current Pattern
The existing pattern for many tools in the base toolkit follows `{env}.{package}.{module}.{function}` (e.g., `base.skimage.filters.gaussian`). This works well for dynamic discovery of third-party libraries.

### Proposed Pattern for Curated I/O
For curated, project-specific I/O operations, we will use `base.io.bioimage.*`. This provides a stable, predictable namespace for critical operations.

### Replacement Strategy
The existing `base.bioio.export` function will be **replaced** (not deprecated) by `base.io.bioimage.export`. At this early stage of the project, backward compatibility is not a concern. The old function ID will be removed from the manifest entirely.

## 3. Function Specifications

### 3.1 base.io.bioimage.load
**Description**: Load an image file from the local filesystem into the artifact system as a `BioImageRef`.

**Use Cases**:
- Importing a user-provided image file for analysis.
- Explicitly loading an image before applying a series of filters.

**Inputs**:
- `path` (string, required): Absolute path to the image file.
- `format` (string, optional): Format hint (e.g., "CZI", "LIF", "OME-TIFF").

**Outputs**:
- `image`: `BioImageRef`

**params_schema**:
```yaml
type: object
required: [path]
properties:
  path:
    type: string
    description: Absolute path to the local image file.
  format:
    type: string
    description: Optional format hint to help the reader.
```

**Implementation Notes**:
- Uses `bioio.BioImage` for reading.
- Validates path against `filesystem.allowed_read` config.
- Automatically creates a `BioImageRef` with basic metadata (ndim, shape, dtype).

---

### 3.2 base.io.bioimage.inspect
**Description**: Extract metadata (dimensions, pixel sizes, channel names, etc.) from an image file without loading the full pixel data.

**Use Cases**:
- Checking image dimensions before deciding on a processing strategy.
- Verifying channel names for a specific analysis pipeline.

**Inputs**:
- `path` (string, required): Absolute path to the image file.

**Outputs**:
- `metadata`: `TableRef` (containing key-value pairs of metadata) or JSON output.

**params_schema**:
```yaml
type: object
required: [path]
properties:
  path:
    type: string
    description: Absolute path to the local image file.
```

**Implementation Notes**:
- Uses `BioImage(path).metadata` and `BioImage(path).dims`.
- Should return a structured dictionary or a table artifact.
- Must be fast and not load heavy pixel data.

---

### 3.3 base.io.bioimage.slice
**Description**: Extract a subset of a multi-dimensional image (e.g., specific T, C, or Z slices) and return it as a new `BioImageRef`.

**Use Cases**:
- Selecting a specific channel from a multi-channel acquisition.
- Extracting a single timepoint from a time-lapse series for preview.
- Taking a central Z-slice from a large stack.

**Inputs**:
- `image`: `BioImageRef`
- `slices`: Map of dimension names to indices or ranges.

**Outputs**:
- `output`: `BioImageRef`

**params_schema**:
```yaml
type: object
required: [slices]
properties:
  slices:
    type: object
    description: Map of dimension labels (T, C, Z, Y, X) to integer indices or slice objects.
    additionalProperties:
      oneOf:
        - type: integer
        - type: object
          properties:
            start: {type: integer}
            stop: {type: integer}
            step: {type: integer}
```

**Implementation Notes**:
- Leverages `xarray` indexing if the input is an xarray-backed artifact.
- For file-backed artifacts, uses `BioImage.reader.get_image_dask_data()` to perform lazy slicing.
- Preserves physical metadata (pixel sizes) for the sliced output.

---

### 3.4 base.io.bioimage.get_supported_formats
**Description**: List all image file formats supported by the current environment's readers.

**Use Cases**:
- Allowing an agent to inform the user which files can be processed.
- Checking for the availability of specific format readers (e.g., bioformats).

**Inputs**: None

**Outputs**:
- `formats`: List of supported format strings.

**params_schema**:
```yaml
type: object
properties: {}
```

**Implementation Notes**:
- Queries `bioio` entrypoints and registered readers.
- Includes formats from `bioio-bioformats` if installed.

---

### 3.5 base.io.bioimage.validate
**Description**: Validate that a file can be read as a bioimage and report any potential issues (e.g., missing metadata, corrupt headers).

**Use Cases**:
- Pre-flight check before starting a long analysis pipeline.
- Troubleshooting why a file failed to load.

**Inputs**:
- `path` (string, required): Absolute path to the image file.

**Outputs**:
- `report`: `TableRef` or JSON with validation status and details.

**params_schema**:
```yaml
type: object
required: [path]
properties:
  path:
    type: string
    description: Absolute path to the local image file.
```

**Implementation Notes**:
- Attempts to instantiate `BioImage`.
- Checks for minimum required metadata (e.g., at least 2 spatial dimensions).
- Reports the specific reader that was selected for the file.

---

### 3.6 base.io.bioimage.export
**Description**: Export an artifact to a specific file format (OME-TIFF, OME-Zarr, PNG, CSV, NPY)

**Use Cases**:
- Saving processed results.
- Converting between formats.
- Creating shareable outputs.

**Inputs**:
- `image` (BioImageRef, optional)
- `table` (TableRef, optional)

**Outputs**:
- `output`: `BioImageRef` or `TableRef`

**params_schema**:
```yaml
type: object
properties:
  format:
    type: string
    enum: [OME-TIFF, OME-Zarr, PNG, CSV, NPY]
    description: Target export format.
```

**Implementation Notes**:
- Logic moved from existing `ops/export.py`.
- Infers format if not specified.

## 4. Implementation Plan

### Phase 1: Core Implementation
1.  Create `tools/base/bioimage_mcp_base/ops/io.py`.
2.  Implement the logic for all 6 functions using `bioio.BioImage` and other relevant utilities.

### Phase 2: Registration
1.  Remove `base.bioio.export` from `manifest.yaml`.
2.  Add new `base.io.bioimage.*` functions to the `functions` list.

### Phase 3: Verification
1.  Write contract tests in `tests/contract/test_io_functions.py`.
2.  Write integration tests for a full load-slice-export workflow.

## 5. Technical Details

- **Module**: All functions will be implemented in `tools/base/bioimage_mcp_base/ops/io.py`.
- **Registry**: Functions will be hardcoded in `manifest.yaml` to ensure stable schemas and high-quality descriptions.
- **Consistency**: All functions will use `bioio.BioImage` internally to ensure consistent dimension handling (TCZYX 5D model or native axes as per Spec 014).
- **Metadata**: `inspect` and `validate` will leverage `BioImage.metadata` and `BioImage.physical_pixel_sizes`.

## 6. Success Criteria

1.  All 6 functions are discoverable via `list_tools` and `describe_function`.
2.  An agent can successfully load a CZI file, inspect its Z-slices, extract one slice, and export it as a PNG.
3.  `base.bioio.export` is fully removed from the codebase.
4.  Documentation is updated to reflect the new preferred I/O namespace.
