# Implementation Plan: tttrlib Tool Pack Integration

**Branch**: `025-tttrlib` | **Spec**: [specs/025-tttrlib/proposal.md](proposal.md)

## 1. Summary

Integrate `tttrlib` into Bioimage-MCP as a specialized tool pack for Time-Tagged Time-Resolved (TTTR) data analysis. This integration provides a curated API for Fluorescence Correlation Spectroscopy (FCS), Image Correlation Spectroscopy (ICS), and Single Molecule Spectroscopy. It utilizes a new `TTTRRef` artifact for efficient photon stream handling and `ObjectRef` for stateful interactions with complex C++-backed objects.

### Technical Context
- **Language/Version**: Python 3.13 (core server); Python 3.12 (tttrlib tool env)
- **Primary Dependencies**: `tttrlib` (via conda `tpeulen` channel), `numpy`, `mcp`, `pydantic>=2.0`, `bioio`
- **Storage**: Local filesystem artifact store + SQLite index
- **Testing**: `pytest`, `pytest-asyncio` (TDD - tests first)
- **Target Platform**: Linux-first (due to C++ bindings); macOS best-effort
- **Project Type**: Tool Pack + Dynamic Adapter (manual schemas)
- **Performance Goals**: Minimal data copying; photon streams remain in tool env
- **Constraints**: SWIG-wrapped C++ library requires manual schema generation; no `inspect.signature` introspection

---

## 2. Artifact Definitions

### 2.1 TTTRRef
A dedicated artifact type for photon-stream files (PTU, HT3, SPC, HDF5). Metadata fields are best-effort and may be populated lazily when the file is opened in the tool environment.

```yaml
type: TTTRRef
fields:
  uri: string (file:// path)
  format: string (PTU, HT3, SPC-130, SPC-630_256, SPC-630_4096, HDF, CZ-RAW, SM)
  metadata:
    n_valid_events: integer (optional)
    used_routing_channels: array[integer] (optional)
    macro_time_resolution_s: number (optional)
    micro_time_resolution_s: number (optional)
```

---

## 3. Curated API Surface (v0)

### 3.1 tttrlib.TTTR (Constructor)
Opens a TTTR file and returns a reference.
- **Params**:
  - `filename`: (string, required) Path to TTTR file (must be readable per the server filesystem read allowlist; inherits client permissions).
  - `container_type`: (string, optional) One of `[PTU, HT3, SPC-130, SPC-630_256, SPC-630_4096, HDF, CZ-RAW, SM]`. Inferred if omitted.
- **Outputs**:
  - `tttr`: `TTTRRef`

### 3.2 tttrlib.TTTR.header
Extracts metadata header as JSON.
- **Inputs**:
  - `tttr`: `TTTRRef`
- **Outputs**:
  - `header`: `NativeOutputRef` (format: `json`)

### 3.3 tttrlib.TTTR.get_time_window_ranges
Burst selection based on count rate.
- **Inputs**:
  - `tttr`: `TTTRRef`
- **Params**:
  - `minimum_window_length`: (number, required) Minimum burst duration in seconds.
  - `maximum_window_length`: (number, optional) Maximum burst duration in seconds.
  - `minimum_number_of_photons_in_time_window`: (integer, required) Minimum photons per burst.
  - `maximum_number_of_photons_in_time_window`: (integer, optional)
  - `invert`: (boolean, default: `false`)
- **Outputs**:
  - `ranges`: `TableRef` (columns: `[start_index, stop_index]`)

### 3.4 tttrlib.Correlator
Performs multi-tau correlation.
- **Inputs**:
  - `tttr`: `TTTRRef`
- **Params**:
  - `channels`: (array[array[integer]], required) `[[ch1_list], [ch2_list]]` for cross-correlation. Example: `[[0], [8]]`.
  - `n_bins`: (integer, default: `17`)
  - `n_casc`: (integer, default: `25`)
  - `make_fine`: (boolean, default: `false`)
  - `method`: (string, enum: `[wahl, felekyan, laurence]`, default: `wahl`)
- **Outputs**:
  - `curve`: `TableRef` (columns: `[tau, correlation]`)

### 3.5 tttrlib.CLSMImage (Constructor)
Constructs a scanning image object from TTTR data.
- **Inputs**:
  - `tttr`: `TTTRRef`
- **Params**:
  - `reading_routine`: (string, enum: `[default, SP5, SP8]`, default: `default`)
  - `channels`: (array[integer])
  - `fill`: (boolean, default: `true`)
  - `n_pixel_per_line`: (integer, optional)
  - `n_lines`: (integer, optional)
  - `marker_frame_start`: (array[integer], optional)
  - `marker_line_start`: (integer, optional)
  - `marker_line_stop`: (integer, optional)
  - `skip_before_first_frame_marker`: (boolean, default: `true`)
- **Outputs**:
  - `clsm`: `ObjectRef` (python_class: `tttrlib.CLSMImage`)

### 3.6 tttrlib.CLSMImage.compute_ics
Image Correlation Spectroscopy on a scanning image.
- **Inputs**:
  - `clsm`: `ObjectRef`
- **Params**:
  - `x_range`: (array[integer], default: `[0, -1]`)
  - `y_range`: (array[integer], default: `[0, -1]`)
  - `subtract_average`: (string, enum: `[frame, stack, ""]`, default: `frame`)
  - `include_summary`: (boolean, default: `false`)
- **Outputs**:
  - `ics`: `BioImageRef`
  - `summary`: `TableRef` (optional, if `include_summary=true`)

### 3.7 tttrlib.TTTR.write
Exports TTTR data to a file (e.g., Photon-HDF5).
- **Inputs**:
  - `tttr`: `TTTRRef`
- **Params**:
  - `filename`: (string, required) Output path. Format inferred from extension. Relative paths write to the tool run work dir (artifact store); absolute paths are permitted only if allowed by the server filesystem write allowlist (inherits client permissions).
- **Outputs**:
  - `tttr`: `TTTRRef` (pointing to the new file)

---

## 4. Extended API (P1 Tier)

### 4.1 tttrlib.TTTR.get_intensity_trace
- **Inputs**: `tttr: TTTRRef`
- **Params**: `time_window_length` (number, default: `1.0`, seconds)
- **Outputs**: `trace: TableRef` (`[time_s, counts]`)
- **Schema hint**: `time_window_length` is in seconds (e.g., `0.010` for 10 ms); some upstream docs mention milliseconds, but the implementation (and tttrlib tests) treat this value as seconds (it is scaled against the macro-time resolution, which is in seconds).

### 4.2 tttrlib.TTTR.get_microtime_histogram
- **Inputs**: `tttr: TTTRRef`
- **Params**: `micro_time_coarsening` (integer, default: `1`)
- **Outputs**: `histogram: TableRef` (`[micro_time_ns, counts]`)

### 4.3 tttrlib.TTTR.get_selection_by_channel
- **Inputs**: `tttr: TTTRRef`
- **Params**: `channels` (array[integer])
- **Outputs**: `selection: TableRef` (`[index]`)

### 4.4 tttrlib.CLSMImage.intensity
- **Inputs**: `clsm: ObjectRef`
- **Outputs**: `image: BioImageRef`

### 4.5 tttrlib.CLSMImage.get_mean_micro_time
- **Inputs**: `clsm: ObjectRef`, `tttr: TTTRRef`
- **Params**: `microtime_resolution` (number, default: `-1.0`), `minimum_number_of_photons` (integer, default: `2`), `stack_frames` (boolean, default: `false`)
- **Outputs**: `mean_microtime: BioImageRef`

### 4.6 tttrlib.CLSMImage.get_phasor
- **Inputs**: `clsm: ObjectRef`, `tttr: TTTRRef`
- **Params**: `tttr_irf` (`TTTRRef`, optional), `frequency` (number, default: `-1`), `minimum_number_of_photons` (integer, default: `2`), `stack_frames` (boolean, default: `false`)
- **Outputs**: `phasor: BioImageRef` (4D array with g,s channels)

---

## 5. Implementation Phases

### Phase 1: Infrastructure & Artifacts (TDD)
- **Failing Tests**: `tests/unit/artifacts/test_tttrref.py` checking `TTTRRef` validation; `tests/contract/test_tttrlib_manifest.py` checking schema compliance; `tests/contract/test_tttrlib_env.py` checking environment+schema version alignment.
- **Steps**:
    1. Define `TTTRRef` in `src/bioimage_mcp/artifacts/models.py`.
    2. Create `envs/bioimage-mcp-tttrlib.lock.yml` (Python 3.12).
    3. Create `tools/tttrlib/manifest.yaml` with the Curated API schemas.
- **Verification**: `pytest tests/unit/artifacts/test_tttrref.py tests/contract/test_tttrlib_manifest.py tests/contract/test_tttrlib_env.py`

### Phase 2: TTTR Core & Metadata (TDD)
- **Failing Tests**: `tests/integration/test_tttr_core.py` verifying `tttrlib.TTTR` and `tttrlib.TTTR.header` on `bh_spc132.spc`.
- **Steps**:
    1. Implement `TttrlibAdapter` for isolated execution.
    2. Implement `tttrlib.TTTR` constructor and `tttrlib.TTTR.header`.
- **Verification**: `conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_tttr_core.py`

### Phase 3: FCS & Correlation (TDD)
- **Failing Tests**: `tests/integration/test_fcs.py` comparing MCP correlation output with reference values.
- **Steps**:
    1. Implement `tttrlib.Correlator`.
    2. Map numpy correlation results to `TableRef`.
- **Verification**: `conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_fcs.py`

### Phase 4: CLSM & ICS (TDD)
- **Failing Tests**: `tests/integration/test_clsm_ics.py` reconstructing an image and verifying ICS map shape.
- **Steps**:
    1. Implement `tttrlib.CLSMImage` constructor.
    2. Implement `tttrlib.CLSMImage.compute_ics`.
- **Verification**: `conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_clsm_ics.py`

### Phase 5: P1 Features & Export (TDD)
- **Failing Tests**: `tests/integration/test_tttr_p1.py` for intensity traces and Photon-HDF5 export.
- **Steps**:
    1. Implement P1 functions (4.1 - 4.6).
    2. Implement `tttrlib.TTTR.write`.
- **Verification**: `conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_tttr_p1.py`

### Phase 6: Smoke Tests & Integration (TDD)
- **Failing Tests**: `tests/smoke/test_tttrlib_live.py` with 4 smoke test cases (8.1-8.4).
- **Steps**:
    1. Implement smoke test fixtures for live server startup and dataset access.
    2. Implement `test_fcs_workflow` (8.1): Load SPC → Correlate → Verify TableRef.
    3. Implement `test_ics_workflow` (8.2): Load PTU → CLSMImage → compute_ics → Verify BioImageRef.
    4. Implement `test_burst_selection` (8.3): Load SPC → get_time_window_ranges → Verify TableRef.
    5. Implement `test_photon_hdf5` (8.4): Load HDF5 → header → write → Verify round-trip.
    6. Add `@pytest.mark.requires_env("bioimage-mcp-tttrlib")` markers.
    7. Add dataset skip markers if files are missing.
- **Acceptance Criteria**: All 4 smoke tests pass against a live MCP server with the tttrlib tool pack.
- **Verification**: `pytest tests/smoke/test_tttrlib_live.py -v`

---

## 6. Project Structure

#### Documentation (this feature)
```text
specs/025-tttrlib/
├── proposal.md           # Feature specification and decisions
├── plan.md               # This file
├── data-model.md         # TTTRRef and ObjectRef definitions
├── quickstart.md         # Usage examples
└── tasks.md              # Implementation task checklist
```

#### Source Code
```text
src/bioimage_mcp/
├── artifacts/
│   └── models.py                    # UPDATE: Add TTTRRef
├── registry/
│   └── dynamic/
│       └── adapters/
│           └── tttrlib.py            # NEW: TttrlibAdapter
│           └── tttrlib_schemas.py    # NEW: Manual function schemas
├── api/
│   └── schemas.py                   # UPDATE: Register TTTRRef

tools/tttrlib/
├── manifest.yaml                    # Tool identity and function schemas
├── bioimage_mcp_tttrlib/
│   ├── __init__.py
│   ├── entrypoint.py                # Object caching and dispatch
│   ├── tttr_ops.py                  # TTTR class wrappers
│   ├── correlator_ops.py            # Correlator wrappers
│   └── clsm_ops.py                  # CLSMImage wrappers
└── schema/
    └── tttrlib_api.json             # Versioned API schema file

envs/
├── bioimage-mcp-tttrlib.yaml        # Conda environment definition
└── bioimage-mcp-tttrlib.lock.yml    # Platform-specific lockfile

datasets/tttr-data/
├── README.md                        # Provenance and inventory
├── bh/bh_spc132.spc
├── imaging/leica/sp5/LSM_1.ptu
├── imaging/pq/ht3/pq_ht3_clsm.ht3   # Optional fallback
└── hdf/1a_1b_Mix.hdf5

tests/
├── contract/
│   ├── test_tttrlib_env.py          # Environment/lockfile checks
│   └── test_tttrlib_manifest.py     # Manifest schema validation
├── unit/
│   ├── artifacts/
│   │   └── test_tttrref.py          # TTTRRef model tests
│   └── registry/
│       └── test_tttrlib_adapter.py  # Adapter unit tests
├── integration/
│   ├── test_tttr_core.py            # TTTR load + header
│   ├── test_fcs.py                  # Correlator
│   ├── test_clsm_ics.py             # CLSMImage + ICS
│   └── test_tttr_p1.py              # P1 features
└── smoke/
    └── test_tttrlib_live.py         # Live server smoke tests
```

---

## 7. Constitution Compliance

| Principle | How it is satisfied |
|---|---|
| **I. Stable MCP Surface** | All `tttrlib` functions are curated with manual schemas in `manifest.yaml` to avoid SWIG introspection issues. |
| **II. Isolated Tool Execution** | `tttrlib` runs in a dedicated `bioimage-mcp-tttrlib` environment (Python 3.12). |
| **III. Artifact References Only** | Large photon streams use `TTTRRef`; intermediate state uses `ObjectRef`. Results use standard `TableRef`/`BioImageRef`. |
| **IV. Reproducibility** | Environment is pinned via `conda-lock`. All tool calls record parameters and input hashes. |
| **V. Safety** | Filesystem access is restricted via allowlists in the adapter. |
| **VI. TDD** | Failing integration tests are written for each phase before implementation. |

---

## 8. Smoke Test Specifications

### 8.1 Smoke: FCS Workflow
- **Dataset**: `datasets/tttr-data/bh/bh_spc132.spc`
- **Workflow**:
    1. `tttrlib.TTTR(filename=..., container_type="SPC-130")` -> `tttr`
    2. `tttrlib.Correlator(tttr=tttr, channels=[[0], [8]], n_bins=7, n_casc=27)` -> `curve`
- **Assertions**: `curve` is a `TableRef` with `tau` and `correlation` columns; `row_count > 0`.

### 8.2 Smoke: ICS Workflow
- **Dataset**: `datasets/tttr-data/imaging/leica/sp5/LSM_1.ptu`
- **Workflow**:
    1. `tttrlib.TTTR(filename=..., container_type="PTU")` -> `tttr`
    2. `tttrlib.CLSMImage(tttr=tttr, reading_routine="SP5", channels=[0])` -> `clsm`
    3. `tttrlib.CLSMImage.compute_ics(clsm=clsm, subtract_average="frame")` -> `ics`
- **Assertions**: `ics` is a `BioImageRef`; file exists on disk as OME-TIFF.

### 8.3 Smoke: Single-Molecule Burst Selection
- **Dataset**: `datasets/tttr-data/bh/bh_spc132.spc`
- **Workflow**:
    1. `tttrlib.TTTR(filename=..., container_type="SPC-130")` -> `tttr`
    2. `tttrlib.TTTR.get_time_window_ranges(tttr=tttr, minimum_window_length=0.002, minimum_number_of_photons_in_time_window=40)` -> `ranges`
- **Assertions**: `ranges` is a `TableRef` with `start_index`, `stop_index` columns; `row_count > 0`.

### 8.4 Smoke: Photon-HDF5 Import/Export
- **Dataset**: `datasets/tttr-data/hdf/1a_1b_Mix.hdf5`
- **Workflow**:
    1. `tttrlib.TTTR(filename=..., container_type="HDF")` -> `tttr_hdf`
    2. `tttrlib.TTTR.header(tttr=tttr_hdf)` -> `header_json`
    3. `tttrlib.TTTR.write(tttr=tttr_hdf, filename="exported.h5")` -> `tttr_exported`
- **Assertions**: `header_json` is a `NativeOutputRef` (json); `tttr_exported` is a `TTTRRef` pointing to a valid `.h5` file.

---

## 9. Dataset Requirements

Vendored minimal subset in `datasets/tttr-data/` via Git LFS:
- `bh/bh_spc132.spc`: Used for FCS and Burst Selection.
- `imaging/leica/sp5/LSM_1.ptu`: Used for ICS.
- `hdf/1a_1b_Mix.hdf5`: Used for Photon-HDF5 validation.

`datasets/tttr-data/README.md` must include:
- file inventory and which smoke test(s) use each file
- provenance (upstream repo URL + pinned commit hash)
- redistribution/license status (explicitly documented; do not assume)
- instructions for refreshing the subset from upstream

---

## 10. Manifest & Schema Structure

Stored in `tools/tttrlib/manifest.yaml` and `tools/tttrlib/schema/tttrlib_api.json`.
- **Adapter**: `TttrlibAdapter`
- **Environment**: `bioimage-mcp-tttrlib`
- **Schema Source-of-Truth**: `tools/tttrlib/schema/tttrlib_api.json` is versioned and records the upstream `tttrlib` version it was generated from.
- **Function Definitions**: `tools/tttrlib/manifest.yaml` references the curated API (Section 3 and 4) and stays consistent with the versioned schema file.
- **Drift Guard**: Contract tests assert schema version ↔ environment lockfile/package version alignment to prevent silent schema drift.

---

## 11. Verification Commands

```bash
# Contract tests (can run in core server env)
pytest tests/contract/test_tttrlib_*.py -v

# Unit tests (core server env)
pytest tests/unit/artifacts/test_tttrref.py tests/unit/registry/test_tttrlib_adapter.py -v

# Integration tests (requires tttrlib conda env)
conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_tttr_core.py -v
conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_fcs.py -v
conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_clsm_ics.py -v
conda run -n bioimage-mcp-tttrlib pytest tests/integration/test_tttr_p1.py -v

# Smoke tests (live server required)
pytest tests/smoke/test_tttrlib_live.py -v

# Full test suite
pytest tests/ -k tttrlib -v

# Lint check
ruff check src/bioimage_mcp/registry/dynamic/adapters/tttrlib*.py tools/tttrlib/

# Validate tool environment
python -m bioimage_mcp doctor --tool tttrlib
```

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Python 3.13 incompatibility with `tttrlib` | Isolated py312 environment; no core server dependency on tttrlib |
| SWIG obscures Python signatures | Manual schemas from documentation; version-pinned schema file |
| Photon-HDF5 writer unavailable | Implement `tttrlib.TTTR.write` but raise a clear "not supported in this build" error and skip export-dependent tests when writer support is missing |
| Large binary datasets | Git LFS; minimal vendored subset |
| Scan-marker variability across microscopes | Start with documented routines (SP5, SP8); add others incrementally |

---

## 13. Open Questions (Resolved in Proposal)

1. **Dataset storage**: Git LFS for `datasets/tttr-data/`
2. **Photon-HDF5 export**: Use upstream writer if available; defer if not
3. **Schema source**: Scrape tttrlib documentation for parameter definitions
