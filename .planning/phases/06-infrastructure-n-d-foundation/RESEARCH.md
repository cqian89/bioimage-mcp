# Phase 06: Infrastructure & N-D Foundation - Research

**Researched:** 2026-01-25
**Domain:** Scipy Dynamic Adapters, Numpydoc Parsing, N-D Image Processing
**Confidence:** HIGH

## Summary

This research establishes the implementation approach for the Scipy dynamic adapter, focusing on `scipy.ndimage`. The goal is to dynamically discover image processing functions, parse their `numpydoc` docstrings into rich MCP tool schemas, and execute them safely with native dimension preservation.

Key findings include the selection of `docstring-parser` as the primary tool for schema generation due to its robust handling of scientific docstrings, and the definition of a "Safe Callable Registry" to handle functions like `generic_filter` without compromising security. We also confirm that `bioio`'s native 5D handling (TCZYX) aligns with Scipy's N-D processing capabilities, provided that the channel dimension (C) is treated as spatial as per user decision.

**Primary recommendation:** Use `docstring-parser` for unified docstring analysis and implement a `whitelisted` registry for `callable` arguments to enable safe remote execution of generic filters.

## Standard Stack

The established libraries for scientific function discovery and documentation parsing:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scipy` | ^1.10.0 | Core N-D image processing | The industry standard for scientific computing in Python. |
| `docstring-parser` | ^0.16 | Numpydoc/ReST parsing | Supports multiple styles (Numpydoc, Google, Sphinx) and provides structured parameter objects. |
| `inspect` | Stdlib | Signature analysis | Reliable extraction of default values and parameter kinds. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpydoc` | ^1.5 | Reference parser | Use `numpydoc.docscrape` for high-fidelity parsing if `docstring-parser` fails. |
| `bioio` | ^1.0 | N-D Image I/O | Handles TCZYX dimensions natively; preserves spatial resolution metadata. |
| `pydantic` | ^2.0 | Schema generation | Ideal for mapping parsed docstrings to strict MCP JSON schemas. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `docstring-parser` | `griffe` | `griffe` is more powerful (SOTA) but adds significant complexity for runtime parsing of installed packages. |
| `numpydoc` | Custom Regex | Manual regex is fragile and fails on complex scientific docstrings (e.g., multiline descriptions). |

**Installation:**
```bash
pip install scipy docstring-parser bioio bioio-ome-tiff
```

## Architecture Patterns

### Recommended Project Structure for Scipy Adapter
```
src/bioimage_mcp/registry/dynamic/adapters/
├── base.py                 # Abstract BaseAdapter
└── scipy/
    ├── __init__.py
    ├── adapter.py          # Generic Scipy logic (discovery, mapping)
    ├── callables.py        # Whitelist registry for 'callable' args
    └── config.yaml         # Blacklist and manual overrides
```

### Pattern 1: Safe Callable Registry
To satisfy the "Full implementation" requirement for callables (e.g., in `generic_filter`) without allowing arbitrary code execution:
**What:** A dictionary mapping strings to actual Python callables.
**When to use:** Whenever an argument is identified as a `callable` in the docstring/signature.
**Example:**
```python
# callables.py
import numpy as np

SAFE_REGISTRY = {
    "min": np.min,
    "max": np.max,
    "mean": np.mean,
    "median": np.median,
    "std": np.std,
    "sum": np.sum,
}

def resolve_callable(ref: str) -> callable:
    if ref in SAFE_REGISTRY:
        return SAFE_REGISTRY[ref]
    raise ValueError(f"Unauthorized or unknown callable: {ref}")
```

### Anti-Patterns to Avoid
- **Auto-Squeezing:** Do NOT use `np.squeeze()` on input images. Maintain the full TCZYX shape (e.g., 5D) to ensure pixel-size metadata remains aligned with dimensions.
- **In-Place Modification:** Even if Scipy supports `output=input`, the adapter must ALWAYS allocate a new array/artifact to preserve provenance.
- **Strict Float32:** Do NOT force `float32` if Scipy defaults to `float64` (Decision 40). Allow native precision for scientific accuracy.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docstring Parsing | Regex parsers | `docstring-parser` | Handles edge cases in Numpydoc syntax (e.g., "int, optional"). |
| Parameter Discovery | `dir()` only | `inspect.signature` | Provides defaults and parameter kinds (positional-only, etc.). |
| Dimension Mapping | Manual index tracking | `bioio` + `xarray` | `bioio` provides standardized TCZYX shapes regardless of source format. |

## Common Pitfalls

### Pitfall 1: 64-bit Integer OME-TIFF Incompatibility
**What goes wrong:** `scipy.ndimage.label` often returns `int64`. OME-TIFF (via `bioio-ome-tiff`) may fail or truncate when saving `int64` as standard TIFF.
**How to avoid:** Explicitly cast `int64` results to `int32` or `uint32` before saving if they represent labels/counts.

### Pitfall 2: Memory Exhaustion on 5D Filters
**What goes wrong:** Applying a 3D filter to a 5D image (T, C, Z, Y, X) where all dimensions are large.
**How to avoid:** Detect large artifacts and advise the use of `axes` parameter (if supported by the Scipy function) or process slices if the user provides a specific dimension hint.

### Pitfall 3: Alias Resolution Loop
**What goes wrong:** `scipy.ndimage` has many aliases (e.g., `convolve` vs `convolve1d`).
**How to avoid:** Decision 22 mandates exposing all aliases. Ensure the discovery logic does not "deduplicate" but instead registers both as valid tools.

## Code Examples

### Unified Introspection Pattern
```python
# Source: https://github.com/rr-/docstring_parser
import inspect
from docstring_parser import parse

def get_tool_schema(func):
    doc = parse(func.__doc__)
    sig = inspect.signature(func)
    
    parameters = {}
    for param in doc.params:
        # Match docstring param to signature to get defaults
        sig_param = sig.parameters.get(param.arg_name)
        default = sig_param.default if sig_param and sig_param.default is not inspect.Parameter.empty else None
        
        parameters[param.arg_name] = {
            "type": map_type(param.type_name),
            "description": param.description,
            "default": default
        }
    return parameters
```

### Resolving BioImageRef with Native Dimensions
```python
# Source: bioio official docs
from bioio import BioImage

def load_native(artifact_path):
    img = BioImage(artifact_path)
    # img.data is ALWAYS 5D (TCZYX)
    return img.data 
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `aicsimageio` | `bioio` | 2023 | Forked for better modularity and plugin-based reading. |
| `numpydoc` (library) | `docstring-parser` | 2024-2025 | Preferred for general-purpose parsing due to ease of use. |

## Open Questions

1. **Custom Geometric Mappings:** How to allow users to define complex `geometric_transform` mappings?
   - **Recommendation:** Start with a registry of common transforms (e.g., "flip_y", "transpose") and defer arbitrary expression evaluation to a future "unsafe" mode or a dedicated "Lambda Tool".

2. **Dtype Strict Enum:** Which dtypes are standard for the Enum?
   - **Recommendation:** `["uint8", "uint16", "uint32", "int8", "int16", "int32", "float32", "float64", "bool"]`.

## Sources

### Primary (HIGH confidence)
- `/scipy/scipy` - `scipy.ndimage` tutorials and API reference.
- `bioio-devs.github.io/bioio` - Official `bioio` documentation.
- `rr-.github.io/docstring_parser` - `docstring-parser` API.

### Secondary (MEDIUM confidence)
- `numpydoc.readthedocs.io` - Style guide for Scipy docstrings.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries are mature and well-documented.
- Architecture: HIGH - Registry pattern is common for safe remote execution.
- Pitfalls: MEDIUM - Based on known scientific computing challenges.

**Research date:** 2026-01-25
**Valid until:** 2026-02-24 (30 days)
