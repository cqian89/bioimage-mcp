# Tasks: PhasorPy Adapter Integration

## Dependencies & Execution Order
- Phase 1 (US1 MVP) → Phase 2 (US2 Visualization)
- Phase 1 (US1 MVP) → Phase 3 (US3 Multi-format)
- All Phases → Phase 4 (Polish)

## Parallel Example
Phase 1 tests can be run in parallel:
```bash
pytest tests/contract/test_phasorpy_discovery.py &
pytest tests/integration/test_phasorpy_workflow.py -k "sdt" &
```

Phase 2 contract tests can be run in parallel:
```bash
pytest tests/contract/test_plotref_artifact.py &
pytest tests/contract/test_phasor_metadata.py &
```

## Implementation Strategy
MVP First approach - complete Phase 1 (US1) to establish the end-to-end calibrated FLIM analysis workflow, then validate. Phase 1 includes dynamic discovery and SDT loading. Subsequent phases add visualization (US2) and broader format support (US3).

## Test Datasets
The following open-licensed datasets are available for integration testing:
- **SDT**: `datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt` - BSD 3-Clause, ~9.4MB (US1, US3)
- **TIFF/FLIM**: `datasets/FLUTE_FLIM_data_tif/Embryo.tif` - for phasor analysis (US1, US2)
- **PTU**: `datasets/ptu_hazelnut_flim/hazelnut_FLIM_single_image.ptu` - BSD 3-Clause, ~23MB (US3)
- **LIF**: `datasets/lif_flim_testdata/FLIM_testdata.lif` - CC-BY 4.0, ~35MB (US3)

## Phase 1: Discovery & Calibrated Analysis (US1 - MVP) 🎯
**Goal**: Load SDT file, calculate phasors, calibrate using Fluorescein standard. No dependency on PlotRef.
**Independent Test**: Load SDT file + reference lifetime → calibrated Phasor with G/S in [0,1].

### Tests (Red)
- [ ] T038 [P] [US1] Contract test verifying new IOPattern values (PHASOR_TO_SCALAR, etc.) and manifest updates in `tests/contract/test_phasorpy_discovery.py` (Pass: All patterns present; Fail: Missing patterns or manifest mismatch)
- [ ] T040 [P] [US1] Verification test ensuring `phasorpy.io` is NOT imported or used by the adapter in `tests/contract/test_phasorpy_discovery.py` (Pass: Zero functions discovered from `.io` module; Fail: Discovery includes IO functions)
- [ ] T041 [P] [US1] Allowlist enforcement verification (positive/negative) for SDT file reads in `tests/integration/test_phasorpy_workflow.py` (Pass: Reads from `datasets/` succeed, others fail with AccessDenied; Fail: Unauthorized reads allowed)
- [ ] T039 [P] [US1] Provenance recording verification (input hashes, parameters, tool version) in `tests/integration/test_phasorpy_workflow.py` (Pass: Metadata contains hashes and `phasorpy` version; Fail: Missing provenance fields)
- [ ] T009 [P] [US1] Contract test for ≥50 phasorpy functions discovered in `tests/contract/test_phasorpy_discovery.py` (Pass: Count >= 50; Fail: Count < 50)
- [ ] T010 [P] [US1] Contract test for describe_function schema in `tests/contract/test_phasorpy_discovery.py` (Pass: Schema matches Pydantic model; Fail: Validation error)
- [ ] T023 [P] [US1] Integration test for SDT file loading (datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt) in `tests/integration/test_phasorpy_workflow.py` (Pass: Normalized TCZYX artifact created; Fail: Loading error or axis mismatch)
- [ ] T011 [US1] Integration test for phasor_from_signal execution in `tests/integration/test_phasorpy_workflow.py` (Pass: G/S images generated; Fail: Execution error)
- [ ] T012 [US1] Integration test for phasor_calibrate execution in `tests/integration/test_phasorpy_workflow.py` (Pass: Calibrated phasor values in [0,1]; Fail: Uncalibrated or invalid values)

### Implementation (Green)
- [ ] T001 Add new IOPattern values (PHASOR_TO_SCALAR, SCALAR_TO_PHASOR, PLOT) in src/bioimage_mcp/registry/dynamic/models.py
- [ ] T002 Add phasorpy modules (`phasor`, `lifetime`, `plot`, `filter`, `cursor`, `component`) to tools/base/manifest.yaml
- [ ] T013 [US1] Implement full dynamic discovery in src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py
- [ ] T014 [US1] Implement tuple return handling for (mean, real, imag) in src/bioimage_mcp/registry/dynamic/introspection.py
- [ ] T015 [US1] Update dynamic_dispatch.py to unpack tuple outputs in tools/base/bioimage_mcp_base/dynamic_dispatch.py
- [ ] T016 [US1] Add dimension hints for axis parameter in src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py

**Checkpoint**: Calibrated FLIM analysis workflow (MVP) passes integration tests using SDT data.

## Phase 2: Visualization (US2) & PlotRef
**Goal**: Support PlotRef and PhasorMetadata for visualization and metabolic state analysis.
**Independent Test**: Run plot_phasor on Phasor artifact → PNG PlotRef accessible via get_artifact.

### Tests (Red)
- [ ] T003 [P] Contract test for PlotRef schema in `tests/contract/test_plotref_artifact.py` (Pass: Schema matches spec; Fail: Validation error)
- [ ] T004 [P] Contract test for PhasorMetadata in `tests/contract/test_phasor_metadata.py` (Pass: Schema matches spec; Fail: Validation error)
- [ ] T017 [P] [US2] Contract test for PlotRef output from plot functions in `tests/contract/test_phasorpy_discovery.py` (Pass: plot functions return PlotRef; Fail: Incorrect output mapping)
- [ ] T018 [US2] Integration test for plot_phasor execution in `tests/integration/test_phasorpy_workflow.py` (Pass: Tool returns PlotRef; Fail: Execution error)
- [ ] T019 [US2] Integration test for PlotRef artifact accessibility in `tests/integration/test_phasorpy_workflow.py` (Pass: Artifact readable as PNG; Fail: Inaccessible or corrupt)

### Implementation (Green)
- [ ] T005 Add PlotRef and PlotMetadata models in src/bioimage_mcp/artifacts/models.py
- [ ] T006 Add PhasorMetadata model in src/bioimage_mcp/artifacts/models.py
- [ ] T007 Register PlotRef in API schemas in src/bioimage_mcp/api/schemas.py
- [ ] T008 Implement write_plot() helper in src/bioimage_mcp/artifacts/store.py
- [ ] T020 [US2] Implement matplotlib figure capture (Agg backend) in tools/base/bioimage_mcp_base/dynamic_dispatch.py
- [ ] T021 [US2] Add PLOT IOPattern detection for phasorpy.plot functions in src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py
- [ ] T022 [US2] Connect PlotRef creation to write_plot() in artifact store in tools/base/bioimage_mcp_base/dynamic_dispatch.py

**Checkpoint**: Phasor plotting generates accessible PlotRef artifacts in PNG format.

## Phase 3: Multi-Format Normalization (US3)
**Goal**: Process PTU, LIF files into standardized BioImageRef.
**Independent Test**: Load PTU and LIF → both result in BioImageRef with TCZYX axes.

### Tests (Red)
- [ ] T024 [P] [US3] Integration test for PTU file loading (datasets/ptu_hazelnut_flim/hazelnut_FLIM_single_image.ptu) in `tests/integration/test_phasorpy_workflow.py` (Pass: PTU loads as TCZYX BioImageRef; Fail: Plugin error or axis mismatch)
- [ ] T025 [P] [US3] Integration test for LIF file loading (datasets/lif_flim_testdata/FLIM_testdata.lif) in `tests/integration/test_phasorpy_workflow.py` (Pass: LIF loads as TCZYX BioImageRef; Fail: Plugin error or axis mismatch)
- [ ] T026 [US3] Integration test for metadata preservation in `tests/integration/test_phasorpy_workflow.py` (Pass: frequency/harmonics present in PhasorMetadata; Fail: Missing metadata)

### Implementation (Green)
- [ ] T027 [US3] Ensure bioio-bioformats plugin handles PTU in tools/base requirements
- [ ] T028 [US3] Ensure bioio-lif plugin handles LIF in tools/base requirements
- [ ] T029 [US3] Add vendor format documentation (FR-006) in docs/tutorials/flim_phasor.md

**Checkpoint**: Vendor-specific FLIM formats (PTU/LIF) are successfully loaded and normalized to TCZYX BioImageRefs.

## Phase 4: Polish & Verification
**Goal**: Error handling, logging, and final success criteria verification.

### Tests (Red)
- [ ] T042 [P] Integration test for error translation in `tests/integration/test_phasorpy_workflow.py` (Pass: Invalid params return 4xx/5xx MCP errors; Fail: Unhandled 500 or raw traceback)
- [ ] T043 [P] Integration test for log capture in `tests/integration/test_phasorpy_workflow.py` (Pass: Function stdout/stderr appears in `LogRef` artifact; Fail: Missing logs)

### Implementation (Green)
- [ ] T030 [P] Implement phasorpy error translation to MCP error codes in src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py
- [ ] T031 [P] Add logging for phasorpy function executions in src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py

### Verification
- [ ] T032 Verify SC-001: ≥50 functions discovered via `pytest tests/contract/test_phasorpy_discovery.py`
- [ ] T033 Verify SC-002: Workflow <30 seconds via `pytest tests/integration/test_phasorpy_workflow.py -k performance`
- [ ] T034 Verify SC-003: Subprocess isolation handles crashes in `tests/integration/test_phasorpy_workflow.py`
- [ ] T035 Verify SC-004: All PlotRefs accessible via `get_artifact`
- [ ] T036 [P] Update quickstart.md verification examples (FR-006) in `specs/013-phasorpy-adaptor/quickstart.md`
- [ ] T037 Run full test suite: `pytest tests/`
