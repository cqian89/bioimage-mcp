# Code Review: `020-add-xarray-functions`

## Scope

Reviewed `main...HEAD` on branch `020-add-xarray-functions`.

Key touched areas:
- xarray adapter + allowlists (`src/bioimage_mcp/registry/dynamic/adapters/xarray.py`, `src/bioimage_mcp/registry/dynamic/xarray_allowlists.py`)
- dynamic dispatch routing (`tools/base/bioimage_mcp_base/dynamic_dispatch.py`)
- removal of legacy `base.xarray.*` from base manifest (`tools/base/manifest.yaml`)
- new/updated xarray tests (`tests/unit/registry/test_xarray_*`, `tests/contract/test_xarray_functions.py`, `tests/integration/test_xarray_workflows.py`)

Compared behavior against `specs/020-add-xarray-functions/proposal.md`.

## Test Results

### Full test suite
Command: `pytest`

Result: **failed** (many failures).

Failures that appear directly attributable to the xarray changes in this branch:
- `tests/contract/test_axis_tools_schema.py`: expects legacy `base.xarray.{rename,squeeze,expand_dims,transpose}` to exist in `tools/base/manifest.yaml`.
  - This breaks because those entries were deleted in `tools/base/manifest.yaml:57`.
- `tests/contract/test_base_tools.py`: expects legacy `base.xarray.*` tools to exist in the base manifest.
- `tests/integration/test_artifact_export.py`: workflow calls `base.xarray.rename` and now fails with `Unknown or invalid xarray function ID`.
- `tests/integration/test_cross_env_dim_preservation.py`: calls `base.xarray.squeeze` and now fails.

There are also several failures that do **not** look related to the xarray changes (cellpose training/standalone, materialization scripts, missing `test_xr.ome.tiff`, etc.). I did not verify whether those are also failing on `main`.

### Smoke tests
Command: `pytest tests/smoke/ -v`

Result: **failed** (`3 failed, 19 passed, 1 skipped`).

All three failures were caused by missing legacy xarray tool IDs:
- `tests/smoke/test_smoke_basic.py`: `base.xarray.squeeze` fails.
- `tests/smoke/test_flim_phasor_live.py`: `base.xarray.transpose` fails.
- `tests/smoke/test_cellpose_pipeline_live.py`: `base.xarray.sum` fails.

## Proposal Alignment Review

### What matches the proposal
- Adds a comprehensive allowlist module (`src/bioimage_mcp/registry/dynamic/xarray_allowlists.py`).
- Implements multi-input execution paths for top-level functions and ufuncs (list input and multi-key input both supported) in `src/bioimage_mcp/registry/dynamic/adapters/xarray.py`.
- Introduces `base.xarray.DataArray` constructor and `to_bioimage` serializer.

### Key mismatches / gaps vs the proposal

#### 1) **Breaking change to stable MCP surface** (Severity: **Critical**)
Proposal explicitly recommends keeping old `base.xarray.*` IDs as deprecated aliases for a release cycle.

In this branch:
- `tools/base/manifest.yaml` removes legacy `base.xarray.*` functions entirely.
- `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` rejects `base.xarray.squeeze`, `base.xarray.rename`, etc. (see `execute()` around `src/bioimage_mcp/registry/dynamic/adapters/xarray.py:238`).

Impact:
- Contract tests fail.
- Integration tests fail.
- Smoke tests fail.
- Any existing workflows using `base.xarray.*` break immediately.

Actionable fix:
- If the breaking change is intentional, update failing tests (and any example workflows) to use the new IDs under `base.xarray.DataArray.*`:
  - `base.xarray.rename` → `base.xarray.DataArray.rename`
  - `base.xarray.squeeze` → `base.xarray.DataArray.squeeze`
  - `base.xarray.expand_dims` → `base.xarray.DataArray.expand_dims`
  - `base.xarray.transpose` → `base.xarray.DataArray.transpose`
  - `base.xarray.isel` → `base.xarray.DataArray.isel`
  - `base.xarray.pad` → `base.xarray.DataArray.pad`
  - `base.xarray.sum` → `base.xarray.DataArray.sum`
  - `base.xarray.max` → `base.xarray.DataArray.max`
  - `base.xarray.mean` → `base.xarray.DataArray.mean`
- Where tests previously assumed these steps output `BioImageRef`, update the base-environment adapters to also accept `ObjectRef` inputs end-to-end (so workflows can keep chaining without forced serialization). This implies:
  - downstream adapters (e.g. `skimage`, `phasorpy`, etc.) must be able to resolve `ObjectRef` → `xarray.DataArray` (in-process) when the next step runs in the same environment
  - chaining into a **different** environment must still trigger **materialization** to a file-backed `BioImageRef` (handoff boundary), since other envs cannot access the in-memory object cache
  - export functions (whether automatic during cross-env handoff or explicitly called by the user) should accept an xarray `ObjectRef` and automatically convert it to `OME-TIFF`/`OME-Zarr` on disk (i.e., export = ObjectRef → BioImageRef), using the `bioio.BioImage`-based I/O stack (BioImage for normalized handling + the corresponding bioio writers)
  - registry/IO contracts must reflect that `ObjectRef` is an allowed input type where relevant

#### 2) xarray functions are not discoverable via manifests (Severity: **High**)
Proposal Phase 4 suggests adding xarray to `dynamic_sources`.

Currently `tools/base/manifest.yaml` contains no xarray `dynamic_sources` entry, and also no static xarray functions.

Impact:
- The registry loader (`src/bioimage_mcp/registry/loader.py`) only discovers dynamic functions from `manifest.dynamic_sources`. With xarray absent from both `functions` and `dynamic_sources`, the server registry cannot advertise xarray operations via `list()`/`describe()`.
- This is consistent with the observed runtime failures: smoke tests call `base.xarray.squeeze` and the server treats it as unknown.

Actionable fix (decision):
- Adopt option (2) immediately: add an xarray `dynamic_sources` entry in `tools/base/manifest.yaml` so xarray functions are discoverable via `list()`/`describe()`.
- Do this together with Issue (3): the manifest/discovery layer must be able to represent the intended `ObjectRef`-based chaining API in its ports/contracts.

#### 3) Tool I/O schema cannot represent the proposed ObjectRef-based chaining (Severity: **High**)
The current discovery-to-manifest mapping uses `IOPattern` → fixed ports in `src/bioimage_mcp/registry/loader.py:_map_io_pattern_to_ports`.

Problems:
- `base.xarray.DataArray` is described as `IOPattern.GENERIC` in discovery (`src/bioimage_mcp/registry/dynamic/adapters/xarray.py:66`), but its actual output is an `ObjectRef`.
- DataArray methods in the proposal require input `ObjectRef | BioImageRef`. There is currently no `IOPattern` mapping that expresses union types or `ObjectRef` ports.

Impact:
- Even if xarray were added to `dynamic_sources`, the generated manifest would (likely) declare inputs/outputs as `BioImageRef`, and strict validation could reject `ObjectRef` chaining.

Actionable fix (decision):
- Adopt option (2) immediately: extend the registry/tool I/O representation (currently `IOPattern` → ports in `src/bioimage_mcp/registry/loader.py:_map_io_pattern_to_ports`) so discovery can express `ObjectRef` inputs/outputs for `base.xarray.DataArray` and `base.xarray.DataArray.*` correctly.
- Use `Port.artifact_type` unions where needed (it already supports `str | list[str]`), e.g. allow `artifact_type: ["BioImageRef", "ObjectRef"]` for methods that can take either.

#### 4) DataArray methods that require additional DataArray inputs are currently unsupported (Severity: **High**, depends on allowlist usage)
`src/bioimage_mcp/registry/dynamic/adapters/xarray.py:231` executes DataArray methods by:
- picking the first artifact as the “primary” DataArray
- calling `self.core.execute(method_name, da, **params)`

Any additional artifacts in `inputs` are ignored for DataArray methods.

Impact:
- Any allowlisted DataArray methods that require another array (e.g. `broadcast_like`, `reindex_like`, `interp_like`, method-form `where` with `other`, etc.) will raise `TypeError` or silently behave incorrectly because the required argument is never passed.

Actionable fix (decision):
- Implement argument resolution for DataArray methods similar to the ufunc/top-level multi-input paths (load secondary artifacts via `_load_da()` and pass them as positional/keyword args).

#### 5) Unbounded global `OBJECT_CACHE` (Severity: **Medium**, becomes **High** for large/long-lived sessions)
`src/bioimage_mcp/registry/dynamic/adapters/xarray.py:19` defines a process-global `OBJECT_CACHE: dict[str, Any] = {}`.

Impact scenarios:
- Long-running server sessions with repeated xarray operations on large images will steadily increase memory usage.
- No eviction, no per-session scoping, and no cleanup hook.

Actionable fix (decision):
- Scope the cache per session (namespace keys by session id) and add an eviction policy (LRU + size cap).

#### 6) Proposal/implementation drift in function counts and naming (Severity: **Low**, but causes brittle tests)
- Proposal claims total **137** (15 top-level + 50 ufuncs + 71 methods + 1 constructor).
- Implementation currently discovers **140** functions and tests hardcode `140` (e.g. `tests/contract/test_xarray_functions.py:100`).
- `tests/contract/test_xarray_functions.py` docstring says “exactly 147” but asserts `140`.

Actionable fix:
- Update proposal counts (if the implementation is the new truth), or update implementation/allowlists to match the proposal.
- Avoid hardcoding exact totals unless that is a deliberate contract.

#### 7) New integration tests do not follow the project’s “omit params when empty” rule (Severity: **Low**, but can cause real failures)
In `tests/integration/test_xarray_workflows.py`, several tool calls pass `params={}` even when no parameters are required.

The repo guideline in `AGENTS.md` states that tool calls must omit the `params` field entirely when defaults are used.

Actionable fix:
- Update tests to omit `params` when empty, and ensure client helpers do not send empty dicts by default.

## Suggested Next Steps (to get back to green)

1) Update failing tests and example workflows to the new `base.xarray.DataArray.*` IDs (Issue 1 decision).
2) Add xarray to `tools/base/manifest.yaml` as a `dynamic_sources` entry so xarray functions are discoverable via manifests (Issue 2 decision).
3) Extend registry/tool I/O contracts so `ObjectRef` (and unions like `[BioImageRef, ObjectRef]`) are first-class in ports/describe output (Issue 3 decision).
4) Update base-env adapters to accept xarray `ObjectRef` inputs for same-env chaining, and ensure cross-env handoff materializes to file-backed `BioImageRef`; export paths should convert `ObjectRef` → `OME-TIFF`/`OME-Zarr` by reading via `bioio.BioImage` and writing via the bioio writers (`OmeTiffWriter` / `OMEZarrWriter`).
5) Implement multi-DataArray argument resolution for DataArray methods (Issue 4 decision) and add a test covering a method that requires a second DataArray input.
6) Scope the xarray object cache per session with an eviction policy (Issue 5 decision).
7) Fix test/tool-call behavior to omit empty `params` fields where required by repo rules (Issue 7).
