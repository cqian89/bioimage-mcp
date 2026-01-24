# Research Summary: Bioimage-MCP (Scipy Integration)

**Domain:** Bioimage Analysis / Scientific Computing
**Researched:** 2026-01-25
**Overall confidence:** HIGH

## Executive Summary

The v0.3.0 milestone for `bioimage-mcp` focuses on the **dynamic integration of the SciPy ecosystem**. By leveraging the established Hub-and-Spoke architecture, we are moving from hardcoded tool wrappers to a **Dynamic Adapter Pattern**. This allows the MCP server to automatically expose hundreds of validated scientific functions from `scipy.ndimage`, `scipy.signal`, `scipy.stats`, and `scipy.spatial` without manual code maintenance.

Research confirms that the existing **Artifact-based I/O** (OME-TIFF/CSV) is sufficient for SciPy integration, provided the `ScipyAdapter` handles dimension alignment (squeezing) and result normalization. The addition of `numpydoc` 1.10.0 enables high-fidelity parameter schema generation, significantly improving the AI agent's ability to use complex scientific functions correctly. The primary architectural challenge is managing the memory-intensive nature of Scipy's multidimensional algorithms on large bioimage datasets.

## Key Findings

- **Stack (STACK.md):** Recommends **SciPy 1.17.0** and **NumPy 2.2.2** on **Python 3.13**. **BioIO 3.2.0** is the standard for 5D (TCZYX) artifact I/O. **numpydoc 1.10.0** is essential for dynamic discovery, allowing the `Introspector` to generate tool schemas directly from Scipy's documentation.
- **Features (FEATURES.md):** Beyond table stakes like N-D filtering and morphology, the integration offers **Dynamic API Discovery** and **Dimension Autocorrection**. High-value differentiators include the **Coordinate-to-Index Bridge** for spatial analysis and a **Serializable "Measure" API**. Explicitly avoids unsafe optimization callbacks and interactive plotting.
- **Architecture (ARCHITECTURE.md):** Employs the **Dynamic Adapter Pattern**. The `ScipyAdapter` handles four primary data flows: Image-to-Image, Image/Array-to-Scalar, Table-to-Table, and Constructor Pattern (for stateful objects like `KDTree`). Key patterns include **Dimension Squeezing (T203)** and **Result Normalization** to handle heterogeneous Scipy outputs.
- **Pitfalls (PITFALLS.md):** Identified **Memory Exhaustion (OOM)** and **Implicit Dtype Escalation** (e.g., uint16 to float64) as critical risks. Return type mismatches and the loss of physical metadata (voxel sizes) are moderate risks that require mitigation in the adapter layer.

## Implications for Roadmap

Based on synthesized research, the suggested phase structure for v0.3.0 is:

1. **Phase 1: Adapter Hardening & Core Compute** — Generalize the `ScipyAdapter` to support `ndimage` and `signal`. Implement float32 forcing and memory-aware slicing to avoid OOM crashes.
   - *Rationale:* Stabilizes fundamental image-to-image tasks before expansion.
   - *Deliverables:* Gaussian/Uniform filters, morphology, interpolation.
2. **Phase 2: Analytic Expansion & Tabular Bridge** — Implement `ARRAY_TO_SCALAR` and `TABLE_TO_TABLE` patterns for `scipy.stats` and `scipy.spatial`.
   - *Rationale:* Analytical tools rely on the stable data loaders and normalization layers from Phase 1.
   - *Deliverables:* T-tests, ANOVA, pdist, distance metrics.
3. **Phase 3: Stateful Objects & Metadata Preservation** — Implement `ObjectRef` handling for `KDTree` and ensure physical units (microns/ms) are propagated through transforms.
   - *Rationale:* Addresses more advanced spatial analysis needs and ensures biological accuracy.
   - *Deliverables:* KDTree neighbor analysis, resolution-aware transforms.
4. **Phase 4: Agent Guidance & Success Hints** — Populate `DimensionRequirement` and `SuccessHints` for the top 50 common functions.
   - *Rationale:* Refines the agent experience once execution is robust.

### Research Flags
- **Needs Research:** Phase 3 (Object Persistence) needs a specific design for session-scoped `ObjectCache` cleanup to prevent memory leaks during long-running sessions.
- **Standard Patterns:** Phase 1 and 2 follow established adapter patterns already proven in the Skimage integration.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | SciPy 1.17.0 and NumPy 2.2.2 are current; BioIO is well-integrated. |
| Features | HIGH | Clear mapping of SciPy submodules to bioimage needs. |
| Architecture | HIGH | Follows proven `skimage`/`phasorpy` adapter patterns. |
| Pitfalls | HIGH | Specific OOM and dtype issues are well-documented and mitigated. |

### Gaps to Address
- **Dask Parallelization**: Future investigation into `dask-image` is needed for gigapixel volumes exceeding RAM.
- **Sparse Matrix Support**: Deferred due to lack of standard serializable artifact format.

## Sources
- [PyPI Scipy Release History](https://pypi.org/project/scipy/#history)
- [Scipy ndimage User Guide](https://docs.scipy.org/doc/scipy/tutorial/ndimage.html)
- [Bioimage-MCP Adapter Architecture](src/bioimage_mcp/registry/dynamic/adapters/base.py)
- [Image.sc Forum: Scipy Pitfalls](https://forum.image.sc/search?q=scipy%20pitfalls)
- [Numpydoc GitHub Releases](https://github.com/numpy/numpydoc/releases)

---
*Research synthesized: 2026-01-25*
*Status: Ready for roadmap*
