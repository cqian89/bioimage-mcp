# Feature Specification: FLIM Phasor Analysis Gap Fix

**Feature Branch**: `003-base-tool-schema`  
**Created**: 2025-12-21  
**Status**: Draft  
**Input**: User description: "plan the next implementation phase (003) to fix issues identified in @specs/002-base-tool-schema/retrospective.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute phasor maps from FLIM data (Priority: P1)

As a bioimaging workflow user, I want to convert time-resolved fluorescence data into phasor coordinate images, so I can perform downstream FLIM analysis and visualization using standardized outputs.

**Why this priority**: The retrospective for phase 002 identified phasor analysis as a planned but missing capability, blocking a key FLIM workflow.

**Independent Test**: Can be fully tested by providing a reference FLIM dataset artifact, running the phasor transform, and verifying that the expected output artifacts (phasor coordinate images and an intensity image) are produced and readable.

**Acceptance Scenarios**:

1. **Given** a valid FLIM dataset artifact with a time/bin dimension and spatial dimensions, **When** the user runs the phasor transform tool, **Then** the system produces phasor coordinate output artifacts (G and S) and an integrated intensity image artifact (sum over time/bins) with spatial dimensions matching the input (and preserving channel dimension if present).
2. **Given** an input artifact that is missing a time/bin dimension (or the time/bin dimension is ambiguous), **When** the user runs the phasor transform tool, **Then** the system fails with a clear validation error describing what is required and how to correct the input.
3. **Given** an input artifact in an unsupported format (e.g., OME-Zarr), **When** the user runs the phasor transform tool, **Then** the system fails fast with an actionable validation error advising conversion to OME-TIFF.
4. **Given** a valid FLIM dataset artifact that includes a channel dimension with more than one channel, **When** the user runs the phasor transform tool, **Then** the system produces per-channel phasor coordinate output artifacts (G and S) that preserve the channel dimension.

---

### User Story 2 - Reduce noise in phasor outputs (Priority: P2)

As a workflow user, I want an optional denoising step for phasor outputs, so downstream analysis is less sensitive to pixel-level noise.

**Why this priority**: Many FLIM datasets are noisy; producing smoother phasor maps improves usability without changing the underlying workflow.

**Independent Test**: Can be fully tested by running a denoising operation on a phasor output artifact and verifying a new artifact is produced with the same spatial shape and appropriate value ranges.

**Acceptance Scenarios**:

1. **Given** a phasor output artifact (G and/or S), **When** the user applies a denoising operation with valid parameters (defaulting to median, but allowing others), **Then** the system produces a new denoised phasor artifact that preserves spatial shape and is readable.

---

### User Story 3 - Validate an end-to-end FLIM workflow with segmentation (Priority: P3)

As a maintainer, I want an automated end-to-end workflow validation that combines phasor generation with an existing segmentation step, so regressions in artifact handling and multi-tool workflows are caught early.

**Why this priority**: The retrospective identified the absence of end-to-end FLIM workflow coverage; an integrated test provides confidence that the missing capability is truly delivered.

**Independent Test**: Can be fully tested by executing one automated workflow that (1) computes phasor outputs, (2) derives an intensity image for segmentation, (3) runs segmentation, and (4) verifies all expected output artifacts exist and are readable.

**Acceptance Scenarios**:

1. **Given** the runtime prerequisites for the workflow are available, **When** the automated workflow validation is executed, **Then** the workflow completes successfully and produces readable output artifacts for phasor maps (G/S), an intensity image, and a segmentation mask.
2. **Given** required runtime prerequisites are not available, **When** the test suite is executed, **Then** the workflow validation is explicitly skipped with a clear, actionable reason.

---

### Edge Cases

- Input FLIM dataset contains unexpected dimensionality (e.g., missing spatial axes, multiple candidate time axes, or additional channels).
- Input data contains non-finite values (NaN/Inf) or unsupported data types.
- Very small datasets where denoising parameters are invalid (e.g., filter size larger than image).
- Very large datasets (>4GB) should trigger a warning to the user, but execution should proceed (allowing failure only on OOM).
- The reference dataset is unavailable in some environments (e.g., lightweight clones), requiring either synthetic data generation for tests or a clear skip reason.

## Clarifications

### Session 2025-12-21

- The goal of phase 003 is to close the gap identified in the phase 002 retrospective: add the planned phasor-based FLIM capability and validate it end-to-end.
- Q: For the phasor transform, how should we determine the per-bin phase/time mapping? → A: Prefer physical timing metadata when present; otherwise fall back to uniform bin index mapping (0..2π), and record the chosen mode in the workflow run record.
- Q: How should we derive the “intensity image” artifact from the FLIM dataset for segmentation? → A: Sum over time/bins (integrated intensity).
- Q: For phase 003, what artifact formats should the phasor tools accept/produce? → A: OME-TIFF only; fail fast on OME-Zarr with an actionable error.
- Q: If the FLIM dataset includes a channel dimension with more than 1 channel, what should the phasor tool do by default? → A: Compute per-channel G/S outputs (multi-channel artifacts).
- Q: If the FLIM dataset has multiple channels (C>1), how should we derive the intensity image artifact for segmentation? → A: Produce a multi-channel intensity image (preserve channel dimension) and leave segmentation handling to downstream tools.
- Q: Which denoising algorithm should be used for the optional phasor denoising operation? → A: Default to Median filter, but allow user-specified alternatives (e.g., Gaussian).
- Q: Which specific denoising algorithms should be supported beyond the default Median filter? → A: Support all standard simple filters available in `scikit-image`: Mean, Gaussian, Median, and Bilateral.
- Q: How should parameters for the selected denoising filter be passed? → A: Use a structured schema with explicit optional fields (e.g., `filter_type`, `sigma`, `radius`) in the tool definition.
- Q: If the input to the denoising operation has multiple channels, how should the filter be applied? → A: Apply the 2D filter independently to each channel plane (do not filter across the channel dimension).
- Q: How should the system handle very large FLIM datasets that risk excessive runtime or memory use? → A: Warn if >4GB, but allow execution to proceed (fail only on OOM).
- Q: What is the output contract of the phasor transform tool? → A: Return three artifact references: G, S, and integrated intensity (sum over time/bins), plus an optional warnings list when applicable.
- Q: How can callers specify the time/bin dimension when inference is ambiguous? → A: Provide an explicit `time_axis` parameter (axis name or integer index) to override inference; record the resolved axis in the workflow run record.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No breaking changes to existing tool discovery or payload shapes. New capabilities are added as additional tools/functions and remain compatible with “summary-first” discovery.
- **Artifact I/O**: Inputs and outputs MUST be passed and returned as artifact references. Input is a time-resolved FLIM intensity dataset in **OME-TIFF** format with a time/bin dimension plus spatial dimensions. Outputs include phasor coordinate images (G and S), an intensity image suitable for segmentation, and (in the integrated workflow) a segmentation mask artifact, all in **OME-TIFF** format. If an input artifact is provided in OME-Zarr, the system MUST fail fast with an actionable error advising conversion to OME-TIFF.
- **Isolation**: Phasor analysis runs in the base tool environment. Segmentation (for the integrated test) runs in the existing segmentation environment. Cross-environment orchestration uses artifact references only.
- **Reproducibility**: Each run MUST record inputs, selected operations, resolved parameter values (including the phasor bin-to-phase/time mapping mode used), produced output references, and tool-pack version information sufficient to replay the workflow.
- **Safety/observability**: The system MUST validate inputs, provide clear errors for invalid calls, emit structured logs and persist them as artifacts, and include automated tests covering both the phasor operations and at least one live workflow path.

### Functional Requirements

- **FR-001**: The system MUST provide a callable operation that converts a FLIM time-resolved dataset artifact into phasor coordinate outputs (G and S) as artifacts.
- **FR-002**: The phasor operation MUST either (a) correctly infer the time/bin dimension when unambiguous or (b) allow the user to specify which dimension represents time/bins via an explicit `time_axis` parameter (axis name or integer index).
- **FR-003**: The phasor operation MUST return outputs only as artifact references (not embedded raw arrays), per the Artifact I/O constraint.
- **FR-004**: The system MUST provide an intensity image artifact derived from the FLIM dataset by summing over the time/bin dimension (integrated intensity) without requiring the user to manually export intermediate files. The phasor transform operation MUST return this integrated intensity as an output artifact alongside G and S. If the dataset has a channel dimension, the intensity image MUST preserve that channel dimension (per-channel integrated intensity).
- **FR-005**: The system MUST provide an optional denoising operation for phasor outputs, defaulting to a Median filter algorithm but supporting user-specified standard `scikit-image` filters (Mean, Gaussian, Median, Bilateral) via a structured parameter schema. At minimum, the schema MUST include `filter_type` (one of `mean`, `gaussian`, `median`, `bilateral`) and filter-specific parameters (e.g., `radius` for mean/median, `sigma` for gaussian, `sigma_color`/`sigma_spatial` for bilateral), and MUST validate that irrelevant parameters are rejected (rather than silently ignored). The operation MUST produce a new artifact output while preserving spatial shape. For multi-channel inputs, the filter MUST be applied independently to each 2D channel plane.
- **FR-006**: The system MUST fail fast with a clear validation error when the input artifact is missing required dimensions, is unreadable, is in an unsupported format (per the Artifact I/O constraint), or contains unsupported values. For oversized inputs (>4GB), the system MUST include a warning in the response (e.g., in a structured `warnings` field) but allow execution to proceed.
- **FR-007**: The project MUST include an automated end-to-end workflow validation that produces phasor outputs and a segmentation mask from the derived intensity image, and verifies that all expected artifacts exist and are readable.
- **FR-008**: The phasor computation MUST prefer physical timing metadata when available; otherwise it MUST use a uniform bin index phase mapping (0..2π). The workflow run record MUST capture which mapping mode was used.
- **FR-009**: If the input dataset includes a channel dimension with more than one channel, the phasor outputs (G and S) MUST preserve that channel dimension (per-channel phasor maps) rather than implicitly selecting or collapsing channels.


### Acceptance Coverage

- User Story 1 validates FR-001 through FR-004, FR-006, FR-008, and FR-009.
- User Story 2 validates FR-005.
- User Story 3 validates FR-007 and contributes to FR-001 through FR-004 and FR-009 (integration).

### Assumptions & Dependencies

- A reference FLIM dataset in **OME-TIFF** format is available for validation (preferred: an existing dataset already used by the project; when present, use `datasets/FLUTE_FLIM_data_tif/`). For the integrated segmentation workflow validation, prefer a single-channel reference dataset (C=1) unless the downstream segmentation step explicitly supports multi-channel inputs; if a multi-channel dataset is used, the workflow validation may select a single channel for segmentation input while still preserving channels in the derived intensity artifact. When unavailable, tests will either generate a small synthetic FLIM dataset or skip with an explicit reason.
- An existing segmentation capability is available for use in the integrated workflow validation.
- The phasor outputs (G and S) and intensity image are sufficient as standardized intermediates for downstream analysis and testing. Note: if the intensity image preserves multiple channels, downstream steps (e.g., segmentation) may require a channel-selection/collapse policy.

### Out of Scope

- Advanced FLIM lifetime fitting models beyond phasor coordinate generation.
- Interactive visualization or UI for phasor plots.
- Expanding to new specialized tool packs beyond what is needed for phasor analysis and the existing segmentation workflow validation.

### Key Entities *(include if feature involves data)*

- **FLIM Dataset Artifact**: A time-resolved intensity dataset in OME-TIFF format with spatial dimensions and a time/bin axis.
- **Phasor Map Artifact**: Output images representing phasor coordinates (G and S) derived from the FLIM dataset (preserving the channel dimension as per-channel phasor maps when present).
- **Intensity Image Artifact**: A derived image (from the FLIM dataset) intended for downstream segmentation (integrated intensity: sum over time/bins, preserving channel dimension if present).
- **Segmentation Mask Artifact**: A label/mask output produced by a segmentation step.
- **Workflow Run Record**: A record of inputs, parameters, outputs, and status for a single workflow execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The phasor capability is discoverable and executable end-to-end: for the reference FLIM dataset, the system produces readable artifacts for G, S, and the derived intensity image on every run.
- **SC-002**: The automated end-to-end workflow validation produces readable artifacts for G, S, the derived intensity image, and a segmentation mask when prerequisites are available; otherwise it is explicitly skipped with a clear reason.
- **SC-003**: The phasor operations have automated coverage: at least one unit test validates correct handling of valid input and at least one unit test validates a clear failure mode for invalid/ambiguous input.
- **SC-004**: Backward compatibility is maintained: existing phase 002 base tools remain discoverable and callable without client changes.
