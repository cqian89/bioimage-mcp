# User Acceptance Tests - Phase 9: Spatial & Signal Processing

## Discovery & Routing
- [x] **Verify Spatial & Signal Tool Discovery**
  - **Action:** Run `bioimage-mcp list` and check for `scipy.spatial.*` and `scipy.signal.*`.
  - **Expected:** List includes `scipy.spatial.distance.cdist`, `scipy.spatial.Voronoi`, `scipy.spatial.Delaunay`, `scipy.signal.periodogram`, `scipy.signal.welch`, `scipy.signal.fftconvolve`.
  - **Status:** Passed (Verified via internal list command)

## Spatial Analysis
- [x] **Verify Distance Matrix (cdist)**
  - **Action:** Execute `scipy.spatial.distance.cdist` with two point sets.
  - **Expected:** Returns a distance matrix artifact.
  - **Status:** Passed (Returns NativeOutputRef .npy)

- [x] **Verify Tessellations (Voronoi/Delaunay)**
  - **Action:** Execute `scipy.spatial.Voronoi` or `scipy.spatial.Delaunay` on a point set.
  - **Expected:** Returns a structured JSON artifact containing vertices/regions/simplices.
  - **Status:** Passed (Returns NativeOutputRef .json)

## KDTree Lifecycle
- [x] **Verify KDTree Build (Persistence)**
  - **Action:** Execute `scipy.spatial.cKDTree` on a point set.
  - **Expected:** Returns an `ObjectRef` with a valid `obj://` URI and `ref_id`.
  - **Status:** Passed (Returns ObjectRef with ref_id)

- [x] **Verify KDTree Query**
  - **Action:** Execute query using the `ObjectRef` from the previous step.
  - **Expected:** Returns nearest neighbor distances and indices.
  - **Status:** Passed (Returns NativeOutputRef .json)

## Signal Processing
- [ ] **Verify Spectral Analysis (Periodogram)**
  - **Action:** Execute `scipy.signal.periodogram` on a 1D signal (string URI/path).
  - **Expected:** Returns a Table artifact with frequency and power columns.
  - **Status:** Failed
  - **Issue:** `Error executing tool run: string indices must be integers, not 'str'`. Suspect adapter receives string but expects dict, or internal validation issue.

- [ ] **Verify Convolution (fftconvolve)**
  - **Action:** Execute `scipy.signal.fftconvolve` on two images/signals.
  - **Expected:** Returns a convolved Image artifact.
  - **Status:** Blocked
  - **Issue:** Strict input validation accepts `BioImageRef | ObjectRef` but rejects `NativeOutputRef` (from cdist). Lack of test image data.
