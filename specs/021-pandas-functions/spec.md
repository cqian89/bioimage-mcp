# Feature Specification: Pandas Functions for Tabular Data

**Feature Branch**: `021-pandas-functions`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: User description: "Add pandas as a first-class dependency enabling table I/O functions and dynamic pandas DataFrame operations for measurement data manipulation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load Cellpose Measurement CSV (Priority: P1)

A biologist has run Cellpose segmentation and generated a CSV file containing cell measurements (area, mean intensity, perimeter, etc.). They want to load this data into the bioimage-mcp workflow for further analysis.

**Why this priority**: Table loading is the foundational capability - without it, no other tabular operations are possible. Cellpose measurement files are a primary use case.

**Independent Test**: Can be fully tested by providing a sample Cellpose measurement CSV and verifying it loads as a valid TableRef with correct column metadata.

**Acceptance Scenarios**:

1. **Given** a valid Cellpose measurement CSV file on an allowed path, **When** the user calls `base.io.table.load` with the file path, **Then** the system returns a TableRef with column names, data types, and row count metadata.
2. **Given** a TSV file (tab-delimited), **When** the user calls `base.io.table.load` without specifying delimiter, **Then** the system auto-detects the tab delimiter and loads correctly.
3. **Given** a file path outside the configured allowlist, **When** the user attempts to load it, **Then** the system returns a structured error (code/message/details with JSON Pointer `path` and actionable `hint`) and logs the allow/deny decision with the path and reason.

---

### User Story 2 - Filter Cells by Measurement Thresholds (Priority: P1)

A researcher wants to filter their measurement table to include only cells meeting specific criteria (e.g., area > 100 and circularity > 0.8) before exporting for downstream analysis.

**Why this priority**: Filtering is the most common operation after loading - researchers need to clean data and focus on relevant subpopulations.

**Independent Test**: Can be tested by loading a sample table with known values, applying a filter query, and verifying the resulting row count and values match expectations.

**Acceptance Scenarios**:

1. **Given** a loaded TableRef with numeric columns, **When** the user calls `base.pandas.DataFrame.query` with expression `"area > 100"`, **Then** the system returns an ObjectRef containing only rows where area exceeds 100.
2. **Given** a TableRef, **When** the user filters with compound expression `"area > 100 and circularity > 0.8"`, **Then** only rows meeting both conditions are retained.
3. **Given** any query operation, **When** it executes, **Then** the query expression is logged for audit purposes.

---

### User Story 3 - Aggregate Measurements by Condition (Priority: P2)

A researcher wants to group cells by experimental condition (e.g., treatment, time point, well ID) and compute summary statistics (mean, std) for each group.

**Why this priority**: Aggregation by condition is essential for comparing experimental groups, but depends on basic load/filter working first.

**Independent Test**: Can be tested by grouping a sample dataset by a categorical column and verifying the aggregated statistics match expected values.

**Acceptance Scenarios**:

1. **Given** a DataFrame ObjectRef with a "condition" column, **When** the user calls `base.pandas.DataFrame.groupby` with `by="condition"`, **Then** the system returns a GroupByRef.
2. **Given** a GroupByRef, **When** the user calls `base.pandas.GroupBy.mean`, **Then** the system returns an ObjectRef containing group-wise means for all numeric columns.
3. **Given** a GroupByRef, **When** the user calls `base.pandas.GroupBy.agg` with `func=["mean", "std", "count"]`, **Then** the system returns statistics for each function per group.

---

### User Story 4 - Export Filtered Results (Priority: P2)

A researcher has filtered and processed their measurement data and wants to export the results to a CSV file for use in other tools (Excel, R, GraphPad Prism).

**Why this priority**: Export is essential for delivering results, but loading and processing must work first.

**Independent Test**: Can be tested by exporting a sample DataFrame to CSV and verifying the file contents match the data.

**Acceptance Scenarios**:

1. **Given** a TableRef or DataFrame ObjectRef, **When** the user calls `base.io.table.export`, **Then** the system writes a delimited file (CSV/TSV) to the work directory and returns a TableRef pointing to it.
2. **Given** export parameters specifying TSV format (`sep="\t"`), **When** export executes, **Then** the output file uses tab delimiters.
3. **Given** floating-point values, **When** exported, **Then** numeric precision is preserved to 15 significant digits by default.

---

### User Story 5 - Merge Measurement Tables (Priority: P3)

A researcher has measurements from multiple sources (e.g., intensity measurements + morphology measurements) and wants to join them by cell label or unique ID.

**Why this priority**: Merging enables complex multi-source analysis but is less common than basic load/filter/export workflows.

**Independent Test**: Can be tested by providing two tables with a common key column and verifying the merged result contains columns from both.

**Acceptance Scenarios**:

1. **Given** two DataFrame ObjectRefs sharing a "cell_id" column, **When** the user calls `base.pandas.merge` with `on="cell_id"`, **Then** the result contains all columns from both tables for matching IDs.
2. **Given** a left join request (`how="left"`), **When** merging, **Then** all rows from the left table are preserved with nulls for missing right-side matches.

---

### User Story 6 - Multi-Step Pandas Chaining (Priority: P3)

An advanced user wants to perform a sequence of operations (load → filter → groupby → aggregate → export) using ObjectRef chaining, similar to native pandas syntax.

**Why this priority**: Chaining enables complex workflows but builds on all previous capabilities.

**Independent Test**: Can be tested by executing a full workflow chain and verifying the final exported table matches expected results.

**Acceptance Scenarios**:

1. **Given** an ObjectRef from a previous operation, **When** used as input to the next pandas operation, **Then** the system retrieves the in-memory DataFrame and continues processing.
2. **Given** a complete chain of 5+ operations, **When** executed sequentially, **Then** each step produces a valid ObjectRef until final materialization to TableRef.

---

### Edge Cases

- What happens when a CSV file is empty (headers only)?
  - System should return a TableRef with column metadata but row_count=0
- What happens when a query expression has syntax errors?
  - System should return a structured error indicating the invalid expression with an actionable hint (e.g., show supported operators / example syntax)
- What happens when a column referenced in groupby does not exist?
  - System should return a structured error listing available columns with a hint to choose a valid column
- What happens when loading a file with inconsistent row lengths?
  - System should use pandas default behavior (raise error) and surface it clearly
- What happens when loading a file larger than 100MB?
  - System should log a warning but proceed with loading
- What happens when ObjectRef expires from memory cache?
  - System should return a structured error indicating the object is no longer available with a hint to re-run the workflow (or materialize intermediate results to TableRef)

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No new MCP tools; uses existing `run`, `list`, `describe` endpoints. No migration required.
- **Artifact I/O**: Inputs and outputs use TableRef (file-backed CSV/TSV) or ObjectRef (in-memory DataFrame). All data exchange via artifact references - no raw data in MCP messages.
- **Isolation**: Pandas runs in the `bioimage-mcp-base` environment (subprocess), not the core server. No new tool-pack required; extends existing base toolkit.
- **Reproducibility**: Lockfile update required for pandas dependency. All operations recorded in session history for replay.
- **Safety/observability**: File access is enforced via filesystem allowlists; all allow/deny/ask decisions are logged with path and reason. All `query()` expressions are logged for audit. Denylist prevents dangerous methods (arbitrary code execution, serialization bypasses). All user-facing failures return structured errors (code/message/details with JSON Pointer path and actionable hint).

### Functional Requirements

- **FR-001**: System MUST provide a `base.io.table.load` function that loads CSV, TSV, or other delimited files into a TableRef artifact.
- **FR-002**: System MUST auto-detect the delimiter when not explicitly specified (supporting comma, tab, and semicolon).
- **FR-003**: System MUST validate file paths against the configured `filesystem.allowed_read` allowlist before loading.
- **FR-004**: System MUST provide a `base.io.table.export` function that exports TableRef or ObjectRef to a delimited file.
- **FR-005**: System MUST preserve numeric precision (15 significant digits) when exporting floating-point values.
- **FR-006**: System MUST expose pandas DataFrame operations via dynamic discovery using the existing adapter pattern.
- **FR-007**: System MUST implement a category-based allowlist that enables safe pandas methods while blocking dangerous ones (serialization, arbitrary code execution, memory-unsafe operations).
- **FR-008**: System MUST block the following method categories: direct serialization (`to_csv`, `to_pickle`, etc.), memory-unsafe (`to_numpy`, `values`), arbitrary code (`eval`, `pipe`).
- **FR-009**: System MUST allow `query()` with full expression syntax, logging all queries for security audit.
- **FR-010**: System MUST restrict `apply()` to a whitelist of numpy function names only (e.g., `log`, `sqrt`, `exp`, `abs`).
- **FR-011**: System MUST return `GroupByRef` from `groupby()` operations, enabling pandas-style method chaining for aggregations.
- **FR-012**: System MUST provide `to_tableref` operation to materialize in-memory ObjectRef to file-backed TableRef.
- **FR-013**: System MUST include column metadata (names, dtypes, row count) in TableRef artifacts.
- **FR-014**: System MUST support encoding specification for non-UTF-8 files (latin-1, cp1252).
- **FR-015**: System MUST support custom NA value specification for domain-specific missing data markers.
- **FR-016**: System MUST log file permission decisions (allow/deny/ask) with the path and reason when enforcing filesystem allowlists for table load/export.
- **FR-017**: System MUST return structured errors with `code`, `message`, and `details[]` (each detail includes JSON Pointer `path` and actionable `hint`) for all user-facing failures introduced by this feature (e.g., denied paths, invalid query syntax, missing columns, denylisted methods, expired ObjectRefs).

### Key Entities

- **TableRef**: File-backed tabular data artifact with column metadata (names, dtypes), row count, delimiter, and encoding information. Format is CSV/TSV.
- **ObjectRef**: In-memory Python object reference (URI: `obj://...`) used for DataFrame chaining between pandas operations. Includes `python_class` field (e.g., `pandas.core.frame.DataFrame`).
- **GroupByRef**: Specialized ObjectRef returned by `groupby()` operations, supporting aggregation method chaining (`mean`, `sum`, `count`, etc.).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can load a Cellpose measurement CSV and receive a valid TableRef within 5 seconds for files up to 10MB.
- **SC-002**: Users can filter a 100,000-row table using `query()` and receive results within 2 seconds.
- **SC-003**: Users can complete a full workflow (load → filter → groupby → aggregate → export) in under 30 seconds for typical datasets (100,000 rows x 20 columns).
- **SC-004**: At least 50 pandas DataFrame methods are discoverable via `list` and usable via `run`.
- **SC-005**: All dangerous pandas methods (per denylist) are blocked and return structured errors when attempted.
- **SC-006**: ObjectRef chaining works for at least 10 sequential operations without memory issues.
- **SC-007**: Exported tables can be opened correctly in Excel, R, and Python pandas without data loss or encoding issues.
- **SC-008**: All `query()` operations are logged with expression, input ref_id, and result row count for audit review.

## Assumptions

- Pandas is already a transitive dependency via bioio and phasorpy, so adding it explicitly has minimal environment impact.
- The base environment has sufficient memory for typical measurement tables (up to ~100MB working set).
- Users will materialize intermediate results to TableRef when memory-backed ObjectRefs are not needed.
- The category-based allowlist approach (enable categories, deny specific methods) is maintainable as pandas evolves.
- UTF-8 encoding is the default and covers the majority of use cases.
