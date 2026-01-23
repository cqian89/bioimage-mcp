# Phase 5: Trackpy Integration - Research

**Researched:** 2026-01-23
**Domain:** Particle tracking, single-molecule localization microscopy (SMLM), trajectory analysis.
**Confidence:** HIGH

## Summary

Phase 5 involves integrating the `trackpy` library (v0.7.x) into `bioimage-mcp` as a dedicated tool pack. `trackpy` is the industry standard for Crocker-Grier based particle tracking in Python, supporting 2D, 3D, and higher-dimensional data.

The integration requires full API coverage, which is best achieved through dynamic introspection of the `trackpy` namespace. This approach ensures that all 100+ functions (including diagnostics and plotting) are exposed without manual boilerplate, while allowing for "manual override" descriptions to improve LLM usability.

**Primary recommendation:** Use `trackpy 0.7.0` in a dedicated conda environment with `numba` for JIT acceleration. Implement a dynamic discovery layer that parses NumPy-style docstrings into JSON Schemas, mapping `ndarray` inputs to `BioImageRef` and `pandas.DataFrame` outputs to `TableRef`.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `trackpy` | 0.7.x | Particle tracking & linking | Industry standard; robust implementation of Crocker-Grier. |
| `pandas` | >=2.0 | Data representation | Trackpy uses DataFrames for all feature/trajectory data. |
| `numba` | >=0.59 | Acceleration | Required for performant linking and feature finding. |
| `scipy` | >=1.13 | Spatial indexing | Used for KDTree-based neighbor searches. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `docstring-parser` | Latest | Introspection | Essential for converting NumPy docstrings to JSON Schema. |
| `pims` | >=0.6 | Image streaming | Used by `tp.batch` for lazy-loading image sequences. |
| `matplotlib` | >=3.8 | Visualization | Required for `trackpy.plotting` functions. |
| `bioio` | Latest | Artifact I/O | Standard for reading/writing bioimage artifacts in this repo. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `trackpy` | `btrack` | `btrack` is specialized for cell tracking (Bayesian); `trackpy` is better for general particle physics/SMLM. |
| `trackpy` | `napari-strack` | GUI-focused; `trackpy` is headless-first and more suitable for MCP. |

**Installation:**
```bash
# Env definition in envs/bioimage-mcp-trackpy.yaml
conda create -n bioimage-mcp-trackpy python=3.12
conda install -n bioimage-mcp-trackpy trackpy=0.7.0 numba pandas scipy matplotlib pims docstring-parser bioio-ome-tiff
```

## Architecture Patterns

### Recommended Project Structure
```
tools/trackpy/
├── bioimage_mcp_trackpy/
│   ├── ops/
│   │   ├── locate.py       # Specific overrides for locate/batch
│   │   ├── link.py         # Specific overrides for linking
│   │   └── plotting.py     # Plotting wrappers (artifact output)
│   ├── descriptions.py     # Manual docstring overrides
│   ├── discovery.py        # Dynamic introspection engine
│   └── entrypoint.py       # MCP worker entrypoint
├── manifest.yaml           # Tool pack metadata
└── tests/
    └── smoke_test.py       # Numeric tolerance validation
```

### Pattern 1: Dynamic Introspection with Overrides
**What:** Use `inspect.signature` and `docstring-parser` to automatically generate tool definitions for the ~120 functions in `trackpy`.
**When to use:** For high-surface-area libraries where manual maintenance of `manifest.yaml` is prone to error.
**Example:**
```python
# Source: Adapted from neuroconv and smolagents
import inspect
from docstring_parser import parse

def get_tool_definition(func):
    doc = parse(func.__doc__)
    sig = inspect.signature(func)
    
    # Map Python types to MCP Artifact types
    # ndarray -> BioImageRef
    # DataFrame -> TableRef
    # etc.
    return {
        "name": func.__name__,
        "description": doc.short_description,
        "parameters": generate_schema(sig, doc)
    }
```

### Anti-Patterns to Avoid
- **Hard-coding all functions:** Do not manually write `manifest.yaml` entries for every `trackpy` function. It will break when `trackpy` updates.
- **Returning raw DataFrames:** Always wrap results in `TableRef` artifacts. Raw NDJSON of large tracking results will overwhelm MCP transport.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docstring Parsing | Regex parsers | `docstring-parser` | Handles NumPy/Google/Sphinx styles correctly and handles multi-line descriptions. |
| Coordinate Conversion | Custom loops | `numpy.transpose` | `trackpy` expects `(z, y, x)`. `bioio` provides dims metadata. |
| Large Asset Tests | Checking into Git | Git LFS | Upstream trackpy test data (bead sets) can be several MBs. |

**Key insight:** Use `trackpy.predict` for high-velocity particles. Do not try to implement custom "memory" logic outside the library; `trackpy`'s `memory` and `predictor` arguments are highly optimized.

## Common Pitfalls

### Pitfall 1: Numba First-Run Latency
**What goes wrong:** The first time a user calls `tp.locate` or `tp.link`, the MCP request times out (default 120s) because Numba is JIT-compiling kernels.
**How to avoid:** Run a "warm-up" tracking operation during worker initialization (`bioimage-mcp-trackpy` startup).
**Warning signs:** Log messages showing "Compiling...".

### Pitfall 2: Coordinate Ordering (Z, Y, X)
**What goes wrong:** `trackpy` uses `(z, y, x)` for 3D localization. Users often pass `(x, y, z)` or `(y, x, z)`.
**How to avoid:** The adapter must inspect `BioImageRef` metadata and explicitly reorder dimensions to match `trackpy` expectations.

### Pitfall 3: Subpixel Bias
**What goes wrong:** Low-quality images produce "pixel locking" where coordinates cluster at integer values.
**How to avoid:** Always expose `tp.subpx_bias` as a diagnostic tool.

## Code Examples

Verified patterns from official sources:

### Feature Finding (3D)
```python
# Source: https://soft-matter.github.io/trackpy/v0.6.0/tutorial/tracking-3d.html
import trackpy as tp
import numpy as np

# diameter must be a tuple for 3D: (z, y, x)
# Use odd integers for diameter
features = tp.locate(volume, diameter=(3, 11, 11), minmass=100)
```

### Advanced Linking with Prediction
```python
# Source: https://soft-matter.github.io/trackpy/v0.6.0/tutorial/prediction.html
from trackpy.predict import NearestVelocityPredict
pred = NearestVelocityPredict()
trajectories = tp.link(features, search_range=5, memory=3, predictor=pred)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `v0.5` MSD | `v0.7` MSD | July 2024 | Gaps in trajectories now return `NaN` instead of `0`. |
| Python 3.7 | Python 3.12 | v0.6.2 | Support for modern async-capable runtimes. |
| NumPy 1.x | NumPy 2.0 | v0.6.4 | Compatibility with newest scientific stack. |

**Deprecated/outdated:**
- `tp.link_df`: `tp.link` is now the preferred alias for `link_df`.

## Open Questions

Things that couldn't be fully resolved:

1. **Matplotlib Backend in Headless Workers**
   - What we know: `Agg` is the standard headless backend.
   - What's unclear: Does `bioimage-mcp`'s display protocol support returning `png` artifacts from matplotlib?
   - Recommendation: The `plotting.py` wrapper should save plots to temporary files and return `ImageRef` artifacts.

2. **Upstream Reference Data Access**
   - What we know: `trackpy` has a `trackpy-examples` repo.
   - What's unclear: Are these datasets licensed for redistribution?
   - Recommendation: Use the "Brownian motion" synthetic generator for smoke tests if licenses are unclear.

## Sources

### Primary (HIGH confidence)
- `/soft-matter/trackpy` (Context7) - API structure, usage patterns.
- https://github.com/soft-matter/trackpy/releases - Version 0.7 specifics.
- https://soft-matter.github.io/trackpy/stable/api.html - Function lists.

### Secondary (MEDIUM confidence)
- `neuroconv` source code - Dynamic schema generation patterns.
- `smolagents` source code - Tool definition extraction.

### Tertiary (LOW confidence)
- Community blog posts on "Pixel locking in trackpy" - Pitfall verification.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries are stable and well-documented.
- Architecture: HIGH - Follows existing hub-and-spoke pattern of the repo.
- Pitfalls: MEDIUM - Numba latency is environment-dependent.

**Research date:** 2026-01-23
**Valid until:** 2026-02-22 (30 days)
