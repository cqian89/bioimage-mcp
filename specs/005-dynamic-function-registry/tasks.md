# Tasks: Dynamic Function Registry

**Spec**: `specs/005-dynamic-function-registry/spec.md`
**Plan**: `specs/005-dynamic-function-registry/plan.md`
**Status**: Pending

## Phase 1: Setup
*Goal: Define data models and configuration structures.*

- [ ] T001 Define `DynamicSource` schema and add to `ToolManifest` in `src/bioimage_mcp/registry/manifest_schema.py` [FR-001]
- [ ] T002 Create `src/bioimage_mcp/registry/dynamic/models.py` with `FunctionMetadata`, `ParameterSchema`, `IOPattern` enum [FR-007]
- [ ] T003 Update `tools/base/manifest.yaml` with `dynamic_sources` configuration (skimage, phasorpy, scipy_ndimage) [FR-001]

## Phase 2: Foundational
*Goal: Implement core discovery, introspection, and adapter infrastructure. Blocking for all user stories.*

- [ ] T004 Create `BaseAdapter` protocol in `src/bioimage_mcp/registry/dynamic/adapters/__init__.py` [FR-002]
- [ ] T005 Implement `Introspector` class in `src/bioimage_mcp/registry/dynamic/introspection.py` with signature analysis [FR-007, FR-013]
- [ ] T005a [P] Implement docstring parsing using `numpydoc` in `src/bioimage_mcp/registry/dynamic/introspection.py` [FR-006]
- [ ] T006 Implement dynamic discovery engine in `src/bioimage_mcp/registry/dynamic/discovery.py` [FR-012, FR-017]
- [ ] T006a Add prefix uniqueness validation during manifest loading [FR-016]
- [ ] T007 Integrate dynamic discovery into `load_manifests` in `src/bioimage_mcp/registry/loader.py` [FR-008, FR-011]
- [ ] T007a Index discovered functions into SQLite registry (same as static functions) [FR-015]
- [ ] T008 [P] Implement caching for introspection results in `src/bioimage_mcp/registry/dynamic/cache.py` with lockfile-based invalidation [FR-009]
- [ ] T008a Create dynamic dispatch router in `tools/base/bioimage_mcp_base/dynamic_dispatch.py` [FR-008, FR-011]

## Phase 3: Calibrate FLIM Data (User Story 1)
*Goal: Enable FLIM calibration using `phasorpy`.*
*Priority: P1*

- [ ] T009 [P] [US1] Create `PhasorPyAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py` [FR-004]
- [ ] T010 [US1] Implement `phasor_from_signal` mapping with SIGNAL_TO_PHASOR pattern (returns intensity, G, S) [FR-004]
- [ ] T011 [US1] Implement `phasor_transform` mapping with PHASOR_TRANSFORM pattern [FR-004]
- [ ] T012 [US1] Configure `phasorpy` adapter in `tools/base/manifest.yaml` with prefix `phasorpy` [FR-001]
- [ ] T013 [US1] Create integration test `tests/integration/test_flim_calibration.py` using FLUTE dataset (Embryo.tif + Fluorescein_Embryo.tif) [FR-014]

## Phase 4: Access Image Filters (User Story 2)
*Goal: Expose standard `scikit-image` filters automatically.*
*Priority: P2*

- [ ] T014 [P] [US2] Create `SkimageAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` [FR-003]
- [ ] T015 [US2] Implement module-level I/O pattern inference with function-specific overrides [FR-003]
- [ ] T016 [US2] Configure `skimage` adapter in `tools/base/manifest.yaml` with prefix `skimage` [FR-001]
- [ ] T017 [US2] Create integration test `tests/integration/test_skimage_dynamic.py` verifying filter discovery and execution [FR-014]
- [ ] T017a [US2] Add contract test `tests/contract/test_skimage_adapter.py` for representative functions per I/O pattern [FR-014]

## Phase 5: Extensibility for New Libraries (User Story 3)
*Goal: Prove extensibility with `scipy.ndimage`.*
*Priority: P3*

- [ ] T018 [P] [US3] Create `ScipyNdimageAdapter` in `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` [FR-005]
- [ ] T019 [US3] Configure `scipy_ndimage` adapter in `tools/base/manifest.yaml` with prefix `scipy` [FR-001]
- [ ] T020 [US3] Create integration test `tests/integration/test_scipy_adapter.py` [FR-014]
- [ ] T020a [US3] Add contract test `tests/contract/test_scipy_adapter.py` [FR-014]

## Phase 6: Polish & Cross-Cutting
*Goal: Ensure robustness, performance, and documentation.*

- [ ] T021 Validate all discovered functions have non-empty descriptions: assert count(empty_description) == 0 [SC-005]
- [ ] T022 Add startup performance test: assert dynamic_discovery_overhead < 2s with warm cache [SC-003]
- [ ] T023 Run full regression suite to ensure no regressions in static tools [SC-006]
- [ ] T024 Add unit tests for graceful degradation: missing docstrings, unsupported types, import errors [FR-013, FR-017]
- [ ] T025 Verify adapter contract tests pass for all adapters (phasorpy, skimage, scipy_ndimage) [SC-007]

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
| T001-T003 | FR-001, FR-007 | - |
| T004 | FR-002 | - |
| T005, T005a | FR-006, FR-007, FR-013 | SC-005 |
| T006, T006a | FR-012, FR-016, FR-017 | - |
| T007, T007a | FR-008, FR-011, FR-015 | - |
| T008, T008a | FR-008, FR-009, FR-011 | SC-003 |
| T009-T013 | FR-004, FR-014 | SC-001, SC-004 |
| T014-T017a | FR-003, FR-014 | SC-002, SC-007 |
| T018-T020a | FR-005, FR-014 | SC-007 |
| T021 | - | SC-005 |
| T022 | - | SC-003 |
| T023 | - | SC-006 |
| T024 | FR-013, FR-017 | - |
| T025 | - | SC-007 |
