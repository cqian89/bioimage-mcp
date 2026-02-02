# Phase 18 UAT: Artifact Store Retention and Quota Management

## Test List

- [x] **Test 1: CLI Storage Status**
  - **Action**: Run `bioimage-mcp status`
  - **Expected**: Displays used bytes, quota (default 100GB), usage %, and "Last Cleanup" summary.
- [x] **Test 2: Artifact Pinning**
  - **Action**: Pin an existing artifact using `bioimage-mcp pin <ref_id>`, then check `status` or `artifact_info`.
  - **Expected**: Artifact is marked as pinned and becomes exempt from cleanup (expiration info in `artifact_info` should be null/absent for pinned artifacts).
- [x] **Test 3: Manual Cleanup Dry-Run**
  - **Action**: Run `bioimage-mcp cleanup --dry-run`
  - **Expected**: Reports what *would* be deleted (if anything is eligible) without actually deleting files.
- [x] **Test 4: Retention Metadata Visibility**
  - **Action**: Call `artifact_info` for a non-pinned artifact.
  - **Expected**: Output includes `retention_expires_at` or similar cleanup metadata.
- [x] **Test 5: Background Cleanup Initialization**
  - **Action**: Run `bioimage-mcp serve --stdio` (briefly) or check logs if available.
  - **Expected**: Background cleanup thread starts without errors.

## Results

| Test | Status | Notes |
|------|--------|-------|
| Test 1 | Pass | User confirmed status output |
| Test 2 | Pass | User confirmed pinning functionality |
| Test 3 | Pass | User confirmed manual cleanup dry-run |
| Test 4 | Pass | User confirmed retention metadata visibility |
| Test 5 | Pass | User confirmed background thread initialization |
