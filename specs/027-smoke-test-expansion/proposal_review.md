# Review: specs/027-smoke-test-expansion/proposal.md

This review focuses on (1) factual accuracy vs the current repository state and (2) likely implementation pitfalls for the proposed “MCP vs native execution equivalence” smoke tests.

## Accuracy Check: Current Codebase State

### Smoke test suite inventory is incomplete

The proposal’s **Current State** section lists only:
- `tests/smoke/test_tttrlib_live.py`
- `tests/smoke/test_flim_phasor_live.py`

However, the repo currently contains additional smoke tests that are already part of the smoke harness:
- `tests/smoke/test_smoke_basic.py` (minimal discovery + a basic run)
- `tests/smoke/test_cellpose_pipeline_live.py` (Cellpose workflow)
- `tests/smoke/test_multi_artifact_concat.py` (multi-artifact list input regression)
- `tests/smoke/test_smoke_recording.py` (recording-mode log output)

These matter because the test harness already distinguishes `smoke_minimal` vs `smoke_full` and enforces a strict time budget for minimal mode (`SmokeConfig.minimal_suite_budget_s = 120.0` in `tests/smoke/conftest.py`). Any new “equivalence” tests that involve `conda run ...` will almost certainly need to be `smoke_full`.

### “Dual execution pattern already demonstrated” is not strictly accurate

The proposal claims the `tttrlib` tests “demonstrate the dual execution pattern with cross-tool workflows”.

What exists today in `tests/smoke/test_tttrlib_live.py` is a *cross-tool* workflow executed via MCP (tttrlib + cellpose + base), but **not** an MCP-vs-native dual-run comparison. There is no “native” reference execution path in smoke tests today.

So the “pattern” exists only partially:
- ✅ Multi-step workflow orchestration exists.
- ✅ Cross-tool interoperability exists.
- ❌ No side-by-side comparison against a native script exists.

### “Implemented libraries” list does not match the base tool pack surface

The proposal lists “phasorpy, cellpose, skimage, scipy, matplotlib” as the implemented libraries to cover.

The base tool pack manifest also declares dynamic sources for `xarray` and `pandas` (`tools/base/manifest.yaml`), and those APIs are heavily used in existing smoke tests (`base.xarray.DataArray.sum`, `base.xarray.DataArray.transpose`, etc.). If the intent is “cover all implemented surfaces”, either:
- include `xarray`/`pandas` explicitly, or
- scope the spec to “scientific libraries” and call out why `xarray`/`pandas` are excluded.

## Accuracy Check: Tutorial/Documentation References

### Cellpose version mismatch

The proposal references Cellpose `v3.1.1.1` documentation.

The repo’s pinned environment is **Cellpose 3.1.1.2** (`envs/bioimage-mcp-cellpose.lock.yml` has `cellpose-3.1.1.2-...`). That’s close, but if you plan schema/signature comparisons, pin to the exact version.

### Cellpose API call pattern is slightly off

The proposal’s Cellpose workflow says:
- `CellposeModel(model_type='cyto3', gpu=False)`
- `model.eval(img, diameter=30.0, channels=[0,0], flow_threshold=0.4, cellprob_threshold=0.0)`

From Cellpose docs:
- The high-level `cellpose.models.Cellpose` wrapper uses `channels=[0,0]` and `diameter=30.0` defaults.
- The lower-level `cellpose.models.CellposeModel.eval` signature defaults `channels=None` and `diameter=None` (and uses internal defaults like `diam_mean`).

This matters because `bioimage-mcp` exposes `cellpose.models.CellposeModel.eval` (and a separate constructor tool), but also supplies its own defaults in the MCP schema.

Recommendation: update the proposal to explicitly treat `CellposeModel.eval` defaults as “tool-defined defaults” rather than “library defaults”, or else the schema-alignment portion will generate false positives.

### PhasorPy signatures in the proposal are outdated vs current stable docs

The proposal lists (examples):
- `phasorpy.phasor.phasor_from_signal(signal, *, axis=-1, harmonic=1)`

But current PhasorPy stable docs (v0.9) show:
- `phasor_from_signal(signal, /, *, axis=None, harmonic=None, ..., normalize=True, ...)`

Similarly, `phasor_calibrate` in the docs uses parameter names:
- `reference_mean`, `reference_real`, `reference_imag`

Whereas the proposal uses `ref_mean`, `ref_real`, `ref_imag`. That will not match either:
- the actual library signature, or
- the MCP adapter’s input-port naming conventions.

Recommendation: update the proposal’s “Reference Documentation Alignment” signatures to match PhasorPy v0.9.

### Matplotlib tutorial link is fine, but the plan assumes signature-level stability you won’t get from the gallery

The Matplotlib link in the proposal points to the gallery index, which is not a great source for extracting function signatures/defaults.

If signature assertions are a goal, use the Matplotlib API reference pages (`matplotlib.pyplot.subplots`, `matplotlib.axes.Axes.imshow`, `matplotlib.figure.Figure.savefig`) rather than the gallery index.

## Design Gaps / Inconsistencies

### 1) Schema-alignment tests as written will produce many false positives

The proposal suggests:
- `describe()` to get an MCP schema
- `inspect.signature()` to get the “actual” callable signature
- assert default equality / param presence

This is not directly valid in this codebase for several reasons:

1) **Artifact ports are intentionally removed from params_schema**
   - The server filters out input/output port names from `params_schema` (see `src/bioimage_mcp/api/discovery.py`, “Contract T036: params_schema contains NO artifact port keys”).
   - Therefore, comparing `inspect.signature()` (which includes `image`, `signal`, `real`, etc.) to `params_schema` will incorrectly report “missing params”.

2) **Adapters intentionally reshape or constrain the exposed surface**
   - `MatplotlibAdapter` is allowlist-based with custom schemas (`src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py`) and is not meant to mirror the full Matplotlib signature surface.
   - `SkimageAdapter` skips functions with `**kwargs` during discovery; any “expect full signature parity” will fail by design.

3) **Defaults are not always JSON-serializable or represented the same way**
   - The project already has infrastructure dedicated to making defaults JSON-serializable.
   - Some libraries use sentinel defaults (`None` meaning “auto”), which may be converted to explicit numbers in tool schemas for usability.

Remediation proposal:
- Replace “schema matches library signature” with one of:
  1) “schema is self-consistent”: `describe(fn_id)` matches the tool runtime `meta.describe` output (same properties + defaults), or
  2) “schema matches allowlist”: only test a curated, explicit mapping list of parameters that MCP intentionally supports.

### 2) Native execution environment mismatch is not addressed

The smoke tests run in the **core** Python environment (>=3.13), while key libraries run in isolated conda envs:
- `bioimage-mcp-base` (phasorpy, scikit-image, scipy, matplotlib)
- `bioimage-mcp-cellpose` (cellpose, torch)

If you execute “native scripts” from the test process, you likely will not have the same dependencies available.

Remediation proposal:
- Make “native execution” explicitly mean `conda run -n <env> python ...` reference scripts.
- Budget time accordingly and mark them as `smoke_full` (or a new `smoke_equivalence` marker that is excluded from minimal CI).

### 3) The proposed “matplotlib equivalence” concept is underspecified

Matplotlib outputs are raster images (PNG) whose pixel values vary across:
- font availability
- backend differences
- rendering / antialiasing
- DPI and bbox calculations

“Data equivalence validation (not format equivalence)” makes sense for numeric arrays but is a poor fit for Matplotlib.

Remediation proposal:
- For Matplotlib, test *semantic* invariants instead of pixel equality:
  - PlotRef exists
  - dimensions roughly match expected DPI and figure size
  - file is readable (non-empty)
  - optionally: image histogram / mean intensity is in expected range (very loose)
- Keep strict numerical equivalence for array outputs (phasorpy/scipy/skimage) and strict equality for labels only when deterministic.

### 4) Cellpose equivalence using label equality is risky

Even on CPU, Cellpose can produce small nondeterministic changes depending on:
- torch version / kernels
- threading
- internal resizing/normalization

Expecting exact label images to match between two independent runs can be brittle.

Remediation proposal:
- Compare using segmentation metrics (IoU/Dice) above a threshold, not exact label-by-label equality.
- Pin seeds / threads where possible (and document the limits of determinism).

### 5) Proposed phasorpy workflow parameter names are inconsistent with the tool adapter behavior

In the repo, phasorpy functions are exposed as `base.phasorpy.<module>.<function>` (e.g. `base.phasorpy.phasor.phasor_from_signal`).

The proposal’s section “Reference Documentation Alignment” omits the `base.` prefix and also uses parameter names (`ref_mean`) that do not match the library.

Remediation proposal:
- Normalize function IDs and parameter names to the actual callable interface used by MCP:
  - MCP fn_ids: `base.phasorpy.phasor.phasor_from_signal`, etc.
  - PhasorPy calibrate params: `reference_mean`, `reference_real`, `reference_imag`.

## Implementation Difficulties to Anticipate

### A) Axis conventions and array shapes

The proposal suggests comparing arrays loaded via `BioImage(...).reader.data` and then `np.squeeze()`.

In practice:
- The project sometimes treats FLIM “Z” as the histogram/bin axis.
- Existing smoke tests already have to transpose to get the right axis for phasor computation (`tests/smoke/test_flim_phasor_live.py` uses `base.xarray.DataArray.transpose` and then `axis=-1`).

If native scripts use a different axis order than MCP workflows, you will get non-equivalent results even when both are “correct”.

Recommendation:
- For each equivalence test, explicitly define the expected axis order at each step and implement a shared helper that normalizes to a canonical array shape prior to comparison.

### B) Dataset availability / Git LFS / size

The tttrlib tests already include special logic to detect Git LFS pointer files and skip if datasets are not present (`tests/smoke/test_tttrlib_live.py`).

New tests that rely on real datasets should replicate this pattern, otherwise CI/local runs without full datasets will fail.

Recommendation:
- Prefer `datasets/synthetic/test.tif` for deterministic minimal tests.
- Gate larger/real datasets behind `smoke_full` and dataset presence checks.

### C) SciPy adapter output format / constitution mismatch risk

The current `ScipyNdimageAdapter` writes outputs via `tifffile.imwrite` while labeling the artifact as `format: OME-TIFF` (`src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`). This is likely to be a correctness/consistency problem relative to the project’s I/O conventions.

If equivalence tests depend on reading metadata/dims or validating OME-ness, they may expose this.

Recommendation:
- Either fix the SciPy adapter to use `bioio.writers.OmeTiffWriter` (preferred), or
- scope equivalence comparisons to raw pixel arrays only, and avoid asserting OME metadata for scipy outputs.

### D) CI section is speculative

The proposal includes GitHub Actions YAML snippets, but the repo currently has no `.github/workflows/` directory. Treat these as aspirational examples or adapt to the actual CI system used by this repo.

## Concrete Remediation Edits Suggested for proposal.md

1) **Update “Current State”**
   - Add the currently existing smoke tests (`test_smoke_basic.py`, `test_cellpose_pipeline_live.py`, `test_multi_artifact_concat.py`, `test_smoke_recording.py`).
   - Clarify that “dual execution” is new work; existing tests are MCP-only workflows.

2) **Clarify what “native execution” means**
   - Explicitly state it will run inside the corresponding conda env using `conda run -n ...`.
   - Budget and marker guidance: equivalence tests are `smoke_full`.

3) **Revise schema-alignment approach**
   - Replace “compare describe() against inspect.signature()” with:
     - “compare describe() against meta.describe output for the same fn_id”, and/or
     - “compare describe() against an explicit allowlist mapping (expected supported params)”.

4) **Correct tutorial/signature references**
   - PhasorPy: update signatures to v0.9 (e.g. `axis=None`, `harmonic=None`, `reference_mean` naming).
   - Cellpose: acknowledge `CellposeModel.eval` defaults (`diameter=None`, `channels=None`) and explicitly define what defaults MCP enforces.
   - Matplotlib: link to API reference pages if signature testing is desired.

5) **Adjust equivalence assertions**
   - Matplotlib: do not do pixel-perfect comparisons; validate artifact existence + coarse properties.
   - Cellpose: use IoU/Dice thresholds, not exact label equality.

6) **Fix code snippets in proposal**
   - `assert_data_equivalent` should accept an artifact ref dict (with `uri`), not a raw URI string.
   - Handle `.ome.zarr` directories (BioImage can read them, but path handling differs).

---

If you want, I can also propose a revised “Success Criteria” section that matches the above realities (markers, determinism, and schema parity expectations).