# Implementation Plan: Smoke Test Expansion (027)

## Summary
Expand smoke tests to cover all implemented libraries (PhasorPy, Cellpose, Scikit-image, SciPy, Matplotlib, Xarray, Pandas) with dual MCP/native execution, data equivalence validation using numerical tolerance, and schema self-consistency detection between MCP describe() and tool runtime meta.describe().

## Technical Context
- **Language/Version**: Python 3.13 (core server); Python 3.11 (cellpose env); Python 3.13 (base env)
- **Primary Dependencies**: pytest, numpy, MCP Python SDK
- **Tool-env Dependencies (via conda run)**: bioio (+ readers/writers), library under test (e.g., cellpose)
- **Testing**: pytest with smoke_minimal and smoke_full markers
- **Target Platform**: Cross-platform (Linux/macOS/Windows)
- **Project Type**: Test suite expansion (adds optional `verbosity` parameter to MCP `run` for token-safe responses; backward-compatible, defaults to `minimal`)
- **Key Libraries**: PhasorPy, Cellpose, Scikit-image, SciPy, Matplotlib, Xarray, Pandas
- **Constraints**: Tests run in core env but spawn isolated subprocesses via conda run

## Constitution Check
- [x] **Stable MCP surface**: Adds optional `verbosity` parameter to `run` (defaults to `minimal`); backward-compatible with existing clients. `RunResponseSerializer` reduces token bloat in responses.
- [x] **Tool execution isolated**: Native scripts run via conda run -n <env>
- [x] **Artifact references only**: Tests validate BioImageRef/LabelImageRef/PlotRef/TableRef artifacts
- [x] **Reproducibility**: Tests use explicit tolerances and document nondeterminism limits
- [x] **Safety + debuggability**: Tests include clear skip reasons; optional `--smoke-record` mode provides extra debugging logs
- [x] **Cross-platform**: Tests and utilities must run on Linux/macOS/Windows; platform-specific skips must be explicit and justified

## Phases & Gates
- **Phase 0 (Prerequisites)**: Fix ScipyNdimageAdapter I/O + verify dataset LFS status. See `phase0-prerequisites.md`.
- Phase 1 (Setup): Create directories + LFS skip utility.
- Phase 2 (Foundation): Implement NativeExecutor + DataEquivalenceHelper.
- Phase 3 (US1): Add per-library baseline scripts + equivalence tests.
- Phase 4 (US2): Add schema alignment tests for a curated schema test vector (per environment).
- Phase 5-6 (US3/US4): Strengthen plot + metadata checks.
- Phase 7 (Polish): Wire fixtures + run with --smoke-record.

Quality gates:
- TDD: each implementation task must be preceded by a failing test task.
- Markers: equivalence tests must be smoke_full; lightweight schema checks may be smoke_minimal.
- Env availability: missing conda env must cause a clear skip (not a hard failure).
- Cross-platform: platform-specific behavior must be documented and enforced via explicit skips (never silent pass/fail divergence).

## Test Vectors & Scope Decisions

- **Schema alignment scope**: Validate `describe(fn_id)` vs runtime `meta.describe()` for a curated, explicit function list per tool environment (a "schema test vector"). This keeps `smoke_minimal` fast while still detecting drift for representative APIs.
- **Smoke recording**: `--smoke-record` is an existing debugging feature in `tests/smoke/`; this feature uses it only for optional diagnostics and does not require it for normal pass/fail behavior.

## Project Structure

### Documentation
```text
specs/027-smoke-test-expansion/
├── plan.md              # This file
├── phase0-prerequisites.md  # Phase 0 implementation guidance
├── research.md          # Research output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
```

### Source Code
```text
tests/smoke/
├── conftest.py                       # Extended fixtures for equivalence testing
├── utils/
│   ├── data_equivalence.py           # NEW: Helper for array/label/semantic comparison
│   └── native_executor.py            # NEW: Run native scripts via conda run
├── reference_scripts/                # NEW: Native Python scripts per library (stdout JSON contract)
│   └── schema_dump.py                # NEW: Dump tool runtime meta.describe() to canonical JSON
│   ├── phasorpy_baseline.py
│   ├── skimage_baseline.py
│   ├── scipy_baseline.py
│   ├── xarray_baseline.py
│   ├── pandas_baseline.py
│   ├── matplotlib_baseline.py
│   └── cellpose_baseline.py
├── test_schema_alignment.py          # NEW: Schema self-consistency tests
├── test_equivalence_phasorpy.py      # NEW: PhasorPy equivalence
├── test_equivalence_skimage.py       # NEW: Scikit-image equivalence
├── test_equivalence_scipy.py         # NEW: SciPy equivalence
├── test_equivalence_xarray.py        # NEW: Xarray equivalence
├── test_equivalence_pandas.py        # NEW: Pandas equivalence
├── test_equivalence_matplotlib.py    # NEW: Matplotlib equivalence
└── test_equivalence_cellpose.py      # NEW: Cellpose equivalence
```

**Structure Decision**: Single project test extension. New files added under tests/smoke/ hierarchy.

## Complexity Tracking
- Constitution VI (TDD) addressed by making tasks explicitly "tests-first then implement".
