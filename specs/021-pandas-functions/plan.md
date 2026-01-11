# Plan: 021-pandas-functions

**Branch**: `021-pandas-functions` | **Date**: 2026-01-11 | **Spec**: [specs/021-pandas-functions/spec.md]

## Summary

Implementation of a comprehensive set of pandas-based table manipulation functions for the `bioimage-mcp` base toolkit. This feature uses a dynamic registry pattern matching `xarray`, enabling curated pandas methods (filtering, aggregation, merging) to be exposed as MCP tools.

## Technical Context

- **Language/Version**: Python 3.13 (core server & base tool env)
- **Primary Dependencies**: `pandas`, `numexpr`
- **Storage**: Local filesystem artifact store for `TableRef` (CSV/TSV); In-memory `OBJECT_CACHE` for `ObjectRef` (DataFrames/GroupBy).
- **Testing**: `pytest` unit tests for each operation; integration tests for multi-step pipelines.
- **Constraints**: No raw table data in MCP messages; all I/O via `TableRef`.

## Constitution Check

- [x] **Stable MCP surface**: All new functions use standard MCP tool patterns; discovery is paginated.
- [x] **Summary-first responses**: Tool manifests provide summaries; full detail via `describe`.
- [x] **Tool execution isolated**: Functions run in `bioimage-mcp-base` subprocesses.
- [x] **Artifact references only**: Tables are passed as `TableRef` (URI-based).
- [x] **Reproducibility**: Environment pinned via `conda-lock`; operations recorded in run logs.
- [x] **Safety + debuggability**: `query()` audit logging; isolated subprocesses.

## Project Structure

### Documentation (this feature)

```text
specs/021-pandas-functions/
├── plan.md              # Implementation plan
├── research.md          # Design decisions and research
├── data-model.md        # TableRef and ObjectRef schemas
├── quickstart.md        # User guide
└── contracts/
    └── pandas-functions.yaml  # Function signatures
```

### Source Code

```text
src/bioimage_mcp/
└── registry/
    └── dynamic/
        ├── pandas_allowlists.py    # pandas method allowlists
        ├── pandas_adapter.py       # core pandas execution logic
        └── adapters/
            ├── pandas.py           # PandasAdapterForRegistry
            └── __init__.py         # registry for pandas adapter (updated)

tools/base/
├── bioimage_mcp_base/
│   └── ops/
│       └── io.py                  # table.load/export (extended)
└── manifest.yaml                  # dynamic_sources + base.io.table.* (updated)

envs/
└── bioimage-mcp-base.yaml         # added pandas dependency (updated)

tests/
├── unit/
│   └── registry/
│       └── test_pandas_adapter.py
└── integration/
    └── test_pandas_pipeline.py
```

## Implementation Steps

### 1. Environment and Dependencies
- [ ] Add `pandas` and `numexpr` to `envs/bioimage-mcp-base.yaml`.
- [ ] Update `bioimage-mcp-base` environment.

### 2. Registry Integration (xarray pattern)
- [ ] Create `src/bioimage_mcp/registry/dynamic/pandas_allowlists.py` with categories:
    - `DATAFRAME_CLASS` (Optional convenience: `TableRef` → `ObjectRef` DataFrame)
    - `DATAFRAME_METHODS` (Curated list: `query`, `groupby`, `sort_values`, etc.; `query` accepts `TableRef` directly via auto-coercion)
    - `GROUPBY_METHODS` (Reductions: `mean`, `sum`, `count`, etc.)
    - `TOPLEVEL_FUNCTIONS` (`concat`, `merge`)
- [ ] Create `src/bioimage_mcp/registry/dynamic/pandas_adapter.py` for core execution logic.
- [ ] Create `src/bioimage_mcp/registry/dynamic/adapters/pandas.py` (implementing `BaseAdapter`).
- [ ] Register `PandasAdapterForRegistry` in `src/bioimage_mcp/registry/dynamic/adapters/__init__.py`.

### 3. Static I/O Functions
- [ ] Extend `tools/base/bioimage_mcp_base/ops/io.py` with:
    - `table_load`: Load CSV/TSV (delimited) into `TableRef`.
    - `table_export`: Save `TableRef` or `ObjectRef` (DataFrame) to disk as CSV/TSV (delimited).

### 4. Manifest Update
- [ ] Add `pandas` to `dynamic_sources` in `tools/base/manifest.yaml`.
- [ ] Define `base.io.table.load` and `base.io.table.export` in `functions` section.

### 5. Verification
- [ ] Unit tests for `PandasAdapter` logic.
- [ ] Contract tests for generated pandas tool schemas.
- [ ] Integration test: Load CSV -> Query -> GroupBy -> Mean -> Export CSV/TSV.

## Complexity Tracking

*No violations.*
