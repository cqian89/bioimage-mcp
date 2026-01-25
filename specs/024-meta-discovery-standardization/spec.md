# Dynamic Discovery Protocol Specification (meta.list & meta.describe)

**Status**: Canonical Protocol  
**Phase**: 05.1-research-dynamic-discovery  
**Scope**: Tool-pack discovery protocol between server and tool environments.

This document defines the standard protocol for dynamic function discovery in `bioimage-mcp`. Tool packs SHOULD implement these functions to support rich, automatic introspection of their scientific capabilities.

## Overview

The discovery protocol consists of two functions:
1. `meta.list`: Discovers available functions and their basic metadata.
2. `meta.describe`: Extracts detailed parameter schemas (JSON Schema) for a specific function.

These functions are called by the core server via the standard subprocess entrypoint protocol (JSON/NDJSON over stdin/stdout).

---

## 1. `meta.list` Protocol

### Request
```json
{
  "fn_id": "meta.list",
  "command": "execute",
  "params": {},
  "inputs": {},
  "ordinal": 0
}
```

### Success Response
Tool packs should return a list of function metadata.

```json
{
  "ok": true,
  "result": {
    "functions": [
      {
        "fn_id": "module.function_name",
        "name": "function_name",
        "summary": "Short one-line description of the function.",
        "module": "optional.module.path",
        "io_pattern": "image_to_image"
      }
    ],
    "tool_version": "1.2.3",
    "introspection_source": "module_scan"
  }
}
```

#### Minimal Function Entry Keys:
| Key | Type | Description |
|-----|------|-------------|
| `fn_id` | string | Unique identifier for the function (e.g. `scipy.ndimage.gaussian_filter`). |
| `name` | string | Display name of the function. |
| `summary` | string | Short description for search results. |

#### Recommended Keys (Optional):
| Key | Type | Description |
|-----|------|-------------|
| `module` | string | The Python module containing the function. |
| `io_pattern` | string | Must match `IOPattern` enum values (e.g. `image_to_image`, `image_to_table`). |
| `description`| string | Full docstring or detailed description. |
| `tags` | list[str]| Searchable keywords. |

---

## 2. `meta.describe` Protocol

### Request
```json
{
  "fn_id": "meta.describe",
  "command": "execute",
  "params": {
    "target_fn": "module.function_name"
  },
  "inputs": {},
  "ordinal": 0
}
```

### Success Response
Tool packs should return the JSON Schema for the function's parameters.

```json
{
  "ok": true,
  "result": {
    "params_schema": {
      "type": "object",
      "properties": {
        "sigma": {
          "type": "number",
          "default": 1.0,
          "description": "Standard deviation for Gaussian kernel."
        }
      },
      "required": ["sigma"]
    },
    "tool_version": "1.2.3",
    "introspection_source": "numpydoc"
  }
}
```

#### Response Keys:
| Key | Type | Description |
|-----|------|-------------|
| `ok` | boolean | Must be `true`. |
| `result.params_schema`| object | Valid JSON Schema (draft 7+) for the parameters. |
| `result.tool_version` | string | REQUIRED. The version of the underlying library (e.g. `scipy.__version__`). |
| `result.introspection_source`| string | REQUIRED. How the schema was derived (e.g. `numpydoc`, `python_api`, `manual`). |

### Error Response
Errors should provide a clear reason for failure.

```json
{
  "ok": false,
  "error": "Unknown function: module.missing_function"
}
```
*Note: `error` must be a string.*

---

## 3. Implementation Rules

### Naming and Prefixing
- **Tool packs SHOULD return library-level fn_ids** (e.g. `scipy.ndimage.gaussian_filter`).
- The server will automatically apply the environment prefix (e.g. `base.`) when indexing.
- Tool packs MAY return already-prefixed ids; the server must tolerate both.

### Version Semantics
- `tool_version` refers to the version of the scientific library being introspected, NOT the version of the `bioimage-mcp` adapter.
- The server uses `tool_version` to invalidate the `SchemaCache`.

### Backwards Compatibility
- **Server**: Should be lenient. If `tool_version` or `introspection_source` is missing, use defaults and log a warning.
- **Tool Packs**: Should be strict. Always provide required fields to ensure reliable server-side caching and search.

### Artifact Ports
- `params_schema` MUST NOT include keys that are defined as I/O ports (inputs/outputs) in the manifest.
- Introspection logic should filter out common artifact parameter names (e.g. `image`, `input`, `output`, `df`).
