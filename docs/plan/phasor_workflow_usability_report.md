# Phasor Workflow Usability Report

**Date:** December 26, 2025
**Scope:** Usability test of Bioimage-MCP "fresh install" experience for Phasor-FLIM analysis.

## Summary
An attempt was made to perform a standard Phasor-FLIM analysis on the `datasets/FLUTE_FLIM_data_tif/Embryo.tif` dataset, using `Fluorescein_Embryo.tif` as the calibration reference. While raw phasor coordinates were successfully generated, the workflow was hindered by critical infrastructure failures and functional gaps.

## Critical Findings

### 1. Discovery Infrastructure Failure
The core discovery tools are currently non-functional, preventing users from exploring available capabilities.
*   **Tools:** `list_tools`, `search_functions`
*   **Error:** `AttributeError: 'ServerSession' object has no attribute 'id'`
*   **Impact:** Users cannot discover tools or search for functionality (e.g., "phasor") without direct code inspection.

### 2. Schema Introspection Gaps
The `describe_function` tool failed to return useful parameter schemas.
*   **Function:** `base.phasor_from_flim`
*   **Result:** Returned an empty schema (`properties: {}`).
*   **Impact:** Users cannot determine required inputs (e.g., `harmonic`, `time_axis`) or expected formats programmatically.

### 3. Missing Calibration Functionality
There is no accessible mechanism to apply the reference calibration to the phasor analysis.
*   **Tool:** `base.phasor_from_flim` only computes raw uncalibrated phasor coordinates.
*   **Gap:** No `phasor_calibrate` or equivalent tool exists in the `base` tool manifest.
*   **Result:** The analysis yielded uncalibrated G/S coordinates, which are insufficient for quantitative biological interpretation.

### 4. Data Compatibility Issues
The provided validation datasets trigger read errors in the primary IO library.
*   **Library:** `bioio-ome-tiff`
*   **Error:** `Unknown property {http://www.openmicroscopy.org/Schemas/OME/2016-06}OME:{...}AnnotationRef`
*   **Fallback:** The system correctly fell back to `tifffile`, but this resulted in loss of metadata certainty (requiring axis inference).
*   **Inference:** Axes were inferred as `TYX` for the 3D stack (Time, Y, X), which appears correct for this dataset but relies on heuristics.

## Recommendations

1.  **Fix Session Management:** Investigate the `ServerSession` attribute error in the discovery endpoints immediately.
2.  **Expose Schemas:** Ensure `describe_function` correctly reflects the underlying Pydantic models for tool parameters.
3.  **Implement Calibration:** Add a calibration step (either integrated into `phasor_from_flim` or as a standalone `phasor_calibrate` tool) to the `base` toolkit.
4.  **Update IO Dependencies:** Investigate `bioio` support for OME-TIFF `AnnotationRef` tags or update the validation datasets to a compatible standard.
