# Phase 9 Issues & Gaps

## Gaps
1. **String-to-BioImageRef Normalization:**
   - `scipy.signal.fftconvolve` failed when passed raw file paths strings, while `scipy.signal.periodogram` (table-based) succeeded.
   - **Impact:** Inconsistent UX; users must construct full `BioImageRef` dicts for images but can use paths for tables.
   - **Fix:** Implement string-to-artifact normalization in `ScipyNdimageAdapter` (or base `ScipyAdapter`) for `BioImageRef` inputs, mirroring `PandasAdapter`.

## Severity
- **Gap 1:** Low/Medium (UX consistency). Core functionality works.

## Verification
- All UAT tests passed (with workaround for Gap 1).
- Core Spatial/Signal requirements met.
