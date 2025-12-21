# Data Model: FLIM Phasor Analysis

## Entities

### 1. FLIM Dataset (Input)
*   **Description**: Time-resolved fluorescence intensity image data.
*   **Type**: `BioImageRef`
*   **Format**: OME-TIFF (Required)
*   **Structure**:
    *   Must contain a time/bin dimension (T).
    *   May contain spatial dimensions (X, Y, Z) and channel dimension (C).
    *   Metadata (OME-XML) should ideally contain time increment or frequency data for physical phasor calibration.

### 2. Phasor Coordinate Maps (Output)
*   **Description**: Two image artifacts representing the G (real) and S (imaginary) components of the phasor transform.
*   **Type**: `BioImageRef`
*   **Format**: OME-TIFF
*   **Structure**:
    *   Spatial dimensions (X, Y, Z) and Channel (C) preserved from input.
    *   Time dimension (T) is collapsed.
    *   Pixel values are floating point (typically -1.0 to 1.0).

### 3. Intensity Image (Output)
*   **Description**: Integrated intensity image derived from the FLIM dataset (sum over time/bins).
*   **Type**: `BioImageRef`
*   **Format**: OME-TIFF
*   **Structure**:
    *   Spatial dimensions (X, Y, Z) and Channel (C) preserved from input.
    *   Time dimension (T) is collapsed.
    *   Pixel values are intensity sums (float or int).

### 4. Denoised Image (Output)
*   **Description**: Output of a denoising operation (Phasor Map or other).
*   **Type**: `BioImageRef`
*   **Format**: OME-TIFF (or OME-Zarr if specified, but spec defaults to OME-TIFF for phasor context).
*   **Structure**: Matches input shape.

## Relationships

*   **FLIM Dataset** --(transform)--> **Phasor Maps (G, S)**
*   **FLIM Dataset** --(transform/projection)--> **Intensity Image**
*   **Phasor Map** --(denoise)--> **Denoised Map**
