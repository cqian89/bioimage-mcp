# Retrospective: Spec 010 - Standardized Image Artifacts with bioio

**Date**: 2025-12-30  
**Status**: Post-Implementation Review  
**Test Results**: 159 contract tests passed, 95 integration tests passed, 4 integration tests failed

---

## Executive Summary

Spec 010 aimed to standardize on `bioio.BioImage` as the cross-environment image artifact layer. While the core implementation is functional, several critical issues were discovered during integration testing that prevent full end-to-end workflows from completing successfully.

**Key Finding**: The primary blocker is that `convert_to_ome_zarr` creates invalid OME-Zarr stores using raw `zarr.open_group()` instead of using the `bioio-ome-zarr` writer plugin.

---

## Test Failures

| Test | Status | Root Cause |
|------|--------|------------|
| `test_flim_phasor_e2e` | FAILED | Cellpose env missing `bioio` |
| `test_live_workflow_project_sum_cellpose` | FAILED | Invalid OME-Zarr output from `project_sum` |
| `test_legacy_redirect_denoise` | FAILED | `get_bioimage` wrapper enforces OME-TIFF reader on plain TIFF |
| `test_flim_phasor_golden_path` | FAILED | Test logic error (T axis has only 1 sample) |

---

## Issues Identified

### Issue #1: `convert_to_ome_zarr` Bypasses bioio Architecture 🔴 CRITICAL

**Location**: `tools/base/bioimage_mcp_base/io.py:60-66`

**Problem**: The function creates a plain Zarr v3 store using `zarr.open_group()` directly, bypassing the bioio plugin ecosystem entirely. This violates the architectural decision to standardize on bioio for all I/O operations.

**Current code** (incorrect):
```python
def convert_to_ome_zarr(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    # ... 
    root = zarr.open_group(str(out_dir), mode="w")  # ❌ Raw zarr, not OME-Zarr!
    root.create_array("0", data=data, chunks=data.shape)
    return out_dir
```

**Consequence**: The output lacks OME-Zarr multiscales metadata, making it unreadable by `bioio-ome-zarr` or any OME-Zarr compliant tool.

**Architectural Decision**: Remove `convert_to_ome_zarr` and replace with `OMEZarrWriter` from `bioio-ome-zarr`. This aligns with Constitution §III (Artifact References Only) which mandates using `bioio` plus plugins for all interchange formats.

**Suggested Fix**:
```python
from bioio_ome_zarr.writers import OMEZarrWriter

def convert_to_ome_zarr(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    # ... load image via BioImage ...
    
    out_dir = work_dir / "converted.ome.zarr"
    
    # Use bioio-ome-zarr writer for spec-compliant output
    writer = OMEZarrWriter(
        store=str(out_dir),
        level_shapes=[data.shape[-2:]],  # YX shape for pyramid
        dtype=data.dtype,
        zarr_format=2,  # OME-Zarr 0.4 uses Zarr v2
    )
    writer.write_full_volume(data)
    
    return out_dir
```

**Constitution Reference**: §III mandates "All tool environments MUST include `bioio` plus the minimal reader/writer plugins for their declared interchange format."

---

### Issue #2: Cellpose Environment Missing `bioio` Dependencies 🔴 HIGH

**Location**: `envs/bioimage-mcp-cellpose.yaml` (lines 19-20)

**Problem**: The YAML file declares `bioio` and `bioio-ome-tiff` as dependencies, but they are NOT actually installed in the environment.

**Verification**:
```bash
$ conda run -n bioimage-mcp-cellpose python -c "import bioio"
ModuleNotFoundError: No module named 'bioio'
```

**Spec 010 Requirement** (from tasks.md T004):
> Update `envs/bioimage-mcp-cellpose.yaml` to satisfy T002 (add `bioio`, `bioio-ome-tiff`)

**Impact**: Any cellpose workflow that uses `BioImage` for loading (as implemented per T025) fails immediately.

**Suggested Fix**:
```bash
# Option 1: Regenerate lockfile and reinstall
cd envs
conda-lock lock -f bioimage-mcp-cellpose.yaml -p linux-64
mamba env update -n bioimage-mcp-cellpose -f bioimage-mcp-cellpose.lock.yml

# Option 2: Manual install
conda activate bioimage-mcp-cellpose
conda install -c conda-forge bioio bioio-ome-tiff
```

---

### Issue #3: Redundant `get_bioimage` Wrapper Function 🟡 MEDIUM

**Location**: `tools/base/bioimage_mcp_base/utils.py:27-36`

**Problem**: The `get_bioimage()` wrapper function is unnecessary and actually causes failures. According to bioio documentation:

1. **BioImage auto-detects formats** - No format hints needed
2. **Plugins register extensions** - `bioio-ome-zarr` registers `.zarr`, `bioio-ome-tiff` registers `.ome.tif`/`.ome.tiff`
3. **Forcing readers causes failures** - The wrapper forces `bioio-ome-tiff` reader on files that might not have OME-XML

**Current code** (problematic):
```python
def get_bioimage(path: str | Path, format_hint: str | None = None) -> BioImage:
    if format_hint and format_hint.upper() == "OME-TIFF":
        try:
            import bioio_ome_tiff
            return BioImage(path, reader=bioio_ome_tiff.Reader)  # ❌ Fails on plain TIFF
        except ImportError:
            pass
    return BioImage(path)
```

**Architectural Decision**: Remove `get_bioimage()` entirely and use `BioImage` directly. The bioio library already handles format detection correctly when plugins are installed.

**Suggested Fix**: Replace all calls to `get_bioimage(path, format_hint)` with:
```python
from bioio import BioImage

# Auto-detection (recommended)
img = BioImage(path)

# Or explicit reader only when truly needed (rare)
from bioio_ome_zarr import Reader as OmeZarrReader
img = BioImage(path, reader=OmeZarrReader)
```

**Files to Update**:
- `tools/base/bioimage_mcp_base/utils.py` - Remove `get_bioimage()`
- `tools/base/bioimage_mcp_base/io.py` - Use `BioImage()` directly
- `tools/base/bioimage_mcp_base/preprocess.py` - Use `BioImage()` directly
- `tools/base/bioimage_mcp_base/axis_ops.py` - Use `BioImage()` directly

---

### Issue #4: Test Logic Error in `test_flim_phasor_golden_path` 🟢 LOW

**Location**: `tests/integration/test_workflows.py:test_flim_phasor_golden_path`

**Problem**: The test swaps Z↔T axes via `relabel_axes`, expecting the resulting T axis to have enough samples for phasor calculation. However, the original data has shape `[1, 1, 56, 512, 512]` with axes `TCZYX`:
- T=1 (only 1 time point)
- Z=56 (56 Z slices)

After swapping Z↔T, the new T axis still has size 1 (not 56), causing phasor to fail with:
```
Time axis must have at least 2 samples for phasor calculation
```

**Note**: `relabel_axes` only changes metadata labels, not data layout. Use `swap_axes` to actually transpose data.

**Suggested Fix**: Update test to either:
1. Use `time_axis="Z"` directly (as done in `test_flim_phasor_e2e`)
2. Use `swap_axes` instead of `relabel_axes` to actually transpose the data

---

## Documentation Updates Required

Based on these findings, the following documents need updates to reflect the bioio standardization:

### 1. Constitution (`.specify/memory/constitution.md`) ✅ Already Updated

Section III already correctly states:
> "All tool environments MUST include `bioio` plus the minimal reader/writer plugins for their declared interchange format."

**Additional Clarification Needed**: Add explicit guidance that custom I/O wrappers SHOULD NOT be created; use bioio APIs directly.

**Suggested Amendment** (Section III):
```markdown
- Tool implementations MUST use `bioio.BioImage` for reading and `bioio.writers.*` 
  (e.g., `OmeTiffWriter`, `OMEZarrWriter`) for writing. Custom I/O wrapper functions 
  SHOULD NOT be created as they bypass plugin auto-detection and cause compatibility issues.
```

### 2. Architecture (`docs/developer/architecture.md`)

**Current State**: Mentions bioio standardization briefly.

**Update Needed**: Add explicit architecture decision record (ADR) for bioio:
```markdown
### ADR: bioio as Standard I/O Layer

**Decision**: All image I/O in bioimage-mcp uses `bioio` library and its plugins.

**Rationale**:
- Consistent 5D TCZYX normalization across formats
- Plugin-based format support (OME-TIFF, OME-Zarr, CZI, LIF, etc.)
- Auto-detection eliminates need for format hints
- Reduces custom converter code

**Consequences**:
- All tool environments must include `bioio` + relevant plugins
- Do NOT use raw `zarr` or `tifffile` for artifact I/O
- Do NOT create wrapper functions around BioImage
```

### 3. Image Handling Guide (`docs/developer/image_handling.md`)

**Current State**: Documents the standard loading pattern correctly but doesn't explicitly prohibit custom wrappers.

**Updates Needed**:

1. Add anti-pattern section:
```markdown
## Anti-Patterns to Avoid

### ❌ Don't Create I/O Wrapper Functions
```python
# BAD - Don't do this
def get_bioimage(path, format_hint=None):
    if format_hint == "OME-TIFF":
        return BioImage(path, reader=bioio_ome_tiff.Reader)
    return BioImage(path)

# GOOD - Use BioImage directly
img = BioImage(path)  # Auto-detects format
```

### ❌ Don't Use Raw Zarr for OME-Zarr Output
```python
# BAD - Creates invalid OME-Zarr
root = zarr.open_group(out_dir, mode="w")
root.create_array("0", data=data)

# GOOD - Use bioio-ome-zarr writer
from bioio_ome_zarr.writers import OMEZarrWriter
writer = OMEZarrWriter(store=out_dir, ...)
writer.write_full_volume(data)
```
```

2. Add writing section for OME-Zarr:
```markdown
## Writing OME-Zarr

For OME-Zarr output, use the `OMEZarrWriter` from `bioio-ome-zarr`:

```python
from bioio_ome_zarr.writers import OMEZarrWriter

writer = OMEZarrWriter(
    store="output.zarr",
    level_shapes=[(height, width)],
    dtype=data.dtype,
    zarr_format=2,  # OME-Zarr 0.4 uses Zarr v2
)
writer.write_full_volume(data)
```
```

### 4. AGENTS.md

**Update Needed**: Add bioio anti-patterns to the "Adding a new function" section:
```markdown
### Standard BioImage I/O Pattern
When implementing image processing functions:

**Reading**: Always use `BioImage` directly without wrappers:
```python
from bioio import BioImage
img = BioImage(path)
data = img.data  # Always 5D TCZYX
```

**Writing OME-TIFF**:
```python
from bioio.writers import OmeTiffWriter
OmeTiffWriter.save(data, path, dim_order="TCZYX")
```

**Writing OME-Zarr**:
```python
from bioio_ome_zarr.writers import OMEZarrWriter
writer = OMEZarrWriter(store=path, level_shapes=[...], dtype=data.dtype)
writer.write_full_volume(data)
```

**Never**: Create custom I/O wrappers or use raw `zarr`/`tifffile` for artifacts.
```

---

## Tasks Status Review

Based on `tasks.md`, the following tasks appear incomplete or have issues:

| Task | Description | Status | Issue |
|------|-------------|--------|-------|
| T006 | Verify environment health with `python -m bioimage_mcp doctor` | ⚠️ | Doctor passes but cellpose env is broken |
| T017 | Integration test: phasor workflow runs from CZI via conversion | ❌ | Not implemented |
| T020 | Add helper to extract `StandardMetadata` from `BioImage` | ❌ | Not implemented |
| T021 | Populate `ArtifactRef.metadata` (shape, pixel_sizes, channel_names) | ❌ | Not implemented |
| T022 | Implement `ensure_interchange_format()` orchestrator | ❌ | Not implemented |
| T024 | Integration test: `cellpose.segment` accepts OME-TIFF | ❌ | Blocked by Issue #2 |
| T027 | Standardize base tool ops input reading to `BioImage` | ❌ | Partial - some ops still use tifffile |
| T029 | Integration test: chunked OME-Zarr workflow | ❌ | Blocked by Issue #1 |
| T030 | Extend `ensure_interchange_format()` to support OME-Zarr | ❌ | Not implemented |

---

## Recommendations

### Immediate Actions (P0)

1. **Replace `convert_to_ome_zarr` with `OMEZarrWriter`** - Use `bioio-ome-zarr` plugin for spec-compliant output
2. **Reinstall cellpose environment** - Ensure `bioio` and `bioio-ome-tiff` are actually installed
3. **Remove `get_bioimage` wrapper** - Use `BioImage()` directly throughout codebase

### Short-term Actions (P1)

4. **Update documentation** - Add anti-patterns and OME-Zarr writing guidance
5. **Amend Constitution §III** - Explicitly prohibit custom I/O wrappers
6. **Complete T020-T022** - Metadata extraction and format orchestration
7. **Fix phasor golden path test** - Use correct axis handling

### Medium-term Actions (P2)

8. **Add environment verification to CI** - Check that declared deps are actually importable
9. **Add format validation** - Verify output artifacts are valid OME-TIFF/OME-Zarr before returning

---

## Lessons Learned

1. **Use the ecosystem, don't bypass it** - Creating custom I/O code (like `zarr.open_group()` for "OME-Zarr") bypasses the plugin ecosystem that handles format compliance.

2. **Wrapper functions add failure modes** - The `get_bioimage()` wrapper tried to be "helpful" with format hints but actually caused failures. BioImage's auto-detection is more robust.

3. **Environment declarations ≠ installations** - YAML files declaring dependencies don't guarantee they're installed. Need verification step.

4. **Integration tests caught real issues** - The 4 failing tests exposed genuine implementation gaps that contract/unit tests missed.

---

## Appendix: bioio API Reference

### Reading (Auto-detection)
```python
from bioio import BioImage

img = BioImage("path/to/image.tif")      # Auto-detects OME-TIFF
img = BioImage("path/to/image.zarr")     # Auto-detects OME-Zarr
img = BioImage("path/to/image.czi")      # Auto-detects CZI

data = img.data                           # 5D TCZYX numpy/dask array
dims = img.dims                           # Dimension info
pixel_sizes = img.physical_pixel_sizes    # (Z, Y, X) in microns
```

### Writing OME-TIFF
```python
from bioio.writers import OmeTiffWriter

OmeTiffWriter.save(
    data,                    # 5D TCZYX array
    "output.ome.tiff",
    dim_order="TCZYX",
    physical_pixel_sizes=pixel_sizes,
    channel_names=channels,
)
```

### Writing OME-Zarr
```python
from bioio_ome_zarr.writers import OMEZarrWriter

writer = OMEZarrWriter(
    store="output.zarr",
    level_shapes=[(height, width)],
    dtype=data.dtype,
    zarr_format=2,           # OME-Zarr 0.4 spec
)
writer.write_full_volume(data)
```

---

## Appendix: Debugging Commands

```bash
# Check if bioio is in cellpose env
conda run -n bioimage-mcp-cellpose python -c "import bioio; print('OK')"

# Verify OME-Zarr structure
python -c "
import zarr
from pathlib import Path
p = Path('/path/to/output.ome.zarr')
root = zarr.open_group(str(p), mode='r')
print('Attrs:', dict(root.attrs))  # Should have 'multiscales'
print('Keys:', list(root.keys()))
"

# Test BioImage auto-detection
python -c "
from bioio import BioImage
from bioio.plugins import dump_plugins
dump_plugins()  # Show installed plugins
"

# Run failing tests with verbose output
pytest tests/integration/test_live_workflow.py -v --tb=long
```
