# Implementation Plan: OME-Zarr Backed Artifact References for High-Dimensional Data

**Branch**: `026-zarr-artifact` | **Spec**: `specs/026-zarr-artifact/proposal.md`

## 1. Summary

Implement **targeted OME-Zarr support** for high-dimensional TTTR/FLIM derivative outputs (starting with `tttrlib.CLSMImage.get_fluorescence_decay`) while preserving **OME-TIFF as the default** interchange format for standard intensity images.

This work has three core outcomes:

1. **Artifact metadata normalization** supports single-character custom axis names (e.g. `B` for microtime bins) compatible with bioio's dimension handling.
2. **Base I/O** correctly detects and reports OME-Zarr artifacts (`.ome.zarr` / `.zarr`) with consistent `format="OME-Zarr"` and non-fragile `metadata.dims`.
3. **tttrlib decay outputs** become semantically correct: OME-Zarr with axis order `(Y, X, B)` matching native tttrlib output, and **no** `microtime_axis: "T"` hint.

## 2. Goals / Non-Goals

### Goals
- Support **single-character custom axis names** in artifact metadata (e.g. `B` for microtime bins, `H` for harmonics) to ensure bioio compatibility.
- Ensure `base.io.bioimage.load` and `base.io.bioimage.export` are consistent for OME-Zarr.
- Switch `tttrlib.CLSMImage.get_fluorescence_decay` output from OME-TIFF (`T` axis hijack) to OME-Zarr with `(Y, X, B)` axis order.
- Preserve/propagate physical metadata where feasible (pixel sizes; axis units), with safe fallbacks.
- Update contract + smoke tests to enforce new behavior (TDD).

### Non-Goals
- Full migration of all `BioImageRef` outputs to OME-Zarr (Option B).
- Format negotiation between tool packs (Option C).
- Adding new user-facing conversion tools (conversion remains `base.io.bioimage.export`).

## 3. Technical Context

- **Core server**: Python 3.13, `pydantic v2`, `mcp`, filesystem-backed artifact store.
- **Tool envs**: isolated conda envs per pack (Constitution Principle II).
- **Relevant deps**:
  - `bioio` for reading
  - `bioio-ome-tiff` for OME-TIFF writing
  - `bioio-ome-zarr` for OME-Zarr writing/reading (must be present in tool envs that write Zarr)
- **Testing**:
  - Contract tests: `tests/contract/`
  - Unit tests: `tests/unit/`
  - Smoke tests: `tests/smoke/` (live server)
  - Tool-env integration tests where required: `conda run -n bioimage-mcp-tttrlib ...`

## 4. Design Decisions

### 4.1 Canonical axis representation
- `metadata.dims` is the canonical representation: `list[str]` with **single-character** axis names for bioio compatibility.
- **Important constraint**: bioio's `BioImage` reader only supports single-character dimension names. Multi-character names like `"bins"` will cause load failures. Use `"B"` instead.
- `metadata.axes` is treated as a **legacy hint** for compatibility:
  - For single-letter dims: `axes` may be the concatenated string (e.g., `"YXB"`).
  - Omit `axes` if using non-standard dimension characters.
- Semantic meaning is captured in `metadata.axis_roles` (e.g., `{"B": "microtime_histogram"}`).

### 4.2 FLIM decay axis naming and order
- Use **`B`** (single character) as the axis name for microtime histogram bins.
- Use **`(Y, X, B)`** axis order (space-first, microtime-last):
  - Matches native tttrlib `get_fluorescence_decay()` output shape - no `moveaxis` needed.
  - Matches FLIM software conventions (PicoQuant SymPhoTime, Becker & Hickl SPCImage).
  - Natural per-pixel decay access pattern: `data[y, x, :]` gives decay curve for pixel (y, x).
- For volumetric data: use `(Z, Y, X, B)` order.
- Set NGFF axis type to `"other"` for `B`.
- Add `metadata.axis_roles = {"B": "microtime_histogram"}` for semantic clarity.

### 4.3 Harmonics axis (for phasor analysis)
- Use **`H`** for the harmonics dimension (confirmed standard in PhasorPy).
- Phasor G/S components stored as channels with `channel_names=["G", "S"]`.

### 4.4 Units and pixel sizes
- Preserve physical pixel sizes for `x/y/z` axes when available.
- Preserve or compute `B` axis unit when possible:
  - Prefer `nanosecond` (singular, per NGFF spec) when resolvable from TTTR header.
  - If not resolvable, store `None` (but keep the axis name semantic).

### 4.5 Zarr format version
- **Use Zarr v2** (`zarr_format=2`) for maximum ecosystem compatibility.
- **Rationale**: OME-Zarr v0.4 (Zarr v2) has broader tool support than v0.5 (Zarr v3) as of early 2026:
  - napari, ImageJ/Fiji Bio-Formats, QuPath all support v0.4
  - bioio-ome-zarr supports both, but v2 is more battle-tested
  - v0.5 adoption is ongoing but not yet universal
- **Future migration**: When v0.5 ecosystem matures, add a configuration option to select Zarr version.

## 5. Constitution Check (Relevant Principles)

- **II. Isolated tool execution**: OME-Zarr writing in tttrlib occurs inside `bioimage-mcp-tttrlib`.
- **III. Artifact references only**: outputs remain file-backed refs (directories for Zarr).
- **I. Stable MCP surface**: no new endpoints; additive metadata relaxations only.
- **VI. TDD**: each phase starts with failing tests.

## 6. Implementation Phases (TDD)

### Phase -1: Tool Environment Dependencies (TDD)

**Why early**: Phase 3 switches the tttrlib tool pack to write OME-Zarr using `bioio_ome_zarr.writers.OMEZarrWriter`. That requires the **tttrlib environment** to include the OME-Zarr plugin package.

**Current env status (as of `envs/bioimage-mcp-tttrlib.yaml`)**
- ✅ `bioio` present
- ✅ `bioio-ome-tiff` present
- ❌ `bioio-ome-zarr` missing (OME-Zarr read/write plugin not guaranteed)
- ❌ No `envs/bioimage-mcp-tttrlib.lock.yml` present (reproducibility gate)

**Failing tests to add/update first:**
1. Extend `tests/contract/test_tttrlib_env.py` to assert `bioio-ome-zarr` is explicitly listed in `envs/bioimage-mcp-tttrlib.yaml`.
2. (Optional but recommended) Add/extend a contract test to assert the corresponding lockfile exists once env YAML changes are made.

**Implementation steps:**
1. Update `envs/bioimage-mcp-tttrlib.yaml`
   - Add `bioio-ome-zarr`
   - (Optional) add `zarr` explicitly if needed by downstream tooling, but prefer letting `bioio-ome-zarr` pull it unless the solver gets ambiguous.
2. Generate a pinned lockfile using `conda-lock`
   - **Naming convention**: `envs/bioimage-mcp-tttrlib.conda-lock.yml` (unified multi-platform format)
   - **Command**:
     ```bash
     conda-lock -f envs/bioimage-mcp-tttrlib.yaml \
       -p linux-64 -p osx-arm64 \
       --lockfile envs/bioimage-mcp-tttrlib.conda-lock.yml
     ```
   - The unified lockfile contains solutions for **both** platforms in a single file.
   - To install from the lockfile: `conda-lock install -n bioimage-mcp-tttrlib envs/bioimage-mcp-tttrlib.conda-lock.yml`
3. (Optional) Add a quick env smoke check command in CI/docs
   - `conda run -n bioimage-mcp-tttrlib python -c "from bioio_ome_zarr.writers import OMEZarrWriter"`

**Verification:**
- `pytest tests/contract/test_tttrlib_env.py -v`

---

### Phase 0: Baseline + Test Scaffolding

**Intent**: lock in current behavior (where needed) and add new failing tests that define the desired behavior.

**New failing tests (write first):**
1. Contract: schema accepts single-character custom dims
   - New: `tests/contract/test_artifact_metadata_schema_allows_custom_dims.py`
   - Validate JSON schema accepts an `ArtifactRef` with:
     - `format="OME-Zarr"`
     - `metadata.dims=["Y","X","B"]`
     - `metadata.ndim=3`
2. Unit: base I/O format detection for `.ome.zarr`
   - New: `tests/unit/tools_base/test_io_detects_ome_zarr.py`
   - Create a temporary directory named `something.ome.zarr` and assert `_detect_format` (or the public `load`) reports `OME-Zarr`.

**Exit criteria:** new tests fail for the expected reasons (dims schema too strict; format detection missing).

---

### Phase 1: Schema + Metadata Normalization (Core + Base)

**Scope**: update artifact metadata contract(s) and normalize code paths that assume `TCZYX` or split dimensions incorrectly.

**Failing tests to add/extend first:**
1. Update/extend `tests/contract/test_artifact_metadata_contract.py` to include a synthetic `ArtifactRef` with `metadata.dims=["Y","X","B"]` validated against the schema.
2. Unit test to ensure no char-splitting occurs:
   - New: `tests/unit/artifacts/test_dims_are_not_character_split.py`
   - Validate that a `dims` source of `"B"` survives normalization as `"B"` (not `["B"]` from string splitting).

**Implementation steps:**
1. Relax artifact metadata schema constraints:
   - Modify `specs/014-native-artifact-types/contracts/artifact-metadata-schema.json`
     - `ImageMetadata.dims.items` from enum `[T,C,Z,Y,X]` → `type: string` (allows custom single-char axes like `B`, `H`)
     - Keep `maxItems: 5` and `ndim.maximum: 5` (NGFF v0.4/v0.5 limits multiscales to ≤5D; our use cases are 3-4D)
     - Consider bumping `version` field (schema-level) to reflect the contract update
2. Base toolkit: consistent OME-Zarr detection
   - Modify `tools/base/bioimage_mcp_base/ops/io.py`
     - `_detect_format()` recognizes directories ending with `.ome.zarr` or `.zarr` as `"OME-Zarr"`
     - `_get_mime_type()` returns a stable mime type for OME-Zarr (e.g. `application/zarr+ome`)
     - ensure `load` populates `format="OME-Zarr"` for directory-backed artifacts
3. Ensure `metadata.dims` remains `list[str]` everywhere
   - Audit any `list(axes_string)` or implicit splitting.
4. Add integration test for OME-Zarr dims round-trip through `load()`
   - New: `tests/integration/test_ome_zarr_dims_roundtrip.py`
   - Create an OME-Zarr with `dims=["Y", "X", "B"]`, call `base.io.bioimage.load`, assert returned `metadata.dims==["Y", "X", "B"]`.

**Verification:**
- `pytest tests/contract/test_artifact_metadata_contract.py -v`
- `pytest tests/contract/test_artifact_metadata_schema_allows_custom_dims.py -v`
- `pytest tests/unit/artifacts/test_dims_are_not_character_split.py -v`
- `pytest tests/unit/tools_base/test_io_detects_ome_zarr.py -v`
- `pytest tests/integration/test_ome_zarr_dims_roundtrip.py -v`

---

### Phase 2: Preserve units / pixel sizes in fallback OME-Zarr writes

**Scope**: ensure that when the system writes OME-Zarr (especially the xarray adapter fallback), it does not hardcode meaningless defaults.

**Failing tests (write first):**
1. Unit test for `save_native_ome_zarr` metadata propagation
   - New: `tests/unit/registry/test_xarray_save_native_ome_zarr_preserves_scale.py`
   - Build a small array + dims and pass explicit pixel sizes; assert written NGFF metadata matches.
2. Unit test for tttrlib decay unit propagation from TTTR header
   - New: `tests/unit/tools_tttrlib/test_decay_extracts_microtime_resolution.py`
   - Mock a TTTR header with known microtime resolution (e.g., `header.micro_time_resolution = 0.016` ns)
   - Assert that the decay writer computes the correct bin width and populates `axes_units` for the `B` axis.

**Implementation steps:**
1. Update `src/bioimage_mcp/registry/dynamic/adapters/xarray.py`
   - Modify `save_native_ome_zarr(...)` to accept optional:
     - `axes_units: list[str | None]`
     - `physical_pixel_size: list[float | None]` (or the writer's expected shape)
   - Stop hardcoding:
     - `axes_units=[None]*ndim`
     - `physical_pixel_size=[1.0]*ndim`
   - Choose propagation source (in priority order):
     1. input artifact metadata (`physical_pixel_sizes`, and any known axis units)
     2. xarray attributes (if present)
     3. safe fallback: `None`
2. Update `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`
   - In `handle_get_fluorescence_decay`, extract microtime resolution from TTTR header:
     ```python
     # tttrlib provides micro_time_resolution in the header (picoseconds or nanoseconds)
     header = tttr_data.header
     micro_time_res_ns = getattr(header, 'micro_time_resolution', None)
     if micro_time_res_ns is not None:
         bin_unit = "nanosecond"
     else:
         bin_unit = None
     ```
   - Pass `bin_unit` to the OMEZarrWriter's `axes_units` parameter.

**Verification:**
- `pytest tests/unit/registry/test_xarray_save_native_ome_zarr_preserves_scale.py -v`
- `pytest tests/unit/tools_tttrlib/test_decay_extracts_microtime_resolution.py -v`

---

### Phase 3: tttrlib `get_fluorescence_decay` outputs OME-Zarr with `B` axis

**Scope**: remove the `T` axis hijack and produce a semantically correct decay artifact with `(Y, X, B)` axis order.

**Failing tests (write first):**
1. Contract: manifest declares the new format
   - Update `tests/contract/test_tttrlib_manifest.py` to require:
     - `tttrlib.CLSMImage.get_fluorescence_decay` output `format: OME-Zarr`
2. Smoke: decay output asserts OME-Zarr + `B` axis
   - Update `tests/smoke/test_tttrlib_live.py` (existing test already calls `get_fluorescence_decay`):
     - assert returned artifact `format == "OME-Zarr"`
     - assert `uri` ends with `.ome.zarr` (or `.zarr`) and is a directory
     - assert `metadata.dims == ["Y", "X", "B"]` (space-first order)
     - assert `metadata.axis_roles["B"] == "microtime_histogram"`
     - remove assertion for `metadata.microtime_axis == "T"`

**Implementation steps:**
1. Update tool implementation
   - Modify `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`
     - In `handle_get_fluorescence_decay`, replace `OmeTiffWriter.save(...)` with `OMEZarrWriter`.
     - **Keep native tttrlib output order** - no `moveaxis` needed:
       - stacked decay `(Y, X, bins)` → write directly with `axes_names=["y", "x", "b"]`
       - volumetric decay `(Z, Y, X, bins)` → write directly with `axes_names=["z", "y", "x", "b"]`
     - `axes_types=["space", "space", "other"]` (or `["space", "space", "space", "other"]` for 4D)
     - `axes_units=["micrometer", "micrometer", "nanosecond"]` when pixel sizes available
     - set `format="OME-Zarr"`, output path `decay_<id>.ome.zarr`
     - update output `metadata`:
       - `dims`: `["Y", "X", "B"]` (bioio uppercases axis names)
       - `ndim`, `shape`, `dtype`
       - `axis_roles`: `{"B": "microtime_histogram"}`
       - keep `micro_time_coarsening` and `n_microtime_bins`
       - **remove** `microtime_axis` field entirely
2. Update tool manifest + schema snapshot
   - Modify `tools/tttrlib/manifest.yaml` to set output `format: OME-Zarr` for the decay function.
   - Modify `tools/tttrlib/schema/tttrlib_api.json` to match the manifest.

**Verification:**
- `pytest tests/contract/test_tttrlib_manifest.py -v`
- `pytest tests/smoke/test_tttrlib_live.py -k fluorescence_decay -v`

---

### Phase 4: Optional internal-only conversion helpers (only if needed)

**Trigger**: only implement if a downstream tool pack needs “OME-TIFF-only” inputs and we find repeated boilerplate conversions.

**Constraints**:
- Helpers must remain internal to `tools/base/` (do not expose in `tools/base/manifest.yaml`).
- Public conversion stays `base.io.bioimage.export`.

**Possible work**:
- Add helper in `tools/base/bioimage_mcp_base/` to materialize OME-Zarr → OME-TIFF for tool-local consumption.

## 7. Acceptance Criteria

- `tttrlib.CLSMImage.get_fluorescence_decay` produces an artifact with:
  - `format == "OME-Zarr"`
  - `metadata.dims == ["Y", "X", "B"]` (space-first, microtime-last order)
  - `metadata.axis_roles["B"] == "microtime_histogram"`
  - no use of `metadata.microtime_axis == "T"`
- Artifact metadata schema allows `dims: list[str]` with single-character custom axis names (e.g., `B`, `H`).
- `base.io.bioimage.load` reports OME-Zarr directories as `format="OME-Zarr"`.
- Existing OME-TIFF workflows (Cellpose, basic image ops) remain unchanged.

## 8. Verification Commands

```bash
# Contract tests
pytest tests/contract/ -v

# Unit tests
pytest tests/unit/ -v

# Smoke tests (live server)
pytest tests/smoke/test_tttrlib_live.py -v

# Tool-env dependency check (fast)
conda run -n bioimage-mcp-tttrlib python -c "from bioio_ome_zarr.writers import OMEZarrWriter"

# Tool-env integration (if added for decay)
conda run -n bioimage-mcp-tttrlib pytest tests/integration/ -k decay -v

# Lint/format
ruff check .
ruff format --check .
```

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OME-Zarr directory outputs complicate workflows | Keep OME-TIFF default; limit OME-Zarr to TTTR-derived artifacts initially |
| Unit/pixel size metadata not available from TTTR headers | Store best-effort units; fall back to `None` while preserving axis naming |
| Schema change accidentally breaks existing clients | Keep additive changes; do not remove legacy fields; validate contract + smoke |
| Downstream TIFF-only tools (Cellpose/Fiji) need conversion | Use `base.io.bioimage.export` (agent-visible) or internal-only helper if repetitive |

---

## Appendix A: bioio Dimension Handling Constraints

### Key Constraint: Single-Character Axis Names Only

bioio's `BioImage` class enforces that dimension names must be single characters. Multi-character names like `"bins"` or `"microtime"` will cause load failures:

```
ValueError: When providing a list of dimension strings, each dimension 
may only be a single character long (received: '('BINS', 'Y', 'X')').
```

### Two APIs with Different Behaviors

| Accessor | Behavior | Custom Axis Support |
|----------|----------|---------------------|
| `img.data`, `img.dims`, `img.shape` | Normalized 5D TCZYX | ❌ Custom axes lost |
| `img.reader.data`, `img.reader.dims`, `img.reader.xarray_data` | Native dimensions | ✅ Custom axes preserved |

**For FLIM data, always use `img.reader.*` accessors** to preserve custom axis semantics.

### Example: Loading Decay Data

```python
from bioio import BioImage

img = BioImage("decay.ome.zarr")

# WRONG - custom axes are lost, data reshaped to 5D
data = img.data  # shape: [1, 1, 1, 32, 32] - B axis gone!

# CORRECT - native dimensions preserved
data = img.reader.data  # shape: [32, 32, 64] - (Y, X, B) preserved
xr_data = img.reader.xarray_data  # dims: ['Y', 'X', 'B']
decay_curve = xr_data.isel(Y=16, X=16)  # Per-pixel decay access
```

---

## Appendix B: OME-Zarr Writer Configuration for FLIM Data

### Recommended Configuration for Decay Histograms

```python
from bioio_ome_zarr.writers import OMEZarrWriter

# Native tttrlib output is (Y, X, bins) - keep as-is, no moveaxis needed!
# decay_data.shape = (32, 32, 64)  # (Y, X, B)

writer = OMEZarrWriter(
    store=str(out_path),
    level_shapes=[decay_data.shape],
    dtype=decay_data.dtype,
    axes_names=["y", "x", "b"],           # Single-char, bioio will uppercase
    axes_types=["space", "space", "other"],
    axes_units=["micrometer", "micrometer", "nanosecond"],  # Singular per NGFF
    zarr_format=2,  # Zarr v2 for OME-Zarr v0.4 compatibility (see Section 4.5)
)
writer.write_full_volume(decay_data)
```

### Artifact Metadata Output

```python
output = {
    "ref_id": uuid.uuid4().hex,
    "type": "BioImageRef",
    "uri": f"file://{out_path.absolute()}",
    "format": "OME-Zarr",
    "storage_type": "zarr-temp",
    "created_at": datetime.now(UTC).isoformat(),
    "metadata": {
        "dims": ["Y", "X", "B"],  # bioio uppercases
        "shape": list(decay_data.shape),
        "ndim": decay_data.ndim,
        "dtype": str(decay_data.dtype),
        "axis_roles": {"B": "microtime_histogram"},
        "n_microtime_bins": decay_data.shape[2],
        "micro_time_coarsening": micro_time_coarsening,
        # NO microtime_axis field - semantic is now explicit via axis_roles
    },
}
```

### Multi-Harmonic Phasor Configuration

```python
# phasor_data.shape = (3, 2, 32, 32)  # (H, C, Y, X) - 3 harmonics, 2 channels (G, S)

writer = OMEZarrWriter(
    store=str(out_path),
    level_shapes=[phasor_data.shape],
    dtype=phasor_data.dtype,
    axes_names=["h", "c", "y", "x"],
    axes_types=["other", "channel", "space", "space"],
    zarr_format=2,  # Zarr v2 for OME-Zarr v0.4 compatibility (see Section 4.5)
)
writer.write_full_volume(phasor_data)

# Metadata
metadata = {
    "dims": ["H", "C", "Y", "X"],
    "axis_roles": {"H": "harmonic"},
    "channel_names": ["G", "S"],
}
```

---

## Appendix C: Axis Naming Convention Summary

| Axis | Single-Char | Semantic Role | NGFF Type |
|------|-------------|---------------|-----------|
| Microtime bins | `B` | `"microtime_histogram"` | `"other"` |
| Harmonics | `H` | `"harmonic"` | `"other"` |
| Phasor G/S | `C` | (use `channel_names`) | `"channel"` |
| Time-lapse | `T` | (standard OME) | `"time"` |
| Channel | `C` | (standard OME) | `"channel"` |
| Z-stack | `Z` | (standard OME) | `"space"` |
| Spatial Y | `Y` | (standard OME) | `"space"` |
| Spatial X | `X` | (standard OME) | `"space"` |

### Axis Order Conventions

| Data Type | Order | Rationale |
|-----------|-------|-----------|
| FLIM decay | `(Y, X, B)` | Matches native tttrlib; natural per-pixel decay access |
| FLIM decay (volumetric) | `(Z, Y, X, B)` | Space-first, microtime-last |
| Multi-harmonic phasor | `(H, C, Y, X)` | Harmonics outer, channels for G/S |
| Standard intensity | `(T, C, Z, Y, X)` | OME convention |
