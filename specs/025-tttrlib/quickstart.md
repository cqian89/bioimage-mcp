# Quickstart: tttrlib Integration

## Prerequisites

1. Install the tttrlib conda environment:
   ```bash
   conda env create -f envs/bioimage-mcp-tttrlib.yaml
   ```

2. Verify installation:
   ```bash
   python -m bioimage_mcp doctor --tool tttrlib
   ```

## Example Workflows

### FCS Correlation

```python
# 1. Open TTTR file
tttr = run("tttrlib.TTTR", params={"filename": "data.spc", "container_type": "SPC-130"})

# 2. Compute correlation
curve = run("tttrlib.Correlator", 
    inputs={"tttr": tttr},
    params={"channels": [[0], [8]], "n_bins": 17, "n_casc": 25})

# curve is a TableRef with columns: tau, correlation
```

### CLSM Image Reconstruction

```python
# 1. Open PTU file
tttr = run("tttrlib.TTTR", params={"filename": "scan.ptu", "container_type": "PTU"})

# 2. Construct CLSM image
clsm = run("tttrlib.CLSMImage",
    inputs={"tttr": tttr},
    params={"reading_routine": "SP5", "channels": [0]})

# 3. Compute ICS
ics = run("tttrlib.CLSMImage.compute_ics",
    inputs={"clsm": clsm},
    params={"subtract_average": "frame"})

# ics is a BioImageRef (OME-TIFF)
```

### Burst Analysis

```python
# 1. Open TTTR file
tttr = run("tttrlib.TTTR", params={"filename": "data.spc"})

# 2. Find bursts
bursts = run("tttrlib.TTTR.get_time_window_ranges",
    inputs={"tttr": tttr},
    params={
        "minimum_window_length": 0.002,
        "minimum_number_of_photons_in_time_window": 40
    })

# bursts is a TableRef with columns: start_index, stop_index
```

### FLIM Intensity Extraction

```python
# 1. Open PTU file
tttr = run("tttrlib.TTTR", params={"filename": "flim.ptu", "container_type": "PTU"})

# 2. Construct CLSM image
clsm = run("tttrlib.CLSMImage",
    inputs={"tttr": tttr},
    params={"reading_routine": "SP5", "channels": [0]})

# 3. Extract intensity image (2D for segmentation)
intensity = run("tttrlib.CLSMImage.get_intensity",
    inputs={"clsm": clsm},
    params={"stack_frames": True})

# intensity is a BioImageRef (OME-TIFF)
```

### Phasor Analysis (PhasorPy Integration)

```python
# 1. Open PTU file
tttr = run("tttrlib.TTTR", params={"filename": "flim.ptu", "container_type": "PTU"})

# 2. Construct CLSM image
clsm = run("tttrlib.CLSMImage",
    inputs={"tttr": tttr},
    params={"reading_routine": "SP5", "channels": [0]})

# 3. Compute phasor coordinates (g, s) per pixel
phasor = run("tttrlib.CLSMImage.get_phasor",
    inputs={"clsm": clsm, "tttr_data": tttr},
    params={"frequency": 80.0, "stack_frames": True})

# phasor is a BioImageRef (OME-TIFF) with channels [g, s]
# Can be used with phasorpy.plot or further analysis
```

### Fluorescence Decay Extraction

```python
# 1. Open PTU file and create CLSM image (as above)

# 2. Extract decay histogram per pixel
decay = run("tttrlib.CLSMImage.get_fluorescence_decay",
    inputs={"clsm": clsm, "tttr_data": tttr},
    params={"micro_time_coarsening": 4, "stack_frames": True})

# decay is a BioImageRef (OME-TIFF) with microtime bins stored along the leading T axis
# For phasorpy.phasor_from_signal, pass axis=0 to operate over microtime bins
```

### Mean Lifetime Analysis

```python
# 1. Open PTU file and create CLSM image (as above)

# 2. Compute mean fluorescence lifetime per pixel
lifetime = run("tttrlib.CLSMImage.get_mean_lifetime",
    inputs={"clsm": clsm, "tttr_data": tttr},
    params={"stack_frames": True})

# lifetime is a BioImageRef (OME-TIFF) in nanoseconds
```

### FLIM + Cellpose Segmentation Workflow

```python
# 1. Open TTTR and create CLSM image
tttr = run("tttrlib.TTTR", params={"filename": "flim.ptu", "container_type": "PTU"})
clsm = run("tttrlib.CLSMImage",
    inputs={"tttr": tttr},
    params={"reading_routine": "SP5", "channels": [0]})

# 2. Extract intensity for segmentation
intensity = run("tttrlib.CLSMImage.get_intensity",
    inputs={"clsm": clsm},
    params={"stack_frames": True})

# 3. Segment cells with Cellpose
model = run("cellpose.models.CellposeModel",
    params={"model_type": "cyto3"})
labels = run("cellpose.models.CellposeModel.eval",
    inputs={"model": model, "x": intensity},
    params={"diameter": 30.0})

# 4. Extract mean lifetime for per-cell analysis
lifetime = run("tttrlib.CLSMImage.get_mean_lifetime",
    inputs={"clsm": clsm, "tttr_data": tttr},
    params={"stack_frames": True})

# labels is LabelImageRef, lifetime is BioImageRef
# Can be combined for per-cell lifetime statistics
```

## Available Functions (v0.3.0)

| Function | Description | Output |
|----------|-------------|--------|
| `tttrlib.TTTR` | Open TTTR file | TTTRRef |
| `tttrlib.TTTR.header` | Extract metadata | NativeOutputRef (JSON) |
| `tttrlib.TTTR.get_time_window_ranges` | Burst selection | TableRef |
| `tttrlib.TTTR.write` | Export TTTR data | TTTRRef |
| `tttrlib.Correlator` | Multi-tau correlation | TableRef |
| `tttrlib.CLSMImage` | Reconstruct CLSM image | ObjectRef |
| `tttrlib.CLSMImage.compute_ics` | Image correlation spectroscopy | BioImageRef |
| `tttrlib.CLSMImage.get_intensity` | Extract intensity image | BioImageRef |
| `tttrlib.CLSMImage.get_phasor` | Compute phasor coordinates | BioImageRef |
| `tttrlib.CLSMImage.get_fluorescence_decay` | Extract decay histogram | BioImageRef |
| `tttrlib.CLSMImage.get_mean_lifetime` | Compute mean lifetime | BioImageRef |

