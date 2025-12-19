# Tasks: Base Tool Schema Expansion

Each task must be completed in order unless marked with [P] (Parallel).
Check off tasks as they are completed.

## Phase 1: Setup
- [ ] T001 Create `tools/base/` directory structure with `__init__.py` and `entrypoint.py`
- [ ] T002 Copy `specs/002-base-tool-schema/contracts/base-manifest.yaml` to `tools/base/manifest.yaml`
- [ ] T003 Ensure `bioimage_mcp/registry` maps `tools.base` to the new directory (verify `src/bioimage_mcp/config.py` or registry loading logic)

## Phase 2: Foundational (Schema Cache & Discovery)
- [ ] T004 Implement `SchemaCache` class in `src/bioimage_mcp/registry/schema_cache.py` (implementing local JSON persistence per `data-model.md`)
- [ ] T005 Update `DiscoveryService.describe_function` in `src/bioimage_mcp/api/discovery.py` to check cache, trigger `meta.describe`, and update cache
- [ ] T006 Ensure `schema_cache.json` path is correctly configured in `src/bioimage_mcp/config.py`

## Phase 3: User Story 1 - Get complete function details on demand
- [ ] T007 [US1] Create integration test `tests/integration/test_discovery_enrichment.py` to verify caching behavior (contract test)
- [ ] T008 [US1] Implement `meta.describe` handler in `tools/base/entrypoint.py` using `runtimes.introspect`
- [ ] T009 [US1] Verify `models.py` allows optional schemas in `ToolManifest` but enforces them in `Function` response

## Phase 4: User Story 2 - Build workflows using a richer base toolkit
- [ ] T010 [US2] Create `tests/contract/test_base_tools.py` to verify all `tools.base` functions are discoverable and identifiable
- [ ] T011 [P] [US2] Implement Image I/O functions (`convert_to_ome_zarr`, `export_ome_tiff`) in `tools/base/io.py`
- [ ] T012 [P] [US2] Implement Transform functions (`resize`, `rescale`, `rotate`, `flip`, `crop`, `pad`) in `tools/base/transforms.py`
- [ ] T013 [P] [US2] Implement Projection functions (`project_sum`, `project_max`) in `tools/base/transforms.py`
- [ ] T014 [P] [US2] Implement Filter functions (`gaussian`, `median`, `bilateral`, `sobel`) in `tools/base/preprocess.py`
- [ ] T015 [P] [US2] Implement Denoise/Enhance functions (`denoise_nl_means`, `unsharp_mask`, `equalize_adapthist`) in `tools/base/preprocess.py`
- [ ] T016 [P] [US2] Implement Segmentation/Morphology functions (`threshold_otsu`, `threshold_yen`, `morph_opening`, `morph_closing`, `remove_small_objects`) in `tools/base/preprocess.py`
- [ ] T017 [US2] Update `tools/base/entrypoint.py` to register and dispatch all new functions

## Phase 5: User Story 3 - Validate a live end-to-end workflow
- [ ] T018 [US3] Create `tests/integration/test_live_workflow.py` framework
- [ ] T019 [US3] Implement logic to skip test if `bioimage-mcp-base` or `bioimage-mcp-cellpose` envs are missing
- [ ] T020 [US3] Implement test case: Load `hMSC-ZOOM.tif` -> `project_sum` -> `cellpose.segment` -> Verify Label Output
- [ ] T021 [US3] Ensure provenance and artifact metadata are correctly recorded for the run
- [ ] T022 [US3] Verify output isolation logic to ensure concurrent runs do not overwrite artifacts (FR-009)

## Phase 6: Polish
- [ ] T023 Create `specs/002-base-tool-schema/base-function-catalog.md` documenting the new functions
- [ ] T024 Update `quickstart.md` with examples of using base tools
- [ ] T025 Document provenance of `datasets/FLUTE_FLIM_data_tif` in `datasets/README.md` or similar (FR-012)
- [ ] T026 Perform final code review and lint check

## Dependencies
- Phase 1 & 2 blocks Phase 3, 4, 5.
- Phase 3 blocks Phase 5 (need schema enrichment to describe functions for workflow?). Actually US2 describes tools too. US3 consumes them.
- US1 and US2 can theoretically look parallel but US2 implementation needs `meta.describe` from US1 to be fully compliant with the new system, OR we can implement functions first then add describing capability. I put them sequentially for clarity.

## Implementation Strategy
- Build the machinery (US1) first to ensure we can describe what we're about to build.
- Then populate the library (US2).
- Then prove it works end-to-end (US3).
