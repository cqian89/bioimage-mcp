Introspection Engine Proposal (Aligned with bioimage-mcp)

This refines the plan to match the current MCP API, registry layout, and the
meta.list/meta.describe protocol. Backward compatibility is explicitly out of
scope; the plan favors consolidation and deletion of duplicate paths.

---

0) Goals and non-goals

Goals
- Automatically derive params_schema (JSON Schema) for callables in tool-pack
  environments.
- Follow precedence: signature defines shape; type hints define types; docstrings
  fill missing types and descriptions.
- Keep params_schema separate from artifact ports (inputs/outputs) per
  specs/024-meta-discovery-standardization/spec.md.
- Unify introspection logic across adapter discovery and meta.describe.
- Provide deterministic caching with strong invalidation (tool_version + env
  lock hash + engine version).
- Provide a patch/override system grounded in existing manifest overlays.

Non-goals (v1)
- Semantic array typing (dims/units/axes) beyond FunctionHints.
- Perfect handling of runtime-generated signatures without imports.
- Maintaining backward compatibility with legacy fn_id or cache shapes.

---

1) Codebase reality and constraints (must align)

- MCP surface is list/search/describe/run in `src/bioimage_mcp/api/server.py`.
- Discovery is `DiscoveryService` + `RegistryIndex` (SQLite) and `ToolIndex`
  hierarchy in `src/bioimage_mcp/registry/index.py`.
- Dynamic discovery runs in-process via adapters in
  `src/bioimage_mcp/registry/dynamic/` and out-of-process via meta.list/meta.describe
  per `specs/024-meta-discovery-standardization/spec.md`.
- params_schema must not include artifact ports; the core server filters them in
  `DiscoveryService.describe_function` (T036/T109).
- Artifact I/O mapping uses `IOPattern` and `FunctionHints`
  (`src/bioimage_mcp/registry/dynamic/models.py`, `src/bioimage_mcp/api/schemas.py`).
- Tool manifests support overlays and param overrides (`function_overlays` in
  `src/bioimage_mcp/registry/manifest_schema.py`).
- Caching is fragmented: SQLite schema_cache in `RegistryIndex` and JSON file
  cache in `src/bioimage_mcp/registry/schema_cache.py`.

---

2) High-level architecture (control plane + tool-pack runtime)

Control plane (core server)
- Owns list/search/describe/run.
- Stores tools/functions/params_schema in SQLite.
- Calls meta.list/meta.describe through tool-pack entrypoints for cross-env
  discovery and schema enrichment.
- Filters out artifact ports before returning params_schema to clients.

Tool-pack runtime (per-env entrypoint)
- Implements meta.list/meta.describe and the actual tool functions.
- Hosts the introspection engine (AST-first with guarded runtime fallback).
- Returns params_schema + tool_version + introspection_source as required by
  spec 024.

Key consolidation: a single introspection engine module is shared by adapter
discovery and meta.describe.

---

3) Function identity and stability

Current spec (must follow)
- Tool packs return library-level fn_ids.
- Server applies environment prefix if missing (spec 024).
- fn_id is dot-delimited and used for list hierarchy.

Proposal
- Keep dot-delimited fn_id for ToolIndex and list/search/describe.
- Use full module paths for module metadata (avoid truncating to last segment).
- Add a callable_fingerprint separate from fn_id (signature hash + source
  location + module mtime).
- Cache invalidation uses tool_version (library version) plus env lock hash and
  engine version.

---

4) Data model (normalized spec mapped to existing models)

Introduce a normalized IR but map to existing types:

FunctionSpec -> FunctionMetadata + Function
- identity: fn_id, module, qualname, tool_version, callable_fingerprint
- doc: summary, description
- params: list[ParamSpec]
- returns: ReturnSpec
- io_pattern: IOPattern
- hints: FunctionHints (inputs/outputs/LLM guidance)
- input_mode: path/numpy/xarray (existing Function.input_mode)
- diagnostics: list[Diagnostic]

ParamSpec -> ParameterSchema -> params_schema
- name, kind, required, default, type_hint, doc_type, description, enum,
  constraints
- special_handling: artifact_ref | file_handle | callable_ref

ReturnSpec is used for hints/diagnostics only (run outputs are artifact ports).

This IR is the sole point for patches and schema emission.

---

5) Introspection pipeline (AST-first, runtime fallback)

Primary (AST-first)
- Use Griffe to load modules from site-packages without importing.
- Resolve by qualname and extract signature + annotations.
- Parse docstrings using docstring_parser (Google/NumPy/Sphinx) with numpydoc as
  fallback.
- Precedence: signature shape -> type hints -> docstring types/description.

Fallback (guarded)
- If AST info is too generic (*args/**kwargs only), missing annotations, or
  docstrings absent, optionally import and use
  inspect.signature(inspect.unwrap(obj)).
- Record diagnostics: RUNTIME_SIGNATURE_USED, DOC_MISSING_FOR_PARAM,
  DOC_PARAM_NOT_IN_SIGNATURE, TYPE_CONFLICT_DOC_VS_HINT.

This replaces both `registry/dynamic/introspection.py` and
`runtimes/introspect.py`.

---

6) Schema emission (Pydantic + JSON Schema)

- Build a Pydantic BaseModel from FunctionSpec for runtime validation in the
  tool pack.
- Export JSON Schema for meta.describe (params_schema).
- Enforce params_schema shape:
  - type: object
  - properties + required
  - no artifact port keys

Type heuristics
- Preserve parameter-name inference from `runtimes/introspect.py` as the last
  resort.

---

7) Varargs/kwargs policy (align with current runtime)

Current behavior
- Both existing introspection paths skip *args/**kwargs.

Updated policy
- Continue skipping *args/**kwargs unless runtime is updated to translate
  args/kwargs explicitly.
- If **kwargs exists:
  - set top-level additionalProperties: true
  - parse "Other Parameters" docstring entries into optional fields
- Emit diagnostics to encourage overlays for ambiguous APIs.

---

8) Artifact and I/O mapping (no API shape change)

- Use IOPattern to define ports via `_map_io_pattern_to_ports` in
  `registry/loader.py`.
- Use FunctionHints for richer input/output constraints.
- Honor `Function.input_mode` for artifact resolution (path/numpy/xarray).
- Keep io_bridge in `registry/dynamic/io_bridge.py` as the cross-env
  materialization layer.

Introspection should set io_pattern/hints and never embed artifact ports into
params_schema.

---

9) Callable references and file handles

Callable parameters
- Represent callables as a discriminated object:
  - {kind: "tool_fn", fn_id: "..."}
  - {kind: "import_path", path: "pkg.mod:func"}
- Resolve in the tool-pack runtime prior to invocation.
- Emit a union schema for callable parameters.

File handles
- Prefer ArtifactRef/NativeOutputRef over raw paths.
- Input: resolve artifact to local path and open with requested mode.
- Output: create a temp artifact path, open handle, then return a
  NativeOutputRef.
- Returned handles are materialized into artifacts with diagnostics.

These require explicit runtime adapters in tool-pack execution (not present
today).

---

10) Caching and invalidation (consolidate)

Replace fragmented caches with a single SQLite schema_cache in RegistryIndex:
- Remove `registry/schema_cache.py` JSON cache.
- Store tool_version + callable_fingerprint + engine_version + module_mtime/hash
  + params_schema.
- Use env lock hash from `envs/<env_id>.lock.yml` to invalidate when deps change.

---

11) Overrides and patches (build on FunctionOverlay)

Use existing FunctionOverlay as the patch interface:
- description, tags, io_pattern, hints, params_override
- extend to:
  - rename params
  - drop params
  - mark artifact/file/callable handling
  - add enum/range/pattern constraints

Patch precedence
1) Built-in tool-pack overlays
2) Manifest function_overlays
3) User-provided overlays

Apply after normalization, before schema emission. Record PATCH_APPLIED
diagnostics.

---

12) Diagnostics and observability

- Diagnostics carried on FunctionSpec; optional debug mode can surface them in
  meta.describe.
- Required in meta.describe: tool_version and introspection_source (spec 024).
- Suggested introspection_source values: griffe_ast, python_runtime, numpydoc,
  manual.
- Core server maps fatal issues to StructuredError in describe/run responses.

---

13) Migration and consolidation plan (no backward compat)

Phase 1: Shared engine
- Add an `introspection_engine` module.
- Replace `registry/dynamic/introspection.py` and `runtimes/introspect.py`.

Phase 2: meta.list/meta.describe alignment
- Tool-pack entrypoints call the shared engine.
- Always return tool_version + introspection_source.

Phase 3: Cache consolidation
- Remove JSON SchemaCache; use RegistryIndex.schema_cache only.

Phase 4: Overlay consolidation
- Move adapter-specific patches into overlays or patch bundles.
- Remove ad-hoc adapter logic where possible.

Phase 5: fn_id + module cleanup
- Enforce full module paths in metadata.
- Keep dot-delimited library-level fn_id per spec 024.

---

14) Gaps, inconsistencies, risks (current state)

- Duplicate introspection paths (`registry/dynamic/introspection.py` vs
  `runtimes/introspect.py`).
- Fragmented caching (SQLite vs JSON file).
- fn_id truncation to last module segment in Introspector.
- Artifact parameter filtering happens in multiple places.
- Docstring parsing behavior differs between paths.
- Runtime import fallback can have side effects; must be opt-in per tool pack.

---

15) External patterns to emulate (LangChain and LlamaIndex)

LangChain
- StructuredTool and @tool: `libs/core/langchain_core/tools/structured.py`,
  `libs/core/langchain_core/tools/convert.py`
- Schema inference tests: `libs/core/tests/unit_tests/test_tools.py`

Example (LangChain, convert.py)
```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def search_api(query: str) -> str:
    """Search the API."""
    return "..."
```

LlamaIndex
- FunctionTool.from_defaults and ToolMetadata:
  `llama-index-core/llama_index/core/tools/function_tool.py`,
  `llama-index-core/llama_index/core/tools/types.py`
- MCP adapter:
  `llama-index-integrations/tools/llama-index-tools-mcp/llama_index/tools/mcp/base.py`

Example (LlamaIndex, tests)
```python
from llama_index.core.tools import FunctionTool

def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b

tool = FunctionTool.from_defaults(fn=multiply)
```

Alignment takeaways
- Pydantic BaseModel is the internal schema of record.
- Docstring summary is the tool description; parameter descriptions are parsed.
- Tools expect JSON Schema with required fields populated.
