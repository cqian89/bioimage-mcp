# Tasks: 022-matplotlib-api

Implementation of the Matplotlib dynamic tool adapter and plotting artifact types for Bioimage-MCP.

**Input Spec**: `specs/022-matplotlib-api/spec.md`
**Prerequisites**: Phase 2 must be completed before any User Stories as it provides the foundational infrastructure.

**TDD Rule**: For every implementation task, the referenced tests must be written first and fail before implementation begins (Constitution VI).

## Format
- `T###`: Sequential Task ID.
- `[P]`: Tasks that can be executed in parallel.
- `[US#]`: User Story marker indicating a feature phase.

---

## Phase 1: Setup (TDD)
- [X] T001 [P] Write failing contract test asserting `envs/bioimage-mcp-base.yaml` declares `matplotlib>=3.8` in `tests/contract/test_matplotlib_env.py`
- [X] T002 [P] Update `envs/bioimage-mcp-base.yaml` with `matplotlib>=3.8`
- [X] T003 [P] Update `envs/bioimage-mcp-base.lock.yml` to reflect new dependencies

---

## Phase 2: Foundational (BLOCKS ALL STORIES)
*Goal: Core artifact models and the dynamic adapter infrastructure required for all plotting operations.*

- [X] T004 [P] Write failing unit tests for `FigureRef`, `AxesRef`, `AxesImageRef` + metadata models in `tests/unit/artifacts/test_matplotlib_refs.py`
- [X] T005 [P] Implement `FigureRef`, `AxesRef`, `AxesImageRef` and related metadata models in `src/bioimage_mcp/artifacts/models.py` (no PatchRef)
- [X] T006 [P] Write failing contract tests for `base.matplotlib.*` discovery + schema separation in `tests/contract/test_matplotlib_adapter_discovery.py`
- [X] T007 [P] Write failing unit tests for adapter safety (Agg enforced, interactive methods blocked, unknown functions rejected) in `tests/unit/registry/test_matplotlib_adapter.py`
- [X] T008 Implement Matplotlib allowlist/denylist + `MatplotlibAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py` and `src/bioimage_mcp/registry/dynamic/adapters/matplotlib.py`
- [X] T009 [P] Register plotting types in `src/bioimage_mcp/api/schemas.py` and update `tools/base/manifest.yaml` with `dynamic_source` for Matplotlib

**Checkpoint**: `pytest tests/unit/artifacts/test_matplotlib_refs.py tests/unit/registry/test_matplotlib_adapter.py tests/contract/test_matplotlib_adapter_discovery.py -v` passes.

---

## Phase 3: [Story] US1 - Create Intensity Histograms
*Goal: Visualize pixel intensity distributions for threshold selection.*

**Independent Test**: Load sample image → Generate histogram plot → Verify PNG shows intensity distribution matching image stats.

### Tests
- [ ] T010 [P] [US1] **Contract Test**: Define `base.matplotlib.hist` schema and verify discovery in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T011 [P] [US1] **Integration Test**: Call `base.matplotlib.hist` + `base.matplotlib.savefig`, verify a valid PlotRef in `tests/integration/test_us1_histograms.py` (include constant-image edge case: FR-016)

### Implementation
- [ ] T012 [US1] Implement `base.matplotlib.hist` execution in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T013 [US1] Support bin-count + TableRef column histogram inputs in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us1_histograms.py` passes.

---

## Phase 4: [Story] US2 - Overlay ROIs on Microscopy Images
*Goal: Draw detected regions (nuclei, cells) as graphical overlays.*

**Independent Test**: Load image + centroids → Render circles on image → Verify overlay positions match centroid coordinates.

### Tests
- [ ] T014 [P] [US2] **Contract Test**: Define `base.matplotlib.imshow` and `base.matplotlib.add_patch` schemas in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T015 [P] [US2] **Integration Test**: `imshow` + overlay patches + `savefig`, verify PlotRef and overlay placement in `tests/integration/test_us2_roi_overlays.py` (include out-of-bounds overlay clipping: FR-018; coordinate conventions: FR-020)

### Implementation
- [ ] T016 [US2] Implement `base.matplotlib.imshow` and ROI overlay patch support (`Circle`, `Rectangle`, etc.) in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T017 [US2] Enforce coordinate conventions + optional display downsampling (`max_display_size`): FR-019/FR-020 in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us2_roi_overlays.py` passes.

---

## Phase 5: [Story] US3 - Create Multi-Panel Comparison Figures
*Goal: Display multiple images side-by-side for comparison.*

**Independent Test**: Create 2-panel figure with raw and segmented images → Verify both panels are rendered.

### Tests
- [ ] T018 [P] [US3] **Contract Test**: Define `base.matplotlib.subplots` schema in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T019 [P] [US3] **Integration Test**: Create 1x2 figure with raw + segmented images and `savefig`, verify PlotRef contains both panels in `tests/integration/test_us3_subplots.py`

### Implementation
- [ ] T020 [US3] Implement `base.matplotlib.subplots` execution (returning AxesRef grid) in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T021 [US3] Route plotting calls to specific axes indices for multi-panel figures in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us3_subplots.py` passes.

---

## Phase 6: [Story] US4 - Plot Feature Relationships
*Goal: Scatter plots showing feature correlations.*

**Independent Test**: Load feature table → Generate scatter plot → Verify points are positioned according to table values.

### Tests
- [ ] T022 [P] [US4] **Contract Test**: Define `base.matplotlib.scatter` schema in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T023 [P] [US4] **Integration Test**: Load feature TableRef, create scatter + `savefig`, verify PlotRef and point mapping in `tests/integration/test_us4_scatter_plots.py` (include empty TableRef behavior: FR-017)

### Implementation
- [ ] T024 [US4] Implement `base.matplotlib.scatter` execution for TableRef inputs in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T025 [US4] Map TableRef columns to x/y/color/size parameters in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us4_scatter_plots.py` passes.

---

## Phase 7: [Story] US5 - Visualize Time-Series Data
*Goal: Line plots for kinetic experiments.*

**Independent Test**: Load time-series artifact → Generate line plot → Verify continuous trace over time.

### Tests
- [ ] T026 [P] [US5] **Contract Test**: Define `base.matplotlib.plot` schema in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T027 [P] [US5] **Integration Test**: Load time-series TableRef, create line plot + `savefig`, verify PlotRef trace continuity in `tests/integration/test_us5_time_series.py`

### Implementation
- [ ] T028 [US5] Implement `base.matplotlib.plot` execution (line/markers) for TableRef inputs in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T029 [US5] Handle temporal axes (labels/units) from time-series metadata in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us5_time_series.py` passes.

---

## Phase 8: [Story] US6 - Export Publication-Quality Figures
*Goal: Save as PNG/SVG/PDF/JPG at high resolution.*

**Independent Test**: Create figure → Save in each format (PNG, SVG, PDF, JPG) → Verify files are valid and high-resolution.

### Tests
- [ ] T030 [P] [US6] **Contract Test**: Update `base.matplotlib.savefig` with format and DPI parameters in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T031 [P] [US6] **Integration Test**: Create figure, save in each format, verify files are valid and high-res in `tests/integration/test_us6_export.py`

### Implementation
- [ ] T032 [US6] Implement `base.matplotlib.savefig` execution in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py` (PNG/SVG/PDF/JPG) and materialize PlotRef
- [ ] T033 [US6] Support `dpi` + `transparent` and enforce auto-close after `savefig` (FR-008) in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us6_export.py` passes.

---

## Phase 9: [Story] US7 - Display Statistical Distributions
*Goal: Box/violin plots for comparing treatment groups.*

**Independent Test**: Load grouped feature data → Generate boxplot → Verify median and quartiles are correctly displayed.

### Tests
- [ ] T034 [P] [US7] **Contract Test**: Define `base.matplotlib.boxplot` and `base.matplotlib.violinplot` schemas in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T035 [P] [US7] **Integration Test**: Load grouped data, create box/violin plots + `savefig`, verify PlotRef contains expected elements in `tests/integration/test_us7_stats_plots.py`

### Implementation
- [ ] T036 [US7] Implement `base.matplotlib.boxplot` + `base.matplotlib.violinplot` execution for TableRef inputs in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T037 [US7] Handle categorical grouping for distribution plotting in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us7_stats_plots.py` passes.

---

## Phase 10: [Story] US8 - Visualize Z-Stack Profiles
*Goal: Intensity profiles across focal planes.*

**Independent Test**: Compute Z-slice means from Z-stack → Generate line plot → Verify profile shape matches intensity across planes.

### Tests
- [ ] T038 [P] [US8] **Contract Test**: Verify Z-profile axis slicing schema in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T039 [P] [US8] **Integration Test**: Compute Z-slice means, create line plot, verify Z-profile shape in `tests/integration/test_us8_z_profiles.py`

### Implementation
- [ ] T040 [US8] Implement intensity profiling + plotting over Z in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T041 [US8] Label Z-axis with physical units (when available) using BioImage metadata in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`

**Checkpoint**: `pytest tests/integration/test_us8_z_profiles.py` passes.

---

## Final Phase: Polish & Required Coverage
- [ ] T042 [P] Expand security regression tests for allowlist/denylist safety (blocked interactive + dangerous APIs) in `tests/unit/registry/test_matplotlib_adapter.py`
- [ ] T043 [P] Write failing contract + integration tests for axes styling, annotations, and colorbar (FR-012/FR-013/FR-014) in `tests/contract/test_matplotlib_adapter_discovery.py` and `tests/integration/test_matplotlib_axes_features.py`
- [ ] T044 Implement axes styling (`set_title`, `set_xlabel`, `set_ylabel`, `set_xlim`, `set_ylim`, `grid`, `tick_params`), annotation/text, and `colorbar` execution in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py`
- [ ] T045 [P] Perform memory leak stress test (generating 100+ figures in a single session) in `tests/integration/test_matplotlib_memory_leak.py`
- [ ] T046 [P] Write failing integration test for `session_export`/`session_replay` determinism (FR-021) in `tests/integration/test_matplotlib_session_replay.py`
- [ ] T047 [P] Write failing contract test asserting `list` exposes ≥200 curated `base.matplotlib.*` functions (FR-015) in `tests/contract/test_matplotlib_adapter_discovery.py`
- [ ] T048 Implement curated function catalog organization + counts via `src/bioimage_mcp/registry/dynamic/adapters/matplotlib_allowlists.py` and `src/bioimage_mcp/registry/dynamic/adapters/matplotlib.py`
- [ ] T049 Fix any missing plotting-step recording needed for deterministic replay (FR-021) in `src/bioimage_mcp/runs/recorder.py`
- [ ] T050 Final end-to-end validation with `python scripts/validate_pipeline.py`

---

## Dependencies & Execution Order
1. **Phase 1 & 2** are strictly required before any User Stories as they provide the base infrastructure.
2. **US1, US2, US4, US5** are independent features that can be developed in parallel following Phase 2.
3. **US3** (Subplots) depends on the core plotting logic in **US1/US2**.
4. **US6** (Export) can be implemented any time after a basic figure can be generated (US1) and MUST enforce auto-close after savefig (FR-008).
5. **US7 & US8** are lower priority extensions of the plotting toolkit.
6. **Required coverage tasks**: T043/T044 (FR-012/013/014), T047/T048 (FR-015), and T046/T049 (FR-021) MUST be completed before considering the feature complete; they can run any time after Phase 2.
7. **Final validation**: T050 runs after all core tasks are green.

---

## Parallel Example: US1 (Intensity Histograms)
Developers can work on the following in parallel:
- **Dev A**: Define the Pydantic schema for `base.matplotlib.hist` and the contract test in `tests/contract/test_matplotlib_adapter_discovery.py`.
- **Dev B**: Set up the integration test in `tests/integration/test_us1_histograms.py` using expected output formats.

---

## Implementation Strategy
- **MVP First**: Prioritize the `Agg` backend and PNG export for basic `FigureRef` functionality.
- **Incremental Delivery**: Deliver plotting tools one by one (Hist -> Imshow -> Scatter).
- **Security First**: Maintain a strict allowlist of Matplotlib functions to ensure the dynamic adapter is safe from exploit.

---

## Notes
- Matplotlib must be configured to run in `Agg` (non-interactive) mode for all tool environments.
- Figures must be managed within the MCP session context and persisted as artifacts before the session closes.
- ROI coordinate systems must strictly follow `bioio` conventions (origin at top-left, units in pixels or physical as specified).
