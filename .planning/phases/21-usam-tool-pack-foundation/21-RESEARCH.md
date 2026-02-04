# Phase 21: µSAM Tool Pack Foundation - Research

**Researched:** 2026-02-04
**Domain:** isolated environment and model management for µSAM (`micro-sam`)
**Confidence:** HIGH

## Summary

Phase 21 establishes the foundation for the µSAM tool pack by creating a dedicated conda environment and ensuring the availability of essential pretrained models. `micro-sam` (µSAM) is a library built on top of Meta's Segment Anything Model (SAM), fine-tuned for microscopy applications (Light Microscopy - LM and Electron Microscopy - EM).

The standard installation uses `conda-forge`. For device acceleration, µSAM relies on PyTorch's native support for CUDA (Linux/Windows) and MPS (Apple Silicon). Models are managed via `pooch` and cached in a standard location, which can be overridden via environment variables.

**Primary recommendation:** Use `conda-forge` for the base installation, and ensure at least the `vit_b` (Base) variants of the Generalist, LM, and EM model sets are pre-downloaded to the default cache directory during installation.

## Standard Stack

The established stack for µSAM:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `micro_sam` | 1.7.1+ | Core library for microscopy SAM | Official library for this domain |
| `segment-anything` | 1.0+ | Original SAM implementation | Foundation for µSAM |
| `torch` | 2.4+ | Deep learning framework | Backs SAM and µSAM |
| `torchvision` | 0.19+ | Image processing utilities | Required by SAM |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pooch` | 1.8+ | Model download and caching | Standard µSAM model management |
| `python-xxhash` | 3.4+ | Fast checksum calculation | Used by µSAM to verify model integrity |
| `trackastra` | 0.1+ | Object tracking | Required for µSAM tracking functionality |
| `mobile-sam` | Latest | Lightweight SAM (vit_t) | Required for `vit_t` models |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `conda install` | `pip install` | µSAM explicitly recommends `conda` due to complex binary dependencies (PyTorch, vigra, etc.) |

**Installation (CPU Profile):**
```bash
conda create -n bioimage-mcp-microsam -c conda-forge micro_sam pytorch torchvision cpuonly
```

**Installation (GPU Profile - Linux):**
```bash
conda create -n bioimage-mcp-microsam -c conda-forge micro_sam pytorch torchvision pytorch-cuda=12.1 -c nvidia
```

**Installation (GPU Profile - macOS/MPS):**
```bash
conda create -n bioimage-mcp-microsam -c conda-forge micro_sam pytorch torchvision
```

## Architecture Patterns

### Recommended Project Structure
µSAM tools will follow the standard `bioimage-mcp` tool pack structure:
```
tools/microsam/
├── manifest.yaml       # Tool definitions
├── adapter.py          # Adapter for µSAM functions
└── ...
```

### Pattern 1: Model Caching
µSAM uses `pooch` for caching. The default directory is resolved as follows:
1. Environment variable `MICROSAM_CACHEDIR`.
2. Fallback to `pooch.os_cache("micro_sam")` (e.g., `~/.cache/micro_sam/models`).

**Implementation:**
```python
# Source: micro_sam/util.py
def get_cache_directory():
    default_cache_directory = os.path.expanduser(pooch.os_cache("micro_sam"))
    cache_directory = Path(os.environ.get("MICROSAM_CACHEDIR", default_cache_directory))
    return cache_directory
```

### Anti-Patterns to Avoid
- **Mixing Environments:** Do not install `micro_sam` in the base environment or shared tool environments; it has strict version requirements for `torch` and `torch_em`.
- **Manual Download:** Do not manually download `.pth` files. Use `micro_sam.util._download_sam_model` to ensure checksum verification.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model Downloads | Custom `requests` downloader | `micro_sam.util._download_sam_model` | Handles checksums, multi-part decoders, and `pooch` caching automatically. |
| Device Selection | `torch.device("cuda")` | `micro_sam.util.get_device("auto")` | Handles the `cuda` > `mps` > `cpu` priority list correctly across platforms. |
| Instance Merging | Custom NMS for masks | `micro_sam.util.apply_nms` | Optimized for SAM mask outputs and overlaps. |

## Common Pitfalls

### Pitfall 1: `vit_t` Dependency
**What goes wrong:** `micro_sam` supports `vit_t` (Tiny) models for fast inference, but the required `mobile-sam` package is not currently on `conda-forge`.
**How to avoid:** If `vit_t` models are required, run `pip install git+https://github.com/ChaoningZhang/MobileSAM.git` inside the environment after creation.

### Pitfall 2: Tracking Prerequisite
**What goes wrong:** Tracking features require `trackastra`, which may be missing from the `conda-forge` recipe.
**How to avoid:** Ensure `trackastra` is installed via `pip` if tracking tools are enabled.

## Code Examples

### Verifying Model Presence
```python
from micro_sam.util import models

def verify_models():
    registry = models()
    # Check if vit_b_lm is already cached
    path = registry.fetch("vit_b_lm", progressbar=False)
    print(f"Model available at: {path}")
```

### Device Selection Override
```python
from micro_sam.util import get_device

# bioimage-mcp config mapping
config_device = "mps" # or "cuda", "cpu", "auto"
device = get_device(config_device)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Original SAM | µSAM (fine-tuned) | 2023 | Significantly better performance on organelles and small cells. |
| SHA256 hashes | XXH128 hashes | v1.5.0 | Faster integrity checks for large model files. |

## Open Questions

1. **Exact Model Set Definition:** The requirements mention "LM, EM, and Generalist sets". Does this mean B (Base), L (Large), and H (Huge) for all three, or just the default B?
   - **Recommendation:** Start with the `vit_b` versions of all three as the minimum requirement for a successful install.
2. **Trackastra in Foundation:** Should `trackastra` be part of the foundation (Phase 21) or wait until tracking tools are implemented?
   - **Recommendation:** Install it during Phase 21 to ensure the environment is "ready for local inference" for all core µSAM features.

## Sources

### Primary (HIGH confidence)
- `computational-cell-analytics/micro-sam` GitHub Repository
- `micro_sam/util.py` - Core logic for downloads and devices
- `conda-forge/micro_sam-feedstock` - Official conda recipe

### Secondary (MEDIUM confidence)
- `micro-sam` Official Documentation (`doc/installation.md`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified via official recipe and source code.
- Architecture: HIGH - µSAM has a well-defined internal registry for models and devices.
- Pitfalls: MEDIUM - Dependent on current state of `conda-forge` recipes.

**Research date:** 2026-02-04
**Valid until:** 2026-03-06 (30 days)

## RESEARCH COMPLETE

**Phase:** 21 - µSAM Tool Pack Foundation
**Confidence:** HIGH

### Key Findings

- **Environment:** `micro-sam` is best installed via `conda-forge` with a specific `pytorch` version for the target profile (CPU/GPU).
- **Models:** The LM, EM, and Generalist sets correspond to fine-tuned microscopy models and foundation SAM models. `vit_b` is the standard default for each.
- **Caching:** Models are stored in `~/.cache/micro_sam/models` by default, managed by `pooch` with XXH128 checksums.
- **Device Support:** Full support for CUDA and Apple Silicon (MPS) via PyTorch.
- **Hidden Dependencies:** `mobile-sam` and `trackastra` are not in the conda-forge recipe and require `pip` installation for full functionality.

### Ready for Planning

Research complete. Planner can now create PLAN.md files.

---

*Note: The plan should include explicit `pip install` steps for `mobile-sam` and `trackastra` within the isolated environment to ensure full functionality.*
