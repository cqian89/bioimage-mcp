# Phase 09 Research Notes: SciPy Spatial + Signal Integration

## Integration Pattern (Reuse)

- Follow the Phase 08 approach: a composite `ScipyAdapter` routes by `fn_id` prefix to sub-adapters.
- Prefer curated wrappers (stable I/O + predictable outputs) over exposing raw `scipy.spatial` / `scipy.signal` functions dynamically.

## Artifact I/O Patterns

- Tables: load points/signals via `PandasAdapterForRegistry._load_table()` and select numeric columns.
- JSON-like outputs: write as `NativeOutputRef` JSON using `ScipyNdimageAdapter._save_json()`.
- Session-persistent objects: store `cKDTree` objects in `OBJECT_CACHE` under `obj://...` URIs and return `ObjectRef`.

## New IOPatterns Needed

- `TABLE_TO_OBJECT`: build an in-memory object from a TableRef (KDTree build).
- `OBJECT_AND_TABLE_TO_JSON`: query an in-memory object using a TableRef and return JSON (KDTree query).
