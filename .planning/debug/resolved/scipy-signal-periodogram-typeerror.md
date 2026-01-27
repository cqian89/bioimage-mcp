---
status: investigating
trigger: "Investigate the 'TypeError: string indices must be integers, not 'str'' failure in 'base.scipy.signal.periodogram'. The error occurs during execution."
created: 2026-01-26T00:00:00Z
updated: 2026-01-26T00:00:00Z
---

## Current Focus

hypothesis: confirmed: TableRef metadata shape incompatible with TableRef model; fix in pandas _save_table and artifact store normalization resolves
test: rerun periodogram workflow with file URI input
expecting: success with TableRef metadata columns list of dicts and row_count
next_action: remove debug logging from scipy_signal adapter and document root cause/fix

## Symptoms

expected: periodogram execution completes without TypeError
actual: TypeError: string indices must be integers, not 'str'
errors: TypeError: string indices must be integers, not 'str'
reproduction: run base.scipy.signal.periodogram tool
started: unknown

## Eliminated

## Evidence

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/scipy_signal.py
  found: periodogram/welch path reads input via input_dict = dict(inputs) and accepts art_ref as dict/object only
  implication: any string artifact (URI/path) will pass through unvalidated and be treated as non-bioimage

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/loader.py (IOPattern.ANY_TO_TABLE)
  found: ANY_TO_TABLE allows input artifact types TableRef/BioImageRef/ObjectRef
  implication: callers may send serialized refs or URIs; adapter must handle or reject clearly

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/pandas.py::_load_table
  found: table loader handles dicts and objects with uri/path, but has no explicit string handling
  implication: string inputs are not normalized and can trigger type errors in downstream access

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/pandas.py::_load_table
  found: _load_table now explicitly handles string artifacts by treating them as uri/path
  implication: TypeError is unlikely to be inside pandas _load_table; failure likely occurs before reaching this loader

- timestamp: 2026-01-26T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/scipy_signal.py
  found: periodogram/welch branch passes art_ref directly into PandasAdapterForRegistry()._load_table
  implication: any TypeError from string indexing must occur upstream of _load_table or in a different path

- timestamp: 2026-01-26T00:00:00Z
  checked: tools/base/bioimage_mcp_base/dynamic_dispatch.py::_convert_inputs_to_artifacts
  found: file:// or mem:// URI strings are treated as ref_id strings if length <= 64; they are passed through unchanged (not wrapped), and lists of strings are normalized to {"ref_id": v}
  implication: a file:// URI string with length <= 64 may be treated as ref_id, not as uri; downstream may try to resolve it as ref_id and fail or index it as dict

- timestamp: 2026-01-26T00:00:00Z
  checked: tests/unit/registry/dynamic/test_scipy_signal_execute.py::test_scipy_signal_periodogram_string_input
  found: direct adapter execution handles string URI when PandasAdapterForRegistry._load_table supports string
  implication: failure likely occurs before adapter execution (dynamic dispatch input conversion) or elsewhere in tool pack

- timestamp: 2026-01-26T00:00:00Z
  checked: local attempt to run ExecutionService via python
  found: ModuleNotFoundError for bioimage_mcp.api.config
  implication: use MCP run tool or correct import path for Config

- timestamp: 2026-01-26T00:00:00Z
  checked: local attempt to run ExecutionService via python using load_config
  found: Config object has no session_store attribute
  implication: ExecutionService initialization requires SessionManager differently; need alternate test harness or use MCP run tool

- timestamp: 2026-01-26T00:00:00Z
  checked: run_workflow with file URI input after adding debug logging
  found: stack trace shows TypeError in ArtifactStore._reconstruct_ref when accessing meta["columns"] for TableRef
  implication: metadata for TableRef is a string, not dict; string indexing error originates in artifact store, not periodogram adapter

- timestamp: 2026-01-26T00:00:00Z
  checked: run_workflow after adjusting _reconstruct_ref columns handling
  found: TableRef validation error: metadata.columns expects list[ColumnMetadata], metadata.row_count missing
  implication: TableRef requires structured metadata; current TableRef outputs provide metadata with columns as list[str] and missing row_count

## Resolution

root_cause: "ArtifactStore._reconstruct_ref assumes TableRef metadata.columns is a list of dicts (ColumnMetadata). PandasAdapterForRegistry._save_table produced metadata.columns as list[str] and omitted row_count, so TableRef reconstruction indexed strings and raised TypeError."
fix: "Pandas table outputs now emit structured column metadata (name + dtype) and row_count; ArtifactStore normalizes legacy columns lists to ColumnMetadata with row_count."
verification: "ExecutionService run_workflow for base.scipy.signal.periodogram with input=file://... succeeds and returns TableRef with metadata.columns as dicts and row_count."
files_changed:
  - src/bioimage_mcp/registry/dynamic/adapters/pandas.py
  - src/bioimage_mcp/artifacts/store.py
