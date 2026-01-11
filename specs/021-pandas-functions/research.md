# Research: Pandas Table Functions (Spec 021)

This document outlines the design decisions for implementing pandas-based operations in `bioimage-mcp`.

## 1. Function ID Naming Pattern
**Decision**: Follow the `xarray` pattern already established in the base toolkit.
- Pattern: `base.pandas.[Class].[Method]`
- Examples:
  - `base.pandas.DataFrame.query`
  - `base.pandas.DataFrame.groupby`
  - `base.pandas.GroupBy.mean`
- Top-level functions: `base.pandas.merge`, `base.pandas.concat`.

## 2. Allowlist Approach
**Decision**: Use a category-based allowlist with a strict denylist.
- **Allowed Categories**:
  - Selection: `query`, `filter`, `head`, `tail`, `sample`.
  - Aggregation: `mean`, `sum`, `count`, `min`, `max`, `std`, `var`, `describe`.
  - Transformation: `fillna`, `dropna`, `replace`, `sort_values`, `reset_index`.
  - Relational: `merge`, `concat`, `join`.
- **Denylist**: `eval`, `to_pickle`, `to_csv` (use `base.io.table.export`), `read_*` (use `base.io.table.load`).

## 3. GroupBy Handling
**Decision**: Return a `GroupByRef` (subtype of `ObjectRef`) for chaining.
- Calling `df.groupby()` returns a `GroupByRef`.
- Subsequent aggregation tools (e.g., `base.pandas.GroupBy.mean`) accept a `GroupByRef` and return an `ObjectRef` (DataFrame).
- This prevents large intermediate objects from being serialized.

## 4. `query()` Safety
**Decision**: Allow `query()` with strict audit logging and restricted engines.
- Use `engine="python"` or `engine="numexpr"` (if available).
- The `query` string is captured in the workflow run log for reproducibility and audit.
- No local variable access (`@var`) allowed to maintain isolation.

## 5. `apply()` Restrictions
**Decision**: Limit `apply()` to pre-defined numpy function names.
- Users can pass strings like `"sqrt"`, `"log"`, `"abs"`.
- Arbitrary lambda functions are prohibited to prevent arbitrary code execution and ensure workflow serializability.

## 6. Memory Management
**Decision**: Use the `OBJECT_CACHE` pattern.
- DataFrames and GroupBy objects are stored in an in-memory dictionary within the tool runtime.
- Artifact IDs correspond to cache keys.
- Cache is cleared at the end of a session or when explicitly requested.
- If memory limits are reached, the least recently used objects are evicted (with a warning).
