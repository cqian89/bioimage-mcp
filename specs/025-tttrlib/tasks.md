# Implementation Tasks: tttrlib Integration

## Summary
- Total tests: 45 (41 passed, 4 skipped)
- All phases complete
- Note that smoke tests skip gracefully without real TTTR datasets

## Status Legend
- ✅ Complete
- 🔄 In Progress  
- ⏳ Pending

## Phase 1: Infrastructure & Artifacts
- ✅ [x] Define TTTRRef in models.py
- ✅ [x] Create bioimage-mcp-tttrlib.yaml environment
- ✅ [x] Create tools/tttrlib/manifest.yaml
- ✅ [x] Create tools/tttrlib/schema/tttrlib_api.json
- ✅ [x] Write contract tests

## Phase 2: TTTR Core & Metadata
- ✅ [x] Implement TttrlibAdapter
- ✅ [x] Implement tttrlib entrypoint
- ✅ [x] Implement tttrlib.TTTR constructor
- ✅ [x] Implement tttrlib.TTTR.header
- ✅ [x] Write integration tests

## Phase 3: FCS & Correlation
- ✅ [x] Implement tttrlib.Correlator
- ✅ [x] Map correlation results to TableRef
- ✅ [x] Write FCS integration tests

## Phase 4: CLSM & ICS
- ✅ [x] Implement tttrlib.CLSMImage constructor
- ✅ [x] Implement tttrlib.CLSMImage.compute_ics
- ✅ [x] Write CLSM/ICS integration tests

## Phase 5: P1 Features & Export
- ✅ [x] Implement tttrlib.TTTR.get_intensity_trace
- ✅ [x] Implement tttrlib.TTTR.get_microtime_histogram
- ✅ [x] Implement tttrlib.TTTR.get_selection_by_channel
- ✅ [x] Implement tttrlib.CLSMImage.intensity
- ✅ [x] Implement tttrlib.TTTR.write
- ✅ [x] Write P1 integration tests

## Phase 6: Smoke Tests & Documentation
- ✅ [x] Create smoke test fixtures
- ✅ [x] Implement FCS workflow smoke test
- ✅ [x] Implement ICS workflow smoke test
- ✅ [x] Implement burst selection smoke test
- ✅ [x] Implement Photon-HDF5 smoke test
- ✅ [x] Create datasets README
- ✅ [x] Create quickstart documentation

## Verification
- ⏳ [ ] Create conda-lock lockfile (pending - requires manual step)
- ⏳ [ ] Run full test suite in tttrlib env (pending - requires real datasets)
- ⏳ [ ] Run smoke tests with real datasets (pending - requires real datasets)
