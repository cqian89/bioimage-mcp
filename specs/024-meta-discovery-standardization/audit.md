# Tool-Pack Compliance Audit Matrix (Dynamic Discovery)

This document audits the current implementation of dynamic discovery protocols (`meta.list` and `meta.describe`) across all tool packs.

## Compliance Matrix

| Tool Pack | meta.list implemented | meta.describe implemented | includes tool_version / introspection_source | error shape is string | Notes / Action Items |
|-----------|-----------------------|---------------------------|---------------------------------------------|-----------------------|----------------------|
| `tools.base` | No | Yes | Yes (v0.2.0) | Yes | Action: Add `meta.list` handler to entrypoint for full subprocess discovery fallback. |
| `tools.cellpose` | Yes | Yes | Yes | Yes | Compliance: GOOD. Action: Ensure `meta.list` results are cached. |
| `tools.trackpy` | Yes | Yes | No (`tool_version` missing) | No (returns dict) | Action: Update `handle_meta_describe` to include library version and return string errors. |
| `tools.tttrlib` | No | No | No | N/A | Action: Implement discovery for `tttrlib` to support requirements. |

## Gap Analysis & Action Items

### 1. Unified `meta.list` Support
While `tools.base` relies on its manifest, providing a `meta.list` handler enables the server to verify the environment matches the manifest.
- **Action**: Implement standard module scanner for `tools.base`.

### 2. Missing Metadata in `trackpy`
The `trackpy` implementation returns rich schemas via `numpydoc` but omits the required `tool_version` and uses a non-standard error shape.
- **Action**: Align `trackpy` entrypoint with the canonical protocol.

### 3. Missing `tttrlib` Discovery
`tttrlib` functions are currently manual entries in the manifest.
- **Action**: Add dynamic discovery to `tools.tttrlib` to reduce boilerplate.

### 4. Shared Utilities
Much of the logic in `trackpy`'s `introspect.py` is generally useful.
- **Action**: Move common introspection logic to `bioimage_mcp.runtimes.introspect` for all tool packs to use.
