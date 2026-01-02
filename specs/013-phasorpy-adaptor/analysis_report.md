# Phasorpy v0.9 API Audit & Mapping Report

## Module: phasorpy.io

> **⚠️ EXCLUDED FROM ADAPTER**: All file I/O is handled via bioio and its plugins (bioio-bioformats, bioio-lif). The phasorpy.io module is NOT exposed through the adapter.

| Function | Category | Notes |
|----------|----------|-------|
| `signal_from_sdt` | `FILE_TO_SIGNAL` | Becker & Hickl SDT files |
| `signal_from_ptu` | `FILE_TO_SIGNAL` | PicoQuant PTU files |
| `signal_from_lif` | `FILE_TO_SIGNAL` | Leica LIF files |
| `phasor_from_ometiff` | `FILE_TO_PHASOR` | OME-TIFF with phasor tags |
| `phasor_to_ometiff` | `PHASOR_TO_FILE` | Writes OME-TIFF |

## Module: phasorpy.phasor

| Function | Category | Notes |
|----------|----------|-------|
| `phasor_from_signal` | `SIGNAL_TO_PHASOR` | Returns `(mean, real, imag)` |
| `phasor_transform` | `PHASOR_TRANSFORM` | Returns `(real, imag)` |
| `phasor_center` | `PHASOR_TRANSFORM` | Subtracts center |
| `phasor_normalize` | `PHASOR_TRANSFORM` | Normalizes to unit circle |
| `phasor_to_polar` | `PHASOR_TO_OTHER` | Returns `(phase, modulation)` |
| `phasor_from_polar` | `OTHER_TO_PHASOR` | Takes `(phase, modulation)` |

## Module: phasorpy.lifetime

| Function | Category | Notes |
|----------|----------|-------|
| `phasor_from_lifetime` | `SCALAR_TO_PHASOR` | Takes `lifetime`, `frequency` |
| `phasor_to_apparent_lifetime` | `PHASOR_TO_SCALAR` | Returns `lifetime` |
| `phasor_calibrate` | `PHASOR_TRANSFORM` | Uses reference lifetime |
| `phasor_semicircle` | `GENERIC` | Returns semicircle coordinates |

## Module: phasorpy.plot

| Function | Category | Notes |
|----------|----------|-------|
| `plot_phasor` | `PLOT` | 2D histogram of phasors |
| `plot_phasor_image` | `PLOT` | Pseudo-color image |
| `PhasorPlot` | `PLOT` | Object-oriented plotting |

## Mapping Strategy for Nested/Complex Outputs

1. **Dictionaries**: If a function returns a dict, it will be mapped to a `TableRef` (if it's tabular) or a JSON artifact.
2. **Objects**: If a function returns a custom object (like a fitted model), it will be serialized to a JSON record if possible, or rejected if it requires persistence of complex state (outside the scope of current artifact model).
3. **Classes**: Classes like `PhasorPlot` will be treated as functions that return a plot (by calling a default method like `plot()`).

## Dimension Hints for Phasorpy

- **Signals**: Usually 5D `(T, C, Z, Y, X)` where `C` or `T` might represent the decay bins.
- **Phasors**: Usually 5D where `C` has specific meaning (0=Mean, 1=Real, 2=Imag).
- The adapter should provide hints to the agent about which dimensions to use for `axis` parameters in phasorpy functions (usually `axis=-1` or `axis=1`).
