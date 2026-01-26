# Roadmap: Bioimage-MCP Scipy Integration (v0.3.0)

## Overview

Milestone v0.3.0 integrates the SciPy ecosystem into Bioimage-MCP using a **Dynamic Adapter Pattern**. This enables AI agents to perform advanced N-D image processing, statistical analysis, and spatial modeling through a single, secure interface. The milestone focuses on high-fidelity schema generation via `numpydoc` and memory-safe execution patterns.

## Milestone Status
- **Target:** v0.3.0
- **Phases:** 6-10 (follows v0.2.0)
- **Coverage:** 21/21 requirements mapped

---

## Phases

### Phase 5.1: Research Dynamic Discovery Standardization (INSERTED)

**Goal:** Research and standardize dynamic discovery implementations across packages.
**Depends on:** Phase 5
**Plans:** 6 plans

Plans:
- [x] 05.1-01-PLAN.md — Define canonical meta.list/meta.describe protocol + audit matrix
- [x] 05.1-02-PLAN.md — Add core protocol parsers and wire into loader/discovery
- [x] 05.1-03-PLAN.md — Align trackpy meta.* responses + hermetic unit tests
- [x] 05.1-04-PLAN.md — Align cellpose meta.* responses + hermetic unit tests
- [x] 05.1-05-PLAN.md — Gap closure: include tool_version + introspection_source in CLI list output
- [x] 05.1-06-PLAN.md — Gap closure: persist module/io_pattern and expose in MCP list output

**Details:**
It seems dynamic discovery is implemmented via different methods in different packages via meta.list and meta.describe. Confirm whether this is the case. Research and Compare the implementations to see the similarities and differences. Consider standardization to an single discovery method.

### Phase 6: Infrastructure & N-D Foundation
**Goal:** Establish the Scipy dynamic adapter and enable core image processing filters with native dimension preservation.
- **Dependencies:** None (v0.2.0 Core)
- **Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, NDIMG-01, NDIMG-02
- **Success Criteria:**
  - AI agent can list and describe 50+ `scipy.ndimage` functions via dynamic discovery.
  - Large uint16 images are automatically processed as `float32` to prevent overflow.
  - Image operations preserve native dimensions and physical resolution metadata (microns/ms).
  - Gaussian filters and morphology operations (dilation/erosion) return OME-TIFF artifacts.

**Plans:** 4 plans

Plans:
- [x] 06-01-PLAN.md — Rich subprocess discovery for dynamic sources
- [x] 06-02-PLAN.md — Harden scipy.ndimage discovery (blacklist + deprecated filtering)
- [x] 06-03-PLAN.md — Scipy N-D execution infrastructure (dtype safety, auxiliary artifacts, callable allowlist)
- [x] 06-04-PLAN.md — Gap closure: preserve physical pixel sizes in written OME-TIFF metadata

### Phase 7: Transforms & Measurements
**Goal:** Enable coordinate-aware operations and analytical extraction from images.
- **Dependencies:** Phase 6
- **Requirements:** NDIMG-03, NDIMG-04, NDIMG-05
- **Success Criteria:**
  - Rotated or zoomed images retain physical pixel size metadata (microns/ms).
  - Labeling and center-of-mass measurements return JSON artifacts usable for downstream logic.
  - Fourier filters correctly handle complex-to-real transitions in image artifacts.

**Plans:** 4 plans

Plans:
- [x] 07-01-PLAN.md — Add IO patterns for JSON + multi-output labeling
- [x] 07-02-PLAN.md — Implement zoom metadata updates and transform pass-through
- [x] 07-03-PLAN.md — Implement labeling + measurement JSON schemas
- [x] 07-04-PLAN.md — Add complex Fourier artifact support + expose scipy.fft

### Phase 8: Statistical Analysis
**Goal:** Bridge image measurements to scientific statistical testing.
- **Dependencies:** Phase 7
- **Requirements:** STATS-01, STATS-02, STATS-03
- **Success Criteria:**
  - Agent can execute T-tests and ANOVA on tabular artifacts generated from image measurements.
  - Summary statistics (mean, skew, kurtosis) are returned as structured scalar results.
  - Probability distributions (PDF/CDF) are accessible via dynamic introspection of `scipy.stats`.

**Plans:** 3 plans

Phases:
- [x] 08-01-PLAN.md — Add stats IOPatterns + scipy adapter routing + enable scipy.stats discovery
- [ ] 08-02-PLAN.md — Implement scipy.stats wrappers (summary/tests) + distribution methods with JSON outputs
- [ ] 08-03-PLAN.md — Add contract + unit tests for scipy.stats discovery and execution

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
| 5.1 - Discovery | v0.3.0 | ✅ Complete | 2026-01-25 |
| 6 - Infrastructure | v0.3.0 | ✅ Complete | 2026-01-25 |
| 7 - Transforms | v0.3.0 | ✅ Complete | 2026-01-26 |
| 8 - Statistics | v0.3.0 | 🚧 In progress | 2026-01-26 |
| 9 - Spatial/Signal | v0.3.0 | 📋 Pending | — |
| 10 - Verification | v0.3.0 | 📋 Pending | — |

---
*Roadmap generated: 2026-01-25*
