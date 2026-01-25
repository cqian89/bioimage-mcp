# Phase 6: Infrastructure & N-D Foundation - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the Scipy dynamic adapter and enable core image processing filters with native dimension preservation. Focus on `scipy.ndimage` infrastructure, dynamic discovery, and memory-safe execution patterns.

</domain>

<decisions>
## Implementation Decisions

### Discovery Strategy
- **Scope:** Expose all public functions in `scipy.ndimage` *except* those in a blacklist.
- **Safety:** Allow utility functions even if they don't take an image as the first argument.
- **Documentation:** Parse `numpydoc` to generate rich JSON schemas (params/returns).
- **Configuration:** Define the blacklist in an external configuration file (YAML/JSON).
- **Deprecated:** Automatically exclude functions marked as deprecated.
- **Aliases:** Expose all aliases (e.g., if a function is available at two paths, expose both) rather than deduping.
- **Stale Config:** If blacklist mentions a missing function, ignore it (log warning/silent) rather than crashing.
- **Architecture:** Build a **Generic Scipy Adapter** structure (extensible to `scipy.stats` etc.), not just hardcoded for `ndimage`.

### Tool Naming Convention
- **Format:** Dot + Snake Case (e.g., `base.scipy.ndimage.gaussian_filter`).
- **Prefix:** Auto-detect the root prefix (e.g., `base`) from the tool pack environment/manifest.
- **Display Name:** Use the raw ID (e.g., `base.scipy.ndimage.gaussian_filter`) for the UI display name.

### Argument Mapping
- **Auxiliary Arrays:** Support both **Inline JSON** (lists) and **Artifact references** for array arguments (like structuring elements).
- **Dtypes:** Map `dtype` arguments to a **Strict Enum** in the schema (e.g., "float32", "uint8") rather than open strings.
- **Callables:** **Full implementation** required. Must support passing callables (e.g., `callback`, `footprint`) safely, likely via resolving string references to known functions.
- **Unmappable Types:** If an argument has a type that cannot be mapped/supported, **exclude that specific argument** from the schema but keep the tool.

### Output Behavior
- **Return Format:** **Context Dependent** — return Image artifacts for array results, JSON for scalar results.
- **In-Place:** Always **Force New Artifact**. Do not allow modifying input artifacts in-place (even if Scipy supports `output=input`).
- **Precision:** **Allow Float64** (Native Scipy default). Do not strictly enforce Float32 if Scipy returns Float64 (overrides generic roadmap heuristic GEN-03 for flexibility).
- **Metadata:** **Rely on I/O**. The adapter should trust the underlying I/O library (`bioio`) to handle metadata/pixel-size preservation, rather than explicit copy logic.
- **Channels:** **Treat C as Spatial**. Apply filters across all dimensions (including channels) by default, matching Scipy's native N-D behavior.

</decisions>

<specifics>
## Specific Ideas

- **Artifact Naming:** "Artifact ref_id must follow convention established in other packages of the project." (Researcher must investigate existing patterns in `tools/` or `src/bioimage_mcp/artifacts`).
- **Callable Implementation:** User emphasized "full implementation" for callables. This likely requires a registry or safe resolution mechanism for function strings.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-infrastructure-n-d-foundation*
*Context gathered: 2026-01-25*
