# Tasks: Dynamic Function Registry

**Spec**: `specs/005-dynamic-function-registry/spec.md`
**Plan**: `specs/005-dynamic-function-registry/plan.md`
**Status**: Pending

## TDD Workflow

Per Constitution Principle VI, all tasks follow **red-green-refactor**:

- `[RED]` tasks: Write a failing test that captures the expected behavior BEFORE implementation
- `[GREEN]` tasks: Write the minimum implementation code to make the test pass
- `[REFACTOR]` tasks: Improve code structure while keeping tests green

**Non-negotiable**: Implementation tasks (`[GREEN]`) MUST NOT begin until their corresponding `[RED]` test task is complete and failing.

## Phase 1: Setup
*Goal: Define data models and configuration structures.*

- [ ] T001a [RED] Write failing test for `DynamicSource` schema validation in `tests/unit/registry/test_dynamic_models.py` [FR-001]
- [ ] T001 [GREEN] Define `DynamicSource` schema and add to `ToolManifest` in `src/bioimage_mcp/registry/manifest_schema.py` [FR-001]
- [ ] T002a [RED] Write failing test for `FunctionMetadata`, `ParameterSchema`, `IOPattern` models [FR-007]
- [ ] T002 [GREEN] Create `src/bioimage_mcp/registry/dynamic/models.py` with `FunctionMetadata`, `ParameterSchema`, `IOPattern` enum [FR-007]
- [ ] T003a [RED] Write failing test for manifest loading with `dynamic_sources` section [FR-001]
- [ ] T003 [GREEN] Update `tools/base/manifest.yaml` with `dynamic_sources` configuration (skimage, phasorpy, scipy_ndimage) [FR-001]

## Phase 2: Foundational
*Goal: Implement core discovery, introspection, and adapter infrastructure. Blocking for all user stories.*

- [ ] T004a [RED] Write failing test for `BaseAdapter` protocol interface in `tests/unit/registry/test_adapters.py` [FR-002]
- [ ] T004 [GREEN] Create `BaseAdapter` protocol in `src/bioimage_mcp/registry/dynamic/adapters/__init__.py` [FR-002]
- [ ] T005a [RED] Write failing test for `Introspector` signature analysis in `tests/unit/registry/test_introspection.py` [FR-007, FR-013]
- [ ] T005 [GREEN] Implement `Introspector` class in `src/bioimage_mcp/registry/dynamic/introspection.py` with signature analysis [FR-007, FR-013]
- [ ] T005b [RED] Write failing test for docstring parsing using `numpydoc` [FR-006]
- [ ] T005c [GREEN] [P] Implement docstring parsing using `numpydoc` in `src/bioimage_mcp/registry/dynamic/introspection.py` [FR-006]
- [ ] T006a [RED] Write failing test for dynamic discovery engine in `tests/unit/registry/test_dynamic_discovery.py` [FR-012, FR-017]
- [ ] T006 [GREEN] Implement dynamic discovery engine in `src/bioimage_mcp/registry/dynamic/discovery.py` [FR-012, FR-017]
- [ ] T006b [RED] Write failing test for prefix uniqueness validation [FR-016]
- [ ] T006c [GREEN] Add prefix uniqueness validation during manifest loading [FR-016]
- [ ] T007a [RED] Write failing test for dynamic discovery integration into `load_manifests` [FR-008, FR-011]
- [ ] T007 [GREEN] Integrate dynamic discovery into `load_manifests` in `src/bioimage_mcp/registry/loader.py` [FR-008, FR-011]
- [ ] T007b [RED] Write failing test for SQLite indexing of discovered functions [FR-015]
- [ ] T007c [GREEN] Index discovered functions into SQLite registry (same as static functions) [FR-015]
- [ ] T008a [RED] Write failing test for introspection caching with lockfile invalidation [FR-009]
- [ ] T008 [GREEN] [P] Implement caching for introspection results in `src/bioimage_mcp/registry/dynamic/cache.py` with lockfile-based invalidation [FR-009]
- [ ] T008b [RED] Write failing test for dynamic dispatch router [FR-008, FR-011]
- [ ] T008c [GREEN] Create dynamic dispatch router in `tools/base/bioimage_mcp_base/dynamic_dispatch.py` [FR-008, FR-011]

## Phase 3: Calibrate FLIM Data (User Story 1)
*Goal: Enable FLIM calibration using `phasorpy`.*
*Priority: P1*

- [ ] T009a [RED] [US1] Write failing contract test for `PhasorPyAdapter` in `tests/contract/test_phasorpy_adapter.py` [FR-004, FR-014]
- [ ] T009 [GREEN] [P] [US1] Create `PhasorPyAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py` [FR-004]
- [ ] T010a [RED] [US1] Write failing test for `phasor_from_signal` SIGNAL_TO_PHASOR pattern [FR-004]
- [ ] T010 [GREEN] [US1] Implement `phasor_from_signal` mapping with SIGNAL_TO_PHASOR pattern (returns intensity, G, S) [FR-004]
- [ ] T011a [RED] [US1] Write failing test for `phasor_transform` PHASOR_TRANSFORM pattern [FR-004]
- [ ] T011 [GREEN] [US1] Implement `phasor_transform` mapping with PHASOR_TRANSFORM pattern [FR-004]
- [ ] T012a [RED] [US1] Write failing test for phasorpy adapter manifest configuration [FR-001]
- [ ] T012 [GREEN] [US1] Configure `phasorpy` adapter in `tools/base/manifest.yaml` with prefix `phasorpy` [FR-001]
- [ ] T013a [RED] [US1] Write failing integration test for FLIM calibration workflow using FLUTE dataset [FR-014]
- [ ] T013 [GREEN] [US1] Make integration test pass: `tests/integration/test_flim_calibration.py` (Embryo.tif + Fluorescein_Embryo.tif) [FR-014]

## Phase 4: Access Image Filters (User Story 2)
*Goal: Expose standard `scikit-image` filters automatically.*
*Priority: P2*

- [ ] T014a [RED] [US2] Write failing contract test for `SkimageAdapter` in `tests/contract/test_skimage_adapter.py` [FR-003, FR-014]
- [ ] T014 [GREEN] [P] [US2] Create `SkimageAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` [FR-003]
- [ ] T015a [RED] [US2] Write failing test for module-level I/O pattern inference [FR-003]
- [ ] T015 [GREEN] [US2] Implement module-level I/O pattern inference with function-specific overrides [FR-003]
- [ ] T016a [RED] [US2] Write failing test for skimage adapter manifest configuration [FR-001]
- [ ] T016 [GREEN] [US2] Configure `skimage` adapter in `tools/base/manifest.yaml` with prefix `skimage` [FR-001]
- [ ] T017a [RED] [US2] Write failing integration test for filter discovery and execution [FR-014]
- [ ] T017 [GREEN] [US2] Make integration test pass: `tests/integration/test_skimage_dynamic.py` [FR-014]

## Phase 5: Extensibility for New Libraries (User Story 3)
*Goal: Prove extensibility with `scipy.ndimage`.*
*Priority: P3*

- [ ] T018a [RED] [US3] Write failing contract test for `ScipyNdimageAdapter` in `tests/contract/test_scipy_adapter.py` [FR-005, FR-014]
- [ ] T018 [GREEN] [P] [US3] Create `ScipyNdimageAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` [FR-005]
- [ ] T019a [RED] [US3] Write failing test for scipy_ndimage adapter manifest configuration [FR-001]
- [ ] T019 [GREEN] [US3] Configure `scipy_ndimage` adapter in `tools/base/manifest.yaml` with prefix `scipy` [FR-001]
- [ ] T020a [RED] [US3] Write failing integration test for scipy adapter [FR-014]
- [ ] T020 [GREEN] [US3] Make integration test pass: `tests/integration/test_scipy_adapter.py` [FR-014]

## Phase 6: Validation & Regression
*Goal: Execute validation suite and ensure robustness. No new test writing—all tests written in earlier phases.*

- [ ] T021 [VALIDATE] Run validation: assert all discovered functions have non-empty descriptions (count == 0 empty) [SC-005]
- [ ] T022 [VALIDATE] Run startup performance test: assert dynamic_discovery_overhead < 2s with warm cache [SC-003]
- [ ] T023 [VALIDATE] Run full regression suite: ensure no regressions in static tools [SC-006]
- [ ] T024 [VALIDATE] Verify graceful degradation tests pass: missing docstrings, unsupported types, import errors [FR-013, FR-017]
- [ ] T025 [VALIDATE] Verify all adapter contract tests pass (phasorpy, skimage, scipy_ndimage) [SC-007]

## Dependencies

```
Phase 1 ──► Phase 2 ──┬──► Phase 3 (US1, P1)
                      │
                      ├──► Phase 4 (US2, P2)
                      │
                      └──► Phase 5 (US3, P3)
                      
                      All ──► Phase 6
```

- Phase 1 & 2 are prerequisites for all User Stories.
- US1 (PhasorPy) is independent of US2/US3.
- US2 (Skimage) and US3 (Scipy) share similar adapter patterns; US2 implementation likely informs US3.
- Phase 6 requires all previous phases complete.

## Implementation Strategy

1. **MVP**: Complete Phases 1, 2, and 3 (US1). This delivers the critical FLIM calibration capability.
2. **Expansion**: Complete Phase 4 (US2) to broaden utility with image filters.
3. **Validation**: Complete Phase 5 (US3) to validate the extensibility of the adapter system.
4. **Polish**: Complete Phase 6 for robustness and regression verification.

## Task-Requirement Traceability

| Task | Requirements | Success Criteria |
|------|--------------|------------------|
| T001a-T003 | FR-001, FR-007 | - |
| T004a-T004 | FR-002 | - |
| T005a-T005c | FR-006, FR-007, FR-013 | SC-005 |
| T006a-T006c | FR-012, FR-016, FR-017 | - |
| T007a-T007c | FR-008, FR-011, FR-015 | - |
| T008a-T008c | FR-008, FR-009, FR-011 | SC-003 |
| T009a-T013 | FR-001, FR-004, FR-014 | SC-001, SC-004 |
| T014a-T017 | FR-001, FR-003, FR-014 | SC-002, SC-007 |
| T018a-T020 | FR-001, FR-005, FR-014 | SC-007 |
| T021-T025 | - | SC-003, SC-005, SC-006, SC-007 |
