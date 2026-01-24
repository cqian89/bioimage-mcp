# Architecture Patterns: SciPy Dynamic Integration

**Domain:** Bioimage-MCP / SciPy Ecosystem
**Researched:** 2026-01-25
**Overall Confidence:** HIGH

## Recommended Architecture

SciPy integration follows the **Dynamic Adapter Pattern**, extending the existing Hub-and-Spoke model. Instead of hardcoded tool wrappers, a specialized `ScipyAdapter` uses reflection and docstring parsing to expose the SciPy ecosystem directly to the MCP server.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **ScipyAdapter** | Orchestrates discovery and execution for the `scipy.*` namespace. Maps MCP artifacts to NumPy arrays and vice versa. | `Introspector`, SciPy Submodules |
| **Introspector** | Extracts function signatures and NumPy-style docstrings using `numpydoc`. Maps Python types to JSON Schema. | SciPy functions |
| **Dynamic Dispatch** | Routes `fn_id`s with the `scipy` prefix to the `ScipyAdapter` within the `bioimage-mcp-base` worker. | MCP Server, ScipyAdapter |
| **Artifact Bridge** | Handles conversion between `BioImageRef` (OME-TIFF), `TableRef` (CSV), and `ObjectRef` (In-memory). | `bioio`, `pandas`, `tifffile` |

### Data Flow Changes

The SciPy integration introduces more diverse data flows compared to standard image-to-image tools:

1.  **Image-to-Image (ndimage/signal)**:
    - Input: `BioImageRef` -> loaded as `np.ndarray`.
    - Execution: `scipy.ndimage.gaussian_filter(array, ...)`
    - Output: Result saved as `BioImageRef` (OME-TIFF).
2.  **Image/Array-to-Scalar (stats)**:
    - Input: `BioImageRef` or `TableRef`.
    - Execution: `scipy.stats.skew(array)`
    - Output: Result returned as scalar in `metadata` or saved to a tiny `TableRef`.
3.  **Table-to-Table (spatial)**:
    - Input: `TableRef` (e.g., coordinates from Trackpy).
    - Execution: `scipy.spatial.distance.pdist(table.values)`
    - Output: Result saved as `TableRef` (CSV).
4.  **Constructor Pattern (spatial)**:
    - Execution: `scipy.spatial.KDTree(data)`
    - Output: Result stored in `ObjectCache` as an `ObjectRef` for subsequent neighbor queries.

## New Components

### 1. Generalized ScipyAdapter
A new, multi-module adapter replacing the prototype `ScipyNdimageAdapter`. It must handle:
- **Module Scanning**: Iterating `scipy.ndimage`, `scipy.signal`, `scipy.stats`, `scipy.spatial`, `scipy.optimize`, and `scipy.cluster`.
- **I/O Pattern Mapping**: Automatic assignment of `IOPattern` based on submodule and signature (e.g., functions returning `(p-value, statistic)` mapped to `ARRAY_TO_SCALAR`).

### 2. Enhanced Introspector Configuration
The `Introspector` requires specific tuning for SciPy:
- **Parameter Filtering**: Automatically hide advanced SciPy parameters like `output`, `mode`, `cval`, and `callback` to simplify the agent interface.
- **Axis Awareness**: A middleware component to map TCZYX dimension names to SciPy's integer `axis` indices.

## Patterns to Follow

### Pattern 1: Dimension Squeezing (T203)
SciPy functions typically expect 2D or 3D arrays. The adapter must use the `DimensionRequirement` hints to automatically squeeze singleton dimensions (T, C) from 5D BioImage artifacts before execution.

### Pattern 2: Result Normalization
SciPy's outputs are heterogeneous (ndarrays, named tuples, lists). The architecture uses a "Normalization Layer" to ensure all outputs are wrapped in a standard `Artifact` envelope.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Large Array Serialization
**Never** return raw SciPy arrays in the MCP response JSON.
**Instead:** Always save to OME-TIFF or CSV and return an `ArtifactRef`.

### Anti-Pattern 2: Global Object Cache Bloat
**Never** store every intermediate SciPy object (like KDTrees) indefinitely.
**Instead:** Use session-scoped `ObjectCache` with an explicit `mcp__base__object_clear` command for cleanup.

## Suggested Build Order

1.  **Phase 1: Adapter Generalization**: Refactor `ScipyNdimageAdapter` to handle `scipy.signal` and `scipy.ndimage` generically. Implement base `IOPattern.IMAGE_TO_IMAGE`.
2.  **Phase 2: Tabular/Scalar Bridge**: Implement `ARRAY_TO_SCALAR` and `TABLE_TO_TABLE` patterns. Add support for `scipy.stats` and `scipy.spatial.distance`.
3.  **Phase 3: Object Persistence**: Implement `ObjectRef` handling for `scipy.spatial.KDTree` and other stateful SciPy objects.
4.  **Phase 4: Agent Guidance**: Populate `DimensionRequirement` and `SuccessHints` for the top 30 most common SciPy bioimage functions.

## Sources
- `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` (Pattern Reference)
- `src/bioimage_mcp/registry/dynamic/introspection.py` (Core Engine)
- [SciPy Multidimensional Image Processing](https://docs.scipy.org/doc/scipy/tutorial/ndimage.html)
- [Bioimage-MCP v0.2.0 Architecture](.planning/research/ARCHITECTURE.md)
