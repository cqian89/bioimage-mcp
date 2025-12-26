# Data Model: Phasor Workflow Usability Fixes

## Overview

This document defines the data models for the phasor calibration workflow and related fixes.

## Entities

### PhasorCoordinates

Phasor transform results stored as a 2-channel BioImageRef artifact.

| Field | Type | Description |
|-------|------|-------------|
| g_channel | float32[Y, X] | Real component (G) of phasor transform, stored as channel 0 |
| s_channel | float32[Y, X] | Imaginary component (S) of phasor transform, stored as channel 1 |

**Storage Format**: 2-channel OME-TIFF with axes `CYX` (C=2: channel 0 = G, channel 1 = S)

**Artifact Type**: `BioImageRef`

**Metadata**:
- `phasor_type`: "raw" | "calibrated"
- `harmonic`: int (e.g., 1)
- `frequency`: float (laser frequency in Hz, if applicable)

### CalibrationReference

Reference standard parameters used for phasor calibration.

| Field | Type | Description |
|-------|------|-------------|
| lifetime | float | Known fluorescence lifetime in nanoseconds (e.g., 4.04 for Fluorescein) |
| frequency | float | Laser repetition frequency in Hz |
| harmonic | int | Harmonic number (default: 1) |
| reference_phasors | BioImageRef | 2-channel phasor coordinates from reference sample |

**Validation Rules**:
- `lifetime` must be > 0
- `frequency` must be > 0
- `harmonic` must be >= 1

### CalibrationResult

Output of phasor calibration operation.

| Field | Type | Description |
|-------|------|-------------|
| calibrated_phasors | BioImageRef | 2-channel calibrated phasor coordinates |
| phase_shift | float | Applied phase correction in radians |
| modulation_ratio | float | Applied modulation correction factor |

**Provenance Metadata**:
- `reference_lifetime`: float (from CalibrationReference)
- `reference_frequency`: float
- `reference_harmonic`: int
- `calibration_timestamp`: ISO 8601 datetime

### FunctionSchema (Updated)

Complete parameter schema returned by `describe_function`.

| Field | Type | Description |
|-------|------|-------------|
| fn_id | string | Function identifier (e.g., "base.phasor_calibrate") |
| name | string | Human-readable function name |
| description | string | Function description |
| inputs | list[InputSpec] | Required input artifacts |
| outputs | list[OutputSpec] | Output artifacts produced |
| params_schema | JSONSchema | Complete JSON Schema for parameters |
| introspection_source | string | "pydantic" | "docstring" | "manual" |

**params_schema Structure** (example for phasor_calibrate):
```json
{
  "type": "object",
  "properties": {
    "lifetime": {
      "type": "number",
      "description": "Known lifetime of reference standard in nanoseconds",
      "minimum": 0,
      "exclusiveMinimum": true
    },
    "frequency": {
      "type": "number",
      "description": "Laser repetition frequency in Hz",
      "minimum": 0,
      "exclusiveMinimum": true
    },
    "harmonic": {
      "type": "integer",
      "description": "Harmonic number for multi-harmonic analysis",
      "default": 1,
      "minimum": 1
    }
  },
  "required": ["lifetime", "frequency"]
}
```

## State Transitions

### Phasor Workflow States

```
FLIM Dataset → [phasor_from_flim] → Raw Phasors
                                         ↓
Reference Dataset → [phasor_from_flim] → Reference Phasors
                                         ↓
Raw Phasors + Reference Phasors → [phasor_calibrate] → Calibrated Phasors
```

### Session State

| State | Description |
|-------|-------------|
| NEW | Session created, no tools called |
| ACTIVE | At least one tool call made |
| FILTERED | Active function filter applied |
| EXPORTED | Session exported to workflow artifact |

## Validation Rules

### Phasor Calibration Inputs

1. **Dimension Match**: Sample and reference phasor images must have the same spatial dimensions (Y, X) OR reference can be a single point (for global calibration)
2. **Channel Count**: Both inputs must have exactly 2 channels (G, S)
3. **Data Type**: Both inputs should be float32 for precision

### Error Conditions

| Error | Condition | Message |
|-------|-----------|---------|
| DIMENSION_MISMATCH | Sample and reference have incompatible shapes | "Reference phasor dimensions {ref_shape} incompatible with sample {sample_shape}" |
| INVALID_LIFETIME | lifetime <= 0 | "Reference lifetime must be positive, got {lifetime}" |
| INVALID_FREQUENCY | frequency <= 0 | "Frequency must be positive, got {frequency}" |
| CHANNEL_COUNT_ERROR | Input has != 2 channels | "Expected 2-channel phasor image, got {n_channels} channels" |

## Relationships

```
BioImageRef (FLIM Data)
    │
    ├──[phasor_from_flim]──▶ PhasorCoordinates (raw)
    │                              │
    │                              ▼
    └──(reference)──▶ PhasorCoordinates (raw)
                              │
                              ├── CalibrationReference ◀── (known lifetime)
                              │          │
                              └──────────┴──[phasor_calibrate]──▶ CalibrationResult
```
