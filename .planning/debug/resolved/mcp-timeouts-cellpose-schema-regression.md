---
status: resolved
trigger: "Investigate issue: mcp-timeouts-cellpose-schema-regression"
created: 2026-01-24T00:00:00Z
updated: 2026-01-24T00:36:00Z
---

## Current Focus

hypothesis: dynamic discovery appends duplicate fn_ids that override manifest-defined schemas, causing empty params_schema for cellpose models.
test: run unit tests covering loader merge and confirm manifest schema preserved on duplicate fn_id.
expecting: loader keeps manifest params_schema and skips duplicate dynamic function; new dynamic fn_ids still added.
next_action: archive debug session file.

## Symptoms

expected: describe with ~8 fn_ids returns promptly; cellpose.models.CellposeModel returns non-empty params_schema from manifest; list children navigation does not loop; run for base.io.bioimage.load returns artifacts without client timeout.
actual: describe with ~8 fn_ids times out (-32001); cellpose.models.CellposeModel params_schema becomes {}; list reports has_children true but listing returns itself/empty (loop); run for base.io.bioimage.load times out on first calls.
errors: McpError: MCP error -32001: Request timed out for describe/run; empty schema and loop for cellpose.
reproduction: cold-cache server start; call MCP describe with array of ~8 fn_ids; list cellpose hierarchy around cellpose.models.CellposeModel; call run for base.io.bioimage.load twice back-to-back.
started: after out-of-process dynamic discovery introduced; bisect indicates a7deade and cellpose meta.list in 7142664 enable regression.

## Eliminated

## Evidence

- timestamp: 2026-01-24T00:02:00Z
  checked: src/bioimage_mcp/registry/loader.py dynamic discovery handling
  found: discovered functions are appended to manifest.functions unconditionally (manifest.functions.append(function)) without deduping existing fn_id entries
  implication: discovered stubs can overwrite explicit manifest definitions during indexing when fn_id conflicts (params_schema loss).
- timestamp: 2026-01-24T00:03:00Z
  checked: src/bioimage_mcp/registry/index.py list_children
  found: if resolved node.type == "function", list_children returns [node] regardless of children (nodes = [node])
  implication: nodes that are both functions and parents yield a self-loop for list navigation despite has_children true.
- timestamp: 2026-01-24T00:04:00Z
  checked: src/bioimage_mcp/api/discovery.py describe_function
  found: when fn_ids is provided, describe_function loops sequentially and each fn_id path calls load_manifests(config.tool_manifest_roots)
  implication: batch describe triggers repeated manifest scanning and cache I/O per fn_id, multiplying latency in cold-cache scenarios.
- timestamp: 2026-01-24T00:06:00Z
  checked: tools/base/bioimage_mcp_base/ops/io.py
  found: load() imports bioio inside function but base module imports numpy/pandas at module load; no obvious dynamic discovery here
  implication: base.io.bioimage.load timeout likely dominated by worker startup/import overhead or repeated manifest discovery rather than function logic.
- timestamp: 2026-01-24T00:08:00Z
  checked: src/bioimage_mcp/api/execution.py
  found: load_manifests called in _get_input_storage_requirements, _get_function_metadata, and _get_function_ports on run path
  implication: run workflows may re-scan manifests multiple times per request; caching per request could reduce startup latency.
- timestamp: 2026-01-24T00:09:00Z
  checked: tools/cellpose/bioimage_mcp_cellpose/entrypoint.py handle_meta_list
  found: meta.list returns only fn_id/name/summary entries (no parameters), so discovery creates empty params_schema
  implication: when these discovered entries overwrite manifest-defined functions, params_schema becomes {} for cellpose.models.CellposeModel.
- timestamp: 2026-01-24T00:30:00Z
  checked: src/bioimage_mcp/registry/loader.py dynamic discovery merge
  found: added existing_fn_ids guard to skip discovered functions when manifest already defines fn_id
  implication: manifest params_schema should no longer be replaced by empty discovered schema.
- timestamp: 2026-01-24T00:35:00Z
  checked: pytest tests/unit/registry/test_loader_dynamic_integration.py
  found: 3 passed
  implication: loader merge regression test covers manifest schema precedence.

## Resolution

root_cause: "Dynamic discovery appends duplicate fn_ids that overwrite manifest definitions, replacing manifest params_schema with empty schemas from meta.list for Cellpose."
fix: "Skip dynamically discovered functions when the manifest already defines the same fn_id; add regression test to enforce manifest schema precedence."
verification: "pytest tests/unit/registry/test_loader_dynamic_integration.py (3 passed)"
files_changed:
  - src/bioimage_mcp/registry/loader.py
  - tests/unit/registry/test_loader_dynamic_integration.py
