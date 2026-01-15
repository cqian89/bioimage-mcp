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
