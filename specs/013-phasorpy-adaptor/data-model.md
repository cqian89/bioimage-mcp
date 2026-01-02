# Data Model: Phasorpy Adaptor

This document defines the core entities, data structures, and state transitions for the `013-phasorpy-adaptor` feature, exposing the Phasorpy v0.9+ API within the BioImage-MCP framework.

## 1. Core Entities

### Signal (Input)
- **Description**: Raw fluorescence decay data from FLIM microscopy.
- **Shape**: 5D or 6D array (T, C, Z, Y, X) where one dimension contains time-gate/decay bins.
- **Storage**: `BioImageRef` artifact (OME-TIFF or OME-Zarr).
- **Metadata**: `axes`, `shape`, `dtype`, `laser_frequency_hz` (if available).
- **Relationships**: Input to `phasor_from_signal`, produced by `bioio` readers.

### Phasor Components
- **Description**: Frequency-domain representation of fluorescence signal.
- **Components**:
  - `mean`: Average intensity at each pixel (scalar image).
  - `real` (G): Cosine transform component.
  - `imag` (S): Sine transform component.
- **Shape**: Same spatial dimensions as input, minus the decay dimension.
- **Storage**: `BioImageRef` artifact (OME-TIFF).
- **Value range**: G and S typically in [0, 1] for calibrated data.
- **Relationships**: Output of `phasor_from_signal`, input to `phasor_transform`, `phasor_calibrate`, and lifetime functions.

### Lifetime Map
- **Description**: Spatial image where pixel values represent estimated fluorescence lifetimes.
- **Shape**: 2D-4D (spatial dimensions).
- **Units**: Nanoseconds (typically 0.1 - 10 ns for biological samples).
- **Storage**: `BioImageRef` artifact.
- **Relationships**: Output of `phasor_to_apparent_lifetime`.

### PlotRef (NEW)
- **Description**: Visualization artifacts generated from the `phasorpy.plot` module.
- **Format**: PNG image.
- **Metadata**:
  - `width_px`: int
  - `height_px`: int
  - `dpi`: int (default 100)
  - `plot_type`: str (e.g., "phasor_plot", "phasor_image")
- **Relationships**: Output of `plot_phasor`, `plot_phasor_image`.

## 2. Pydantic Models

These models define the structure of the new artifact types and extended metadata.

```python
class PlotRef(ArtifactRef):
    """Reference to a matplotlib plot artifact."""
    type: Literal["PlotRef"] = "PlotRef"
    format: Literal["PNG", "SVG"] = "PNG"
    metadata: PlotMetadata

class PlotMetadata(BaseModel):
    """Metadata for plot artifacts."""
    width_px: int
    height_px: int
    dpi: int = 100
    plot_type: str | None = None
    title: str | None = None

class PhasorMetadata(BaseModel):
    """Extended metadata for phasor artifacts."""
    component: Literal["mean", "real", "imag"]
    harmonic: int = 1
    frequency_hz: float | None = None
    is_calibrated: bool = False
    reference_lifetime_ns: float | None = None
```

## 3. IOPattern Extensions

The following patterns will be added to `src/bioimage_mcp/registry/dynamic/models.py` to support comprehensive Phasorpy tool categorization:

```python
class IOPattern(str, Enum):
    # Existing patterns...
    SIGNAL_TO_PHASOR = "signal_to_phasor"
    PHASOR_TRANSFORM = "phasor_transform"
    PHASOR_TO_OTHER = "phasor_to_other"
    # New patterns for comprehensive phasorpy support
    PHASOR_TO_SCALAR = "phasor_to_scalar"  # e.g., apparent_lifetime
    SCALAR_TO_PHASOR = "scalar_to_phasor"  # e.g., phasor_from_lifetime
    PLOT = "plot"  # matplotlib figure output
```

## 4. State Transitions

The following diagram illustrates the typical workflow and data flow between artifacts:

```text
FileRef (SDT/PTU/LIF)
    ↓ [bioio read]
BioImageRef (Signal)
    ↓ [phasor_from_signal]
BioImageRef (Mean) + BioImageRef (Real) + BioImageRef (Imag)
    ↓ [phasor_calibrate]
BioImageRef (Calibrated Real) + BioImageRef (Calibrated Imag)
    ↓ [phasor_to_apparent_lifetime]
BioImageRef (Lifetime Map)
    ↓ [plot_phasor_image]
PlotRef (PNG)
```

## 5. Validation Rules

- **Signal Dimensions**: Signal arrays must have at least 3 dimensions (decay + 2D space).
- **Laser Frequency**: The `frequency` parameter is required for lifetime calculations (typically 80 MHz for standard FLIM systems).
- **Coordinate Consistency**: Real and Imaginary components must have identical shapes and spatial metadata.
- **Numerical Stability**: Plotting functions require valid phasor coordinates (non-NaN, non-infinite) to produce visual output.
