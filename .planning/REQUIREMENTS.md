# Requirements: Bioimage-MCP Scipy Integration

**Defined:** 2026-01-25
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Milestone:** v0.3.0

## v1 Requirements (v0.3.0)

Requirements for initial release. Each maps to roadmap phases.

### General / Infrastructure

- [x] **GEN-01**: Dynamic Adapter for Scipy module discovery (numpydoc support)
- [x] **GEN-02**: Access images via `BioImageRef.reader` (Native dimensions, no auto-squeezing)
- [x] **GEN-03**: Explicit `float32` output forcing for memory safety
- [x] **GEN-04**: Resolution-aware metadata preservation (pass-through)

### Testing & Verification

- [ ] **TEST-01**: Smoke tests mimicking tool calls on a live server
- [ ] **TEST-02**: Reference scripts based on real Scipy documentation examples
- [ ] **TEST-03**: Verification: Reference script output matches MCP output
- [ ] **TEST-04**: Data strategy: Use `datasets/` folder or synthetic data

### N-D Image Processing (`scipy.ndimage`)

- [x] **NDIMG-01**: Filters (Gaussian, Uniform, Laplace, Prewitt, Sobel)
- [x] **NDIMG-02**: Morphology (Dilation, Erosion, Opening, Closing, Tophat)
- [ ] **NDIMG-03**: Interpolation (Zoom, Rotate, Shift, Affine)
- [ ] **NDIMG-04**: Measurements (Labeling, Center of Mass, Extrema, Sum/Mean)
- [ ] **NDIMG-05**: Fourier Domain Filters (Fourier Gaussian, Ellipsoid)

### Statistics (`scipy.stats`)

- [ ] **STATS-01**: Summary Statistics (Describe, Mean, Skew, Kurtosis)
- [ ] **STATS-02**: Statistical Tests (T-test, ANOVA, KS-test)
- [ ] **STATS-03**: Probability Distributions (PDF/CDF access via introspection)

### Spatial Analysis (`scipy.spatial`)

- [ ] **SPATIAL-01**: Distance Metrics (Euclidean, Cosine, Mahalanobis)
- [ ] **SPATIAL-02**: KDTree / Nearest Neighbor Search (Query points against artifacts)
- [ ] **SPATIAL-03**: Tessellations (Voronoi, Delaunay)

### Signal Processing (`scipy.signal`)

- [ ] **SIGNAL-01**: N-D Convolutions (Convolve, Correlate)
- [ ] **SIGNAL-02**: Spectral Analysis (Periodogram, Welch)

## v2 Requirements

Deferred to future release.

- **CLUSTER-01**: K-Means clustering (`scipy.cluster`)
- **OPTIM-01**: Optimization recipes (`scipy.optimize`) - *unsafe for dynamic dispatch*

## Out of Scope

Explicitly excluded.

| Feature | Reason |
|---------|--------|
| Interactive Plotting | Use `matplotlib` adapter instead. |
| Sparse Matrices | No standard artifact format for sparse arrays yet. |
| Callback-based Optimization | Security risk in dynamic context. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GEN-01 | Phase 6 | Complete |
| GEN-02 | Phase 6 | Complete |
| GEN-03 | Phase 6 | Complete |
| GEN-04 | Phase 6 | Complete |
| TEST-01 | Phase 10 | Pending |
| TEST-02 | Phase 10 | Pending |
| TEST-03 | Phase 10 | Pending |
| TEST-04 | Phase 10 | Pending |
| NDIMG-01 | Phase 6 | Complete |
| NDIMG-02 | Phase 6 | Complete |
| NDIMG-03 | Phase 7 | Pending |
| NDIMG-04 | Phase 7 | Pending |
| NDIMG-05 | Phase 7 | Pending |
| STATS-01 | Phase 8 | Pending |
| STATS-02 | Phase 8 | Pending |
| STATS-03 | Phase 8 | Pending |
| SPATIAL-01 | Phase 9 | Pending |
| SPATIAL-02 | Phase 9 | Pending |
| SPATIAL-03 | Phase 9 | Pending |
| SIGNAL-01 | Phase 9 | Pending |
| SIGNAL-02 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-25*
*Last updated: 2026-01-25 start of v0.3.0*
