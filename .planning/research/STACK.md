# Technology Stack: Scipy Integration

**Project:** Bioimage-MCP
**Researched:** 2026-01-25

## Recommended Stack

### Core Compute (Milestone v0.3.0)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **SciPy** | 1.17.0 | Primary compute engine | Latest stable release (Jan 2026); industry standard for N-D array processing. |
| **NumPy** | 2.2.2 | Array backend | Required for Scipy 1.17+; NumPy 2.x offers improved performance and typing. |
| **BioIO** | 3.2.0 | Image I/O | Standardizes 5D (TCZYX) loading/saving for bioimage artifacts. |
| **Pandas** | 3.0.0 | Tabular data | Essential for handling measurement outputs and coordinate tables. |

### Dynamic Discovery & Introspection
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **numpydoc** | 1.10.0 | Docstring parsing | Required by `Introspector` for generating high-fidelity tool schemas from Scipy's documentation. |
| **Pydantic** | 2.10.5 | Schema modeling | Standard for data validation and JSON schema generation in the core server. |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tifffile** | 2025.12.15 | TIFF/OME-TIFF backup | Fallback when BioIO writers are insufficient for specific metadata. |
| **xarray** | 2025.12.0 | Dimension-aware arrays | Used by bioio; facilitates axis-based indexing (e.g., extracting a Z-slice). |
| **Matplotlib** | 3.10.0 | Plotting | Used via the `FigureRef` pattern for `scipy.signal` spectral plots. |
| **scikit-image**| 0.25.0 | Complementary processing | Often used alongside Scipy for domain-specific image tasks. |

### Infrastructure (Existing)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Python** | 3.13 | Core Server Language | Latest stable with performance improvements. |
| **Micromamba** | Latest | Package Manager | Fast environment isolation for tool-packs. |
| **SQLite** | 3.x | State/Registry | Lightweight, file-based storage for run logs. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **Discovery**| numpydoc | manual manifest | Manual maintenance of Scipy's vast API is fragile; dynamic discovery ensures v0.3.0 stays current. |
| **Compute** | Scipy | OpenCV | OpenCV is optimized for 2D computer vision; Scipy is better for N-D scientific data. |
| **I/O** | BioIO | scikit-image.io | BioIO handles OME-TIFF and OME-Zarr metadata more robustly than basic skimage I/O. |

## Installation

```bash
# Update Scipy Tool Pack environment
# envs/bioimage-mcp-scipy.yaml
dependencies:
  - python=3.13
  - numpy>=2.2.2
  - scipy=1.17.0
  - numpydoc=1.10.0
  - pandas>=3.0.0
  - bioio>=3.2.0
  - bioio-ome-tiff>=1.4.0
  - xarray>=2025.12.0
```

## Sources

- [PyPI Scipy Release History](https://pypi.org/project/scipy/#history) (Verified Jan 10, 2026)
- [PyPI BioIO Release History](https://pypi.org/project/bioio/#history) (Verified Dec 22, 2025)
- [PyPI Pandas Release History](https://pypi.org/project/pandas/#history) (Verified Jan 21, 2026)
- [Numpydoc GitHub Releases](https://github.com/numpy/numpydoc/releases) (Verified Dec 2024)
- Existing `bioimage-mcp` adapters (`skimage.py`, `phasorpy.py`)
