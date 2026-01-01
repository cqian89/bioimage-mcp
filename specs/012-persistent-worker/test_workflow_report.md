# Test Workflow Report: Bioimage-MCP Validation Issues

## Overview
This report summarizes the technical issues encountered during the end-to-end validation of the `bioimage-mcp` server.

## 1. Tool Discovery & Navigation
- **Pagination Complexity**: The `list_tools` and `search_functions` tools are highly paginated, often returning empty lists while providing a `next_cursor`. This makes exhaustive discovery brittle and slow.
- **Inconsistent Search Results**: Tools that appeared in early listings (e.g., `base.bioio.export`) frequently disappeared from subsequent searches or package listings, requiring manual cursor tracking or redundant queries.

## 2. Image Loading & Artifact Handling
- **Direct Loading Failures**: `BioImage` (used by most analysis tools) threw `NotImplementedError` when attempting to read standard `.tif` files from the filesystem.
- **Strict Extension Requirements**: Tools like `phasor_from_flim` perform hard checks for `.tif` or `.tiff` extensions. This is incompatible with the default artifact store which uses content-addressed hashes (no extensions), requiring manual copies to temporary local paths.
- **Export Artifact Constraints**: `bioimage-mcp_export_artifact` failed with `No allowed write roots configured` for allowlisted directories, forcing the use of `bash` to move files out of the artifact store for tool compatibility.

## 3. Phasor Analysis Workflow
- **Dimension Order Conflicts**: The `phasor_from_flim` tool consistently failed with `Invalid dimension_order PTCYX`. 
- **Failed Remediation**: Even after using `base.xarray.transpose` to force the axes to `TCZYX`, the internal reader or tool logic continued to report `PTCYX`, suggesting a possible injection of a 'Position' (P) dimension by the underlying `BioIO` reader that the tool cannot handle.
- **Parameter Mapping**: `base.phasorpy.phasor.phasor_from_signal` failed with missing positional argument errors even when the `signal` input was correctly provided via `BioImageRef`.

## 4. Environment & Dependency Errors
- **Cellpose environment**: `cellpose.segment` is currently non-functional due to a dependency error: `cannot import name 'UTC' from 'datetime'`. This indicates an incompatibility in the Python 3.10 environment provided for the cellpose pack.

## 5. Tool Parameter Mismatches
- **Inaccurate Introspection**: `describe_function` for `base.skimage.filters.threshold_otsu` suggested an input named `input`, while the schema and runtime validation expected `image`, leading to `Workflow validation failed` errors.

## Conclusion
The core server connectivity and basic image manipulation (mean projection, transposition) are functional. However, the high-level analysis pipelines (Phasor FLIM and Cellpose Segmentation) are currently blocked by a combination of strict I/O requirements, dimension handling bugs, and environment misconfigurations.

---

## Investigation Results (2026-01-01)

### Issue 1: Tool Discovery & Navigation

**Root Causes Identified:**

1. **Hierarchy Shadowing Bug** (`src/bioimage_mcp/registry/index.py:461-464`):
   - When `flatten=True`, the `_collect_functions` method returns immediately upon finding a `function` node, skipping any nested children.
   - Functions with fn_ids that are prefixes of others (e.g., `base.noise` vs `base.noise.gaussian`) cause child functions to be hidden.

2. **Offset Pagination Instability** (`src/bioimage_mcp/api/discovery.py:137-240`):
   - `search_functions` uses offset-based pagination but re-fetches and re-ranks the entire registry on every page request.
   - Any registry changes or non-deterministic ranking causes items to shift between pages.

3. **Path Collision/Deduping** (`src/bioimage_mcp/api/discovery.py:111`):
   - Nodes are deduped by `full_path`, causing silent drops when different `fn_id`s map to the same virtual path.

4. **Performance**: Both tools fetch the entire registry into memory on every call.

**Planned Fixes:**
- [ ] Fix hierarchy shadowing: modify `_collect_functions` to continue traversing children even for function nodes
- [ ] Convert search to cursor-based pagination using `fn_id` as stable cursor key
- [ ] Add `installed` status filter to exclude unavailable tools from discovery
- [ ] Add lazy loading with database-level pagination

---

### Issue 2: Image Loading & Artifact Handling

**Root Causes Identified:**

1. **Extension-less Artifacts** (`src/bioimage_mcp/artifacts/store.py:100`):
   - `_artifact_path(ref_id)` returns `objects/UUID_HEX` without file extensions.
   - Metadata (including format) is in SQLite but not reflected in filesystem.

2. **Strict Suffix Checks** (`tools/base/bioimage_mcp_base/transforms.py:193-194`):
   - `_load_flim_data` explicitly fails if suffix is not `.tif`/`.tiff` and format is not set.
   - Code: `if not fmt and path.suffix.lower() not in {".tif", ".tiff"}: raise ValueError`

3. **Export Allowlist Empty by Default** (`src/bioimage_mcp/config/schema.py:54`):
   - `fs_allowlist_write: list[Path] = Field(default_factory=list)` — empty by default.
   - `assert_path_allowed("write", ...)` in `fs_policy.py:46-48` raises `PermissionError` when no allowlist is configured.

4. **Safe Pattern Exists but Not Used** (`tools/base/bioimage_mcp_base/utils.py:27`):
   - `load_image_fallback` handles extension-less files by detecting `has_no_suffix` and using explicit readers.
   - But `transforms.py` calls `BioImage(str(path))` directly instead.

**Planned Fixes:**
- [ ] Update `_load_flim_data` to use `load_image_fallback` or `load_image_with_warnings` from `utils.py`
- [ ] Relax extension checks: use format metadata when available, infer from content for extension-less files
- [ ] Document and auto-populate `fs_allowlist_write` with `artifact_store_root` in config loader
- [ ] Consider storing artifacts with `.ome.tiff` extension for tool compatibility

---

### Issue 3: Phasor Dimension Order Conflicts (PTCYX)

**Root Causes Identified:**

1. **Hardcoded `P` Dimension Injection** (`tools/base/bioimage_mcp_base/transforms.py:424`):
   - When stacking G/S phasor maps, the code checks `if "C" not in output_axes` to use `C` as the stack dimension.
   - If `C` exists, it defaults to prepending `P` (for "Phasor" or "Position"): `stack_axes = f"P{output_axes}"`

2. **OME-TIFF Rejects Non-Standard Dimensions**:
   - `OmeTiffWriter.save` only supports `{T, C, Z, Y, X}`.
   - `P` is not a valid OME dimension character, causing `Invalid dimension_order PTCYX` errors.

3. **Transpose Cannot Fix** (`src/bioimage_mcp/registry/dynamic/adapters/xarray.py:125`):
   - Transpose changes order of existing dimensions, but `P` is injected *after* phasor computation inside `phasor_from_flim`.
   - The `XarrayAdapter` derives `dim_order` from xarray dimensions post-injection.

**Planned Fixes:**
- [ ] Change stacking logic: use `S` (Sample) or repurpose `Z` instead of injecting `P`
- [ ] Alternative: Always merge G/S into an existing dimension (e.g., expand `C` with "G" and "S" channel names)
- [ ] Add validation before calling `OmeTiffWriter` to catch invalid dimension characters early
- [ ] Update `_write_ome_tiff` to sanitize dimension orders, mapping `P` to `C` or `Z` with a warning

---

### Issue 4: Cellpose UTC Import Error

**Root Cause Identified:**

1. **Python Version Mismatch**:
   - The `datetime.UTC` constant was added in **Python 3.11** (PEP 615).
   - `envs/bioimage-mcp-cellpose.yaml:13` pins `python=3.11`, BUT the manifest at `tools/cellpose/manifest.yaml:9` declares `python_version: "3.10"`.
   - If the runtime honors the manifest over the environment YAML, an older Python is used.

2. **Dependency Chain**:
   - Either `cellpose` or a transitive dependency imports `from datetime import UTC`.
   - This fails on Python < 3.11 with `cannot import name 'UTC' from 'datetime'`.

**Planned Fixes:**
- [ ] Align `manifest.yaml` python_version to `3.11` to match the conda env
- [ ] Add a contract test verifying manifest `python_version` matches `envs/*.yaml`
- [ ] Consider upgrading to Python 3.12+ for consistency with core server

---

### Issue 5: threshold_otsu Parameter Mismatch

**Root Cause Identified:**

1. **Introspection vs Manifest Divergence**:
   - `describe_function` for dynamically adapted scikit-image functions calls `meta.describe` if available.
   - The `SkimageAdapter` introspects `skimage.filters.threshold_otsu` signature: first param is named `image`.
   - BUT: The adapter's `_normalize_inputs` method (`skimage.py:124`) assigns `name = "image" if idx == 0`.

2. **No Explicit Input Schema in Manifest**:
   - Dynamic functions don't have explicit `inputs` in the manifest.
   - The `describe_function` response includes `inputs` from the manifest's function definition (line 277-284), but for skimage-adapted functions these are inferred, not declared.

3. **Schema/Signature Mismatch Reporting**:
   - If `meta.describe` returns a schema with different parameter names than what the execution path expects, validation fails.

**Planned Fixes:**
- [ ] Add explicit `inputs` definitions to overlay manifests for commonly-used skimage functions
- [ ] Enhance `SkimageAdapter` to populate the `inputs` section based on introspection
- [ ] Add contract tests comparing `describe_function` output against actual function signatures

---

## Priority Matrix

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| Phasor PTCYX dimension | High | Medium | P0 |
| Artifact extension handling | High | Medium | P0 |
| Cellpose Python version | Medium | Low | P1 |
| Export allowlist defaults | Medium | Low | P1 |
| Discovery pagination bugs | Medium | High | P2 |
| threshold_otsu schema | Low | Low | P2 |

---

## Recommended Fix Order

1. **P0-A**: Fix phasor stacking to use `C` with channel names "G"/"S" instead of injecting `P`
2. **P0-B**: Update `_load_flim_data` to use `load_image_fallback` for extension-less artifacts
3. **P1-A**: Align cellpose manifest `python_version` to `3.11`
4. **P1-B**: Auto-populate `fs_allowlist_write` with artifact store root in config loader
5. **P2**: Fix discovery pagination (larger refactor)

---

## Issue 6: phasor_from_flim Still Present Despite Spec 011 Removal Plan

**Finding:**

The `phasor_from_flim` and `phasor_calibrate` functions still exist in the codebase despite spec 011 (Wrapper Consolidation) explicitly listing them for removal:

```
# From specs/011-wrapper-consolidation/quickstart.md:63
| Phasor | phasor_from_flim, phasor_calibrate (convert to direct phasorpy calls) |
```

**Current State:**
- `tools/base/manifest.yaml:279-302` - Both functions still registered
- `tools/base/bioimage_mcp_base/transforms.py:374-473` - Full implementation still present
- `tools/base/bioimage_mcp_base/entrypoint.py:44-45` - Dispatch mapping still active
- `tools/base/bioimage_mcp_base/wrapper/` - Directory was deleted (T038 completed)

**Spec 011 Task Status (from tasks.md):**
- `[X] T037` - Remove all legacy `base.wrapper.*` tools (completed)
- `[X] T038` - Delete `tools/base/bioimage_mcp_base/wrapper/` directory (completed)

**Root Cause:**

The phasor functions were **never `base.wrapper.*` functions** - they were always `base.bioimage_mcp_base.transforms.*` functions. The spec 011 quickstart table listed them for removal, but:

1. The task T037 only targeted `base.wrapper.*` namespace (which is now gone)
2. The phasor functions live in `transforms.py`, not in the deleted `wrapper/` directory
3. There was no explicit task to remove `phasor_from_flim` from `transforms.py`

**Spec 011's Intended Migration:**

Per `specs/011-wrapper-consolidation/quickstart.md:63`:
> Phasor | phasor_from_flim, phasor_calibrate (convert to direct phasorpy calls)

The intention was to:
1. Remove the wrapper functions
2. Expose `phasorpy.phasor.phasor_from_signal` directly via dynamic discovery

**What Actually Happened:**
- The `wrapper/` directory was deleted
- The phasor functions in `transforms.py` were NOT touched
- No direct `phasorpy.*` exposure was added to dynamic discovery

**Recommended Actions:**

1. **Option A (Complete Removal):** Delete phasor functions from `transforms.py` and add `phasorpy` to dynamic discovery
2. **Option B (Keep with Fixes):** Keep the wrapper but fix the PTCYX dimension issue and extension handling
3. **Option C (Deprecation Path):** Mark `phasor_from_flim` as deprecated, add dynamic `phasorpy.*` exposure, maintain both during transition

### Decision: Option A (Complete Removal) ✅

**Rationale:** This aligns with spec 011's original intent and the Zero-Wrapper Architecture. The custom phasor wrappers add maintenance burden and introduce bugs (PTCYX, extension handling) that would not exist with direct library exposure.

**Implementation Tasks:**

1. [ ] Remove `phasor_from_flim` and `phasor_calibrate` from `tools/base/manifest.yaml`
2. [ ] Delete phasor functions from `tools/base/bioimage_mcp_base/transforms.py`
3. [ ] Remove dispatch mappings from `tools/base/bioimage_mcp_base/entrypoint.py`
4. [ ] Add `phasorpy` to dynamic discovery configuration (similar to skimage adapter)
5. [ ] Create `PhasorpyAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`
6. [ ] Register `phasorpy.phasor.phasor_from_signal`, `phasorpy.phasor.phasor_to_polar`, etc.
7. [ ] Update tests to use direct phasorpy function calls
8. [ ] Update documentation in `docs/tutorials/flim_phasor.md`

**Impact on Current Report:**

With Option A chosen:
- **Issue #3 (PTCYX dimension):** Becomes moot - direct phasorpy calls don't inject `P` dimension
- **Issue #2 (extension handling):** Still relevant for other tools, but no longer blocks phasor workflows
- **P0-A fix:** No longer needed - remove from priority list
- **P0-B fix:** Still needed for general artifact handling

**Revised Priority Matrix:**

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| Phasor wrapper removal (Option A) | High | Medium | P0 |
| Artifact extension handling | High | Medium | P0 |
| Cellpose Python version | Medium | Low | P1 |
| Export allowlist defaults | Medium | Low | P1 |
| Discovery pagination bugs | Medium | High | P2 |
| threshold_otsu schema | Low | Low | P2 |
