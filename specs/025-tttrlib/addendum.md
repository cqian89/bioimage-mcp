# Addendum: tttrlib Integration Review and Expansion Proposal

## 1. Current Implementation Review

### 1.1 Implemented Functions (v0.1.0)
Document the 7 functions currently implemented:
- tttrlib.TTTR - Opens TTTR files, returns TTTRRef
- tttrlib.TTTR.header - Extracts metadata as JSON
- tttrlib.TTTR.get_time_window_ranges - Burst selection
- tttrlib.TTTR.write - Export TTTR data
- tttrlib.Correlator - FCS multi-tau correlation
- tttrlib.CLSMImage - Reconstruct scanning image
- tttrlib.CLSMImage.compute_ics - Image Correlation Spectroscopy

### 1.2 Current Coverage Assessment
Categorize by workflow domain:
- **FCS/Correlation**: Covered (tttrlib.Correlator)
- **ICS**: Covered (tttrlib.CLSMImage.compute_ics) - Note: has upstream stability issues ([#22](https://github.com/Fluorescence-Tools/tttrlib/issues/22), [#25](https://github.com/Fluorescence-Tools/tttrlib/issues/25))
- **Burst Selection**: Covered (get_time_window_ranges)
- **I/O**: Covered (TTTR, write, header)
- **FLIM/Phasor**: NOT covered - get_phasor, get_mean_lifetime, get_fluorescence_decay
- **Intensity imaging**: NOT covered - get_intensity
- **Lifetime fitting**: NOT covered - DecayFit classes
- **PDA/FRET**: NOT covered - Pda class

## 2. API Coverage Gap Analysis

### 2.1 CLSMImage Methods NOT Implemented (Priority Candidates)

| Method | Purpose | Output Type | Priority |
|--------|---------|-------------|----------|
| get_intensity() | Sum photons per pixel | BioImageRef (3D: ZYX) | P0 - Critical for workflows |
| get_phasor(tttr_data, frequency, ...) | Compute g,s per pixel | BioImageRef (4D: ZYXC where C=2) | P0 - Enables PhasorPy bridge |
| get_mean_lifetime(tttr_data, tttr_irf=None, ...) | Fast lifetime image | BioImageRef (3D: ZYX) | P1 - Standalone FLIM |
| get_fluorescence_decay(tttr_data, micro_time_coarsening=1, ...) | Decay histogram per pixel | BioImageRef (4D: ZYXT) | P1 - For custom fitting |

### 2.2 Standalone Classes NOT Implemented

| Class/Method | Purpose | Priority |
|--------------|---------|----------|
| DecayPhasor.compute_phasor | Phasor from microtimes | P2 |
| DecayPhasor.compute_phasor_bincounts | Phasor from histogram | P2 |
| Fit23/Fit24 | MLE lifetime fitting | P2 |
| Pda | Photon Distribution Analysis | P3 |

## 3. Cross-Tool Integration Opportunities

### 3.1 tttrlib → PhasorPy Bridge Workflow

**Goal**: Enable users to start with raw TTTR data and seamlessly transition to PhasorPy analysis.

**Current Gap**: tttrlib produces raw photon data but has no direct path to the phasor-space analysis tools in phasorpy.

**Proposed Solution - Two pathways**:

#### Pathway A: Via CLSMImage.get_phasor()
```
TTTR File (.ptu/.spc)
    │
    ▼ tttrlib.TTTR()
TTTRRef
    │
    ▼ tttrlib.CLSMImage()
ObjectRef (CLSMImage)
    │
    ▼ tttrlib.CLSMImage.get_phasor(tttr_data=<TTTRRef>, frequency=80.0)
BioImageRef (4D: shape=(Z, Y, X, 2), axes="ZYXC")
    │  ├── Channel 0: g (real) component
    │  └── Channel 1: s (imaginary) component
    │
    ├─▶ phasorpy.plot.plot_phasor() → PlotRef
    │
    └─▶ phasorpy.phasor.phasor_transform() → calibrated phasors
```

#### Pathway B: Via fluorescence decay → phasor_from_signal
```
ObjectRef (CLSMImage)
    │
    ▼ tttrlib.CLSMImage.get_fluorescence_decay(tttr_data=<TTTRRef>, micro_time_coarsening=1)
BioImageRef (4D: ZYXT) - Decay histograms
    │
    ▼ phasorpy.phasor.phasor_from_signal(frequency=80.0)
    │
BioImageRef (mean, real, imag outputs)
```

**New Functions Required**:
1. `tttrlib.CLSMImage.get_phasor` - native phasor computation
2. `tttrlib.CLSMImage.get_fluorescence_decay` - decay extraction
3. `tttrlib.CLSMImage.get_intensity` - for reference images

### 3.2 tttrlib → Cellpose Bridge Workflow

**Goal**: Segment cells from FLIM intensity images derived from TTTR data, then use segmentation masks to analyze per-cell lifetime/phasor distributions.

**Proposed Workflow**:
```
TTTR File (.ptu)
    │
    ▼ tttrlib.TTTR()
TTTRRef
    │
    ▼ tttrlib.CLSMImage()
ObjectRef (CLSMImage)
    │
    ├─▶ tttrlib.CLSMImage.get_intensity()
    │       │
    │       ▼ BioImageRef (intensity image)
    │           │
    │           ▼ cellpose.models.CellposeModel.eval()
    │               │
    │               ▼ LabelImageRef (segmentation masks)
    │
    └─▶ tttrlib.CLSMImage.get_mean_lifetime(tttr_data=<TTTRRef>, ...) OR get_phasor(tttr_data=<TTTRRef>, ...)
            │
            ▼ BioImageRef (lifetime/phasor)
                │
                ▼ base.measure.regionprops() using LabelImageRef
                    │
                    ▼ TableRef (per-cell statistics)
```

**Key Integration Point**: The intensity image from tttrlib must be compatible with Cellpose's expected input format (typically 2D or 3D grayscale/multichannel).

### 3.3 Multi-frequency Phasor Analysis

tttrlib's get_phasor supports a `harmonic` parameter for multi-harmonic analysis. Combined with phasorpy's phasor_calibrate and filtering functions, this enables:

1. Acquire TTTR → CLSMImage
2. Compute phasors at multiple harmonics (1st, 2nd)  
3. Use phasorpy for component separation

## 4. Proposed API Expansion (Phase 2)

### 4.1 New Functions to Implement

**P0 - Critical for Cross-tool Workflows**:

```yaml
- fn_id: tttrlib.CLSMImage.get_intensity
  tool_id: tools.tttrlib
  name: Get Intensity Image
  description: Extract intensity image from CLSM data
  inputs:
    - name: clsm
      artifact_type: ObjectRef
      required: true
  outputs:
    - name: intensity
      artifact_type: BioImageRef
      format: OME-TIFF
  params_schema:
    type: object
    properties:
      stack_frames:
        type: boolean
        default: false
        description: "Sum across all frames"

- fn_id: tttrlib.CLSMImage.get_phasor
  tool_id: tools.tttrlib
  name: Get Phasor Image
  description: Compute phasor coordinates (g, s) per pixel
  inputs:
    - name: clsm
      artifact_type: ObjectRef
      required: true
    - name: tttr_data
      artifact_type: TTTRRef
      required: true
      description: "Original TTTR data (required by tttrlib API)"
    - name: tttr_irf
      artifact_type: TTTRRef
      required: false
      description: "IRF data for correction"
  outputs:
    - name: phasor
      artifact_type: BioImageRef
      format: OME-TIFF
      description: "4D array (F,Y,X,2) with g and s channels"
  params_schema:
    type: object
    properties:
      frequency:
        type: number
        default: -1.0
        description: "Modulation frequency (MHz). -1 for auto from header"
      harmonic:
        type: integer
        default: 1
        description: "Harmonic for multi-harmonic phasor analysis"
      minimum_number_of_photons:
        type: integer
        default: 2
        description: "Min photons for valid phasor"
      stack_frames:
        type: boolean
        default: false
        description: "Combine frames before phasor calculation"
```

**P1 - Extended FLIM Capabilities**:

```yaml
- fn_id: tttrlib.CLSMImage.get_mean_lifetime
  description: Compute mean lifetime image (tttrlib mean lifetime image)
  inputs:
    - name: clsm
      artifact_type: ObjectRef
      required: true
    - name: tttr_data
      artifact_type: TTTRRef
      required: true
      description: "Original TTTR data (required by tttrlib API)"
    - name: tttr_irf
      artifact_type: TTTRRef
      required: false
      description: "IRF data for correction"
  outputs:
    - name: lifetime
      artifact_type: BioImageRef
      description: "Lifetime in nanoseconds per pixel"
  params_schema:
    type: object
    properties:
      minimum_number_of_photons:
        type: integer
        default: 3
        description: "Minimum photons per pixel"
      stack_frames:
        type: boolean
        default: false
        description: "Combine frames before lifetime calculation"

- fn_id: tttrlib.CLSMImage.get_fluorescence_decay
  description: Extract decay histogram per pixel
  inputs:
    - name: clsm
      artifact_type: ObjectRef
      required: true
    - name: tttr_data
      artifact_type: TTTRRef
      required: true
      description: "Original TTTR data (required by tttrlib API)"
  outputs:
    - name: decay
      artifact_type: BioImageRef
      description: "4D array (F,Y,X,T) where T is microtime bins"
  params_schema:
    type: object
    properties:
      micro_time_coarsening:
        type: integer
        default: 1
        description: "Coarsening factor for microtime bins"
      stack_frames:
        type: boolean
        default: false
        description: "Combine frames before decay extraction"
```

### 4.2 Implementation Strategy

Follow the same pattern as v0.1.0:
1. Add function definitions to manifest.yaml
2. Add schemas to tttrlib_api.json
3. Implement handlers in entrypoint.py
4. Write contract tests first (TDD)
5. Add smoke tests for new workflows

## 5. Data Flow Diagram (Expanded)

```
TTTR File (SPC/PTU/HDF5)
    │
    ▼ tttrlib.TTTR()
TTTRRef ──────────────────────────────────────────────┐
    │                                                  │
    ├─▶ tttrlib.TTTR.header() ─▶ NativeOutputRef       │
    │                          (JSON metadata)         │
    ├─▶ tttrlib.Correlator() ─▶ TableRef               │
    │                         (tau, correlation)       │
    ├─▶ tttrlib.TTTR.get_time_window_ranges()          │
    │   ─▶ TableRef (burst ranges)                     │
    │                                                  │
    └─▶ tttrlib.CLSMImage() ─▶ ObjectRef ──────────────┤
                                (CLSMImage)            │
                                    │                  │
         ┌──────────────────────────┼──────────────┐   │
         ▼                          ▼              ▼   │
    get_intensity()          get_phasor()    get_fluorescence_decay()
         │                          │              │
         ▼                          ▼              ▼
    BioImageRef              BioImageRef     BioImageRef
    (intensity)              (g, s)          (ZYXT decay)
         │                          │              │
         │                          │              │
    ┌────┴────┐              ┌──────┴──────┐      ▼
    ▼         ▼              ▼             ▼   phasorpy.phasor.
Cellpose    base.        phasorpy.     phasorpy.  phasor_from_signal()
.eval()   filter/      plot.          phasor.         │
    │     transform    plot_phasor()  phasor_transform │
    ▼         │              │              │          │
LabelImageRef │              ▼              ▼          ▼
    │         ▼           PlotRef    BioImageRef  BioImageRef
    │    BioImageRef               (calibrated)   (mean, g, s)
    │                                    │
    └─────────────┬──────────────────────┘
                  ▼
          base.measure.regionprops()
                  │
                  ▼
            TableRef (per-cell stats)
```

Note: In upstream `tttrlib`, `CLSMImage.get_phasor`, `CLSMImage.get_mean_lifetime`, and `CLSMImage.get_fluorescence_decay` require the original `TTTR` object to be passed as `tttr_data` (and optionally `tttr_irf` for correction). `get_intensity` does not require `tttr_data`.

Axis note: tttrlib image arrays are typically `(n_frames, n_lines, n_pixel)`. For OME-TIFF outputs, this proposal maps `n_frames` to the `Z` axis (so `ZYX`), consistent with the existing `compute_ics` implementation in `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`.

## 6. Testing Strategy

### 6.1 New Smoke Tests Required

```python
# test_tttrlib_to_phasorpy.py
@pytest.mark.smoke_full
async def test_tttr_to_phasor_bridge(live_server):
    """Test converting TTTR → CLSMImage → phasor → phasorpy plot"""
    # 1. Load TTTR
    # 2. Create CLSMImage
    # 3. Get phasor image (NEW)
    # 4. Pass to phasorpy.plot.plot_phasor

@pytest.mark.smoke_full  
async def test_tttr_to_cellpose_workflow(live_server):
    """Test TTTR → intensity → Cellpose → segmentation"""
    # 1. Load TTTR
    # 2. Create CLSMImage  
    # 3. Get intensity image (NEW)
    # 4. Run Cellpose segmentation
    # 5. Verify LabelImageRef output
```

### 6.2 Contract Tests

- Verify new function schemas match manifest
- Verify output artifact types are correct
- Test dimension metadata propagation

## 7. Recommendations

### 7.1 Immediate (v0.2.0)
1. Implement `get_intensity()` - enables downstream workflows
2. Implement `get_phasor()` - enables native phasor images
3. Implement `get_fluorescence_decay()` - enables decay → phasorpy pathway
4. Add smoke tests for tttrlib → PhasorPy workflows

### 7.2 Near-term (v0.3.0)
1. Implement `get_mean_lifetime()` - standalone FLIM
2. Add smoke test for tttrlib → Cellpose workflow

### 7.3 Future (v0.4.0+)
1. DecayPhasor standalone class
2. Lifetime fitting (Fit23/24)
3. PDA for FRET analysis

## 8. Constitution Compliance Verification

| Principle | Phase 2 Additions |
|-----------|-------------------|
| I. Stable MCP Surface | New functions follow existing patterns |
| II. Isolated Execution | All in bioimage-mcp-tttrlib env |
| III. Artifact References | Output via BioImageRef (OME-TIFF) |
| IV. Reproducibility | Same lockfile, versioned schema |
| V. Safety | Subprocess isolation maintained |
| VI. TDD | Tests required before implementation |

## 9. Known Issues

### 9.1 Schema/Manifest Drift

`tools/tttrlib/schema/tttrlib_api.json` currently records:
```json
"upstream_version": "0.25.0"
```
This matches the intended `bioimage-mcp-tttrlib` environment pin.

Note: `tttrlib.__version__` may report `0.0.0` (SWIG binding issue), so the schema’s `upstream_version` and the conda package version are the more reliable provenance signals.

**Action Required**: Before adding new CLSMImage methods, fix drift between the curated schema and the actual tool surface (manifest + entrypoint):
- `tttrlib.TTTR.container_type` enum: schema uses `"HDF"` but manifest/entrypoint use `"PHOTON-HDF5"`.
- `tttrlib.CLSMImage` params: schema is missing `n_frames` (present in manifest/entrypoint).
- `tttrlib.TTTR.write` outputs: schema uses `tttr`, but manifest/entrypoint return `tttr_out`.

These mismatches should be covered by contract tests to prevent future drift.

### 9.2 ICS Stability

The `tttrlib.CLSMImage.compute_ics` function has known upstream stability issues:
- [Issue #22](https://github.com/Fluorescence-Tools/tttrlib/issues/22): Kernel crashes with incorrect marker settings
- [Issue #25](https://github.com/Fluorescence-Tools/tttrlib/issues/25): Crashes when required kwargs are missing

The corresponding smoke test is marked as `xfail` until upstream fixes are available.

---

**Author**: AI Analysis  
**Date**: 2026-01-15  
**Status**: Proposal Draft
