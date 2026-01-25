# Roadmap: Bioimage-MCP Scipy Integration (v0.3.0)

## Overview

Milestone v0.3.0 integrates the SciPy ecosystem into Bioimage-MCP using a **Dynamic Adapter Pattern**. This enables AI agents to perform advanced N-D image processing, statistical analysis, and spatial modeling through a single, secure interface. The milestone focuses on high-fidelity schema generation via `numpydoc` and memory-safe execution patterns.

## Milestone Status
- **Target:** v0.3.0
- **Phases:** 6-10 (follows v0.2.0)
- **Coverage:** 21/21 requirements mapped

---

## Phases

### Phase 6: Infrastructure & N-D Foundation
**Goal:** Establish the Scipy dynamic adapter and enable core image processing filters with native dimension preservation.
- **Dependencies:** None (v0.2.0 Core)
- **Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, NDIMG-01, NDIMG-02
- **Success Criteria:**
  - AI agent can list and describe 50+ `scipy.ndimage` functions via dynamic discovery.
  - Large uint16 images are automatically processed as `float32` to prevent overflow.
  - Image operations preserve native dimensions and physical resolution metadata (microns/ms).
  - Gaussian filters and morphology operations (dilation/erosion) return OME-TIFF artifacts.

### Phase 7: Transforms & Measurements
**Goal:** Enable coordinate-aware operations and analytical extraction from images.
- **Dependencies:** Phase 6
- **Requirements:** NDIMG-03, NDIMG-04, NDIMG-05
- **Success Criteria:**
  - Rotated or zoomed images retain physical pixel size metadata (microns/ms).
  - Labeling and center-of-mass measurements return JSON artifacts usable for downstream logic.
  - Fourier filters correctly handle complex-to-real transitions in image artifacts.

### Phase 8: Statistical Analysis
**Goal:** Bridge image measurements to scientific statistical testing.
- **Dependencies:** Phase 7
- **Requirements:** STATS-01, STATS-02, STATS-03
- **Success Criteria:**
  - Agent can execute T-tests and ANOVA on tabular artifacts generated from image measurements.
  - Summary statistics (mean, skew, kurtosis) are returned as structured scalar results.
  - Probability distributions (PDF/CDF) are accessible via dynamic introspection of `scipy.stats`.

### Phase 9: Spatial & Signal Processing
**Goal:** Support advanced spatial metrics and spectral signal analysis.
- **Dependencies:** Phase 8
- **Requirements:** SPATIAL-01, SPATIAL-02, SPATIAL-03, SIGNAL-01, SIGNAL-02
- **Success Criteria:**
  - Distance matrices (Euclidean/Mahalanobis) can be computed between point sets.
  - KDTree objects can be created and queried for nearest neighbors within a session.
  - Spectral analysis (Welch/Periodogram) can be performed on 1D signal artifacts.

### Phase 10: Verification & Smoke Testing
**Goal:** Ensure end-to-end reliability and parity with native Scipy results.
- **Dependencies:** Phase 9
- **Requirements:** TEST-01, TEST-02, TEST-03, TEST-04
- **Success Criteria:**
  - Live server passes automated smoke tests for all four major submodules.
  - MCP tool outputs for Gaussian blur and T-test match native Scipy script outputs bit-for-bit.
  - Synthetic and standard datasets are available for consistent test reproduction.

---

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 1-5 | v0.2.0 | ✅ Complete | 2026-01-25 |
| 6 - Infrastructure | v0.3.0 | 📋 Pending | — |
| 7 - Transforms | v0.3.0 | 📋 Pending | — |
| 8 - Statistics | v0.3.0 | 📋 Pending | — |
| 9 - Spatial/Signal | v0.3.0 | 📋 Pending | — |
| 10 - Verification | v0.3.0 | 📋 Pending | — |

---
*Roadmap generated: 2026-01-25*
