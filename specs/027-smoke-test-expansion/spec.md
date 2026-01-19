# Feature Specification: Smoke Test Expansion with MCP-Native Equivalence Testing

**Feature Branch**: `027-smoke-test-expansion`  
**Created**: 2026-01-18  
**Status**: Draft  
**Input**: User description: "Expand smoke tests to cover each implemented library using dual execution (MCP vs native), data equivalence validation, and schema self-consistency detection."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate MCP Tool Accuracy Against Native Libraries (Priority: P1)

As a developer maintaining the bioimage-mcp server, I need confidence that MCP tool execution produces results equivalent to calling the underlying libraries directly, so I can catch regressions or drift before they affect users.

**Why this priority**: This is the core value of the feature. Without equivalence validation, MCP could silently produce different results than documented library behavior, breaking user trust and scientific reproducibility.

**Independent Test**: Can be fully tested by running a single library's equivalence test (e.g., PhasorPy) and verifying MCP results match native execution within tolerance.

**Acceptance Scenarios**:

1. **Given** a PhasorPy workflow executed via MCP, **When** the same workflow is run with native Python scripts, **Then** output arrays match within numerical tolerance (rtol=1e-5, atol=1e-8).
2. **Given** a Scikit-image filtering pipeline via MCP, **When** the same pipeline runs natively, **Then** outputs are equivalent using an explicit policy: exact equality for integer/bool images, and tolerance-based comparison for floating outputs (rtol=1e-5, atol=1e-8).
3. **Given** a Cellpose segmentation via MCP, **When** the same segmentation runs natively with identical parameters and determinism controls (fixed seed where supported; CPU-only and limited threads when needed for stability), **Then** label images achieve mean IoU >= 0.95 (acknowledging minor nondeterminism).

---

### User Story 2 - Detect Schema Drift Between MCP Interface and Tool Runtime (Priority: P2)

As a developer, I need to detect when the MCP-exposed function schema diverges from what the tool runtime actually expects, so schema mismatches don't cause runtime errors or confusing behavior.

**Why this priority**: Schema drift is a common source of integration bugs. Detecting it early prevents user-facing errors and reduces debugging time.

**Independent Test**: Can be fully tested by querying MCP `describe()` and comparing against the tool runtime's `meta.describe()` output for a set of functions.

**Acceptance Scenarios**:

1. **Given** a function exposed via MCP, **When** I compare the server's `describe(fn_id)` output with the tool runtime's `meta.describe` output (after applying the canonicalization rules in FR-006), **Then** parameter names, types, and defaults match exactly.
2. **Given** a schema mismatch is detected, **When** the test runs, **Then** it clearly reports which fields differ between server and runtime views.

---

### User Story 3 - Validate Matplotlib Output Semantics (Priority: P3)

As a developer, I need to verify that Matplotlib-generated plot artifacts are valid and correctly structured, even though pixel-perfect comparison is not practical due to rendering variations.

**Why this priority**: Plot outputs cannot be compared numerically, but semantic validation ensures users receive usable visualization artifacts.

**Independent Test**: Can be tested by generating a PlotRef artifact via MCP and validating existence, dimensions, and basic image properties.

**Acceptance Scenarios**:

1. **Given** a Matplotlib workflow via MCP, **When** a PlotRef artifact is produced, **Then** the artifact file exists and is non-empty.
2. **Given** a PlotRef artifact, **When** its properties are inspected, **Then** dimensions match expected DPI and figure size within a loose tolerance.
3. **Given** a PlotRef artifact, **When** the image is readable, **Then** histogram/mean intensity falls within an expected range.

---

### User Story 4 - Verify Xarray/Pandas Metadata Preservation (Priority: P3)

As a developer, I need to ensure that data manipulation through MCP preserves metadata (coordinates, column names, attributes), not just array values.

**Why this priority**: Metadata loss can break downstream workflows that depend on coordinate systems or column semantics.

**Independent Test**: Can be tested by running Xarray transpose or Pandas describe operations and verifying metadata in output artifacts.

**Acceptance Scenarios**:

1. **Given** an Xarray transpose operation via MCP, **When** the output is compared to native execution, **Then** coordinates and dimension names are preserved.
2. **Given** a Pandas DataFrame describe operation via MCP, **When** output is compared to native execution, **Then** column names and index values match.

---

### Edge Cases

- What happens when required datasets are not present (Git LFS not fetched)?
  - Tests should detect LFS pointer files and skip gracefully with informative messages.
- How does the system handle nondeterministic library behavior (e.g., Cellpose with different torch threads)?
  - Use IoU/Dice thresholds instead of exact equality; apply determinism controls when available (fixed seeds, CPU-only where required, thread limits), and document determinism limits.
- What happens when native execution fails due to missing conda environment?
  - Tests should skip with a clear message indicating the required environment.
- What happens when equivalence tests accidentally run in smoke_minimal?
  - Marker enforcement tests should fail fast if any `test_equivalence_*.py` is missing `@pytest.mark.smoke_full`.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

Note: These constraints are restatements of constitution-aligned requirements for emphasis; functional requirements below are the source of truth for task coverage.

- **MCP API impact**: No changes to MCP endpoints. Tests consume existing `describe()` and `run()` APIs.
- **Artifact I/O**: Tests validate BioImageRef, LabelImageRef, PlotRef, and TableRef artifacts. Comparison uses BioImage for reading OME-TIFF and OME-Zarr formats.
- **Isolation**: Native script execution must use `conda run -n <env>` to respect tool environment isolation. Tests run in core environment but spawn isolated subprocesses.
- **Reproducibility**: Test results are deterministic within documented tolerances. Reference scripts use explicit parameter values matching MCP defaults.
- **Safety/observability**: All equivalence tests are marked `smoke_full` to stay within CI time budgets. Test failures report specific values and differences.

### Functional Requirements

- **FR-001**: System MUST provide equivalence tests for each implemented library (PhasorPy, Cellpose, Scikit-image, SciPy, Matplotlib, Xarray, Pandas).
- **FR-002**: System MUST execute native reference scripts using `conda run -n <env>` to ensure correct library isolation.
- **FR-003**: System MUST compare array outputs after normalizing shapes.
  - Float arrays: compare with numerical tolerance (rtol=1e-5, atol=1e-8).
  - Integer/bool arrays: compare with exact equality.
- **FR-004**: System MUST compare label images using segmentation metrics (IoU/Dice > threshold) instead of exact equality.
  - Default threshold: mean IoU >= 0.99 for deterministic algorithms; mean IoU >= 0.95 for known nondeterministic pipelines (e.g., Cellpose) unless a library-specific override is specified in the test.
- **FR-005**: System MUST validate plot artifacts using semantic invariants (existence, dimensions, readability) rather than pixel equality.
- **FR-006**: System MUST provide schema self-consistency tests comparing `describe(fn_id)` against tool runtime `meta.describe` output.
  - Runtime schema acquisition MUST be implemented via a per-environment reference script (executed with `conda run -n <env>`) that emits canonicalized JSON to stdout.
  - Canonicalization MUST (at minimum): sort keys, normalize ordering of lists where order is not semantically meaningful, and ignore documentation-only fields (e.g., title/description/examples) while preserving all runtime-relevant fields.
  - These tests MAY run in `smoke_minimal` mode as they are lightweight.
- **FR-007**: System MUST use synthetic or minimal test data to minimize CI resource usage; real datasets gated behind `smoke_full` marker.
  - “Minimal” MUST be defined per library test (shape/dtype/dims) and stored as a reusable fixture.
  - Each equivalence test MUST declare whether it uses minimal data only, or requires an LFS dataset.
  - Minimal-data tests MUST be runnable in `smoke_minimal` mode; equivalence tests remain `smoke_full`.
- **FR-008**: System MUST detect Git LFS pointer files and skip tests gracefully when real datasets are unavailable.
- **FR-009**: System MUST mark all equivalence tests with `@pytest.mark.smoke_full` marker.
  - Additionally, equivalence tests SHOULD be marked with `@pytest.mark.requires_env("bioimage-mcp-...")` when a specific tool env is required, and MUST skip with a clear message if the env is not installed.
- **FR-010**: System MUST provide helper utilities for data equivalence comparison (array, label, plot semantic, and table).
  - Helpers MUST encode the “exact vs tolerance” policy for images/arrays (integer/bool exact, float tolerance) to avoid per-test drift.
- **FR-011**: System MUST ensure all tool adapters produce artifacts compatible with BioImage reading (valid OME-TIFF or OME-Zarr format).
  - Scope for this feature: the equivalence tests MUST demonstrate BioImage readability for each artifact type exercised (BioImageRef, LabelImageRef, TableRef, PlotRef) and MUST fail with actionable diagnostics if an artifact is unreadable.

### Key Entities

- **EquivalenceTest**: A paired execution test comparing MCP workflow output against native script output for the same operation.
- **ReferenceScript**: A pure Python script that executes library operations identically to MCP workflows, run in isolated conda environments.
  - Contract: emits a single JSON object to stdout (machine-parseable), writes outputs to a known path, and logs human text to stderr.
- **DataEquivalenceHelper**: Utility for comparing MCP artifacts to native arrays with appropriate tolerance and normalization.
- **SchemaAlignmentTest**: A test that verifies MCP schema matches tool runtime metadata for a given function.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All equivalence tests pass within defined tolerances for all seven libraries (PhasorPy, Cellpose, Scikit-image, SciPy, Matplotlib, Xarray, Pandas) and all are marked `smoke_full`.
- **SC-002**: Schema self-consistency tests pass for all exposed functions (no drift between server and runtime metadata).
- **SC-003**: Tests correctly skip when datasets are unavailable (Git LFS not fetched), with informative skip messages.
- **SC-004**: Native execution correctly uses isolated environments via `conda run`, verified by successful execution in environments different from the test runner.
- **SC-005**: Minimal CI runs (`smoke_minimal`) complete within time budget; equivalence tests run only in `smoke_full` mode. Schema self-consistency tests may run in `smoke_minimal` as they require no heavy computation.
- **SC-006**: Cellpose equivalence achieves mean IoU >= 0.95 between MCP and native label outputs (with explicit determinism controls where possible).
- **SC-007**: Matplotlib equivalence validates artifact existence and basic semantic properties without false failures from rendering differences.
