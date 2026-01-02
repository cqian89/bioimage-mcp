# PhasorPy Adapter Quickstart

This guide helps developers quickly understand how to use and test the phasorpy adapter.

## Prerequisites

- bioimage-mcp server running
- `bioimage-mcp-base` environment with phasorpy>=0.9.0
- Sample FLIM data available:
  - **SDT**: `datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt` (BSD 3-Clause)
  - **TIFF**: `datasets/FLUTE_FLIM_data_tif/Embryo.tif`
  - **PTU**: `datasets/ptu_hazelnut_flim/hazelnut_FLIM_single_image.ptu` (BSD 3-Clause)
  - **LIF**: `datasets/lif_flim_testdata/FLIM_testdata.lif` (CC-BY 4.0)

## Quick Verification

```bash
# Run contract tests for phasorpy discovery
pytest tests/contract/test_phasorpy_discovery.py -v

# Run integration tests for phasorpy workflow
pytest tests/integration/test_phasorpy_workflow.py -v
```

## Example Workflow: FLIM Phasor Analysis

### Step 1: Discover Available Functions
```python
# Via MCP client or direct API
result = search_functions(query="phasor", tags=["flim"])
# Returns: phasorpy.phasor.phasor_from_signal, phasorpy.lifetime.phasor_calibrate, etc.
```

### Step 2: Load FLIM Data
```python
# Load via bioio (not phasorpy.io)
result = run_function(
    fn_id="base.bioio.read",
    inputs={},
    params={"path": "datasets/FLUTE_FLIM_data_tif/Embryo.tif"}
)
signal_ref = result["outputs"]["image"]

# Alternative: Load SDT file (requires bioio-bioformats)
result = run_function(
    fn_id="base.bioio.read",
    inputs={},
    params={"path": "datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt"}
)
signal_ref = result["outputs"]["image"]

# Alternative: Load PTU file (requires bioio-bioformats)
result = run_function(
    fn_id="base.bioio.read",
    inputs={},
    params={"path": "datasets/ptu_hazelnut_flim/hazelnut_FLIM_single_image.ptu"}
)
signal_ref = result["outputs"]["image"]

# Alternative: Load LIF file (requires bioio-lif)
result = run_function(
    fn_id="base.bioio.read",
    inputs={},
    params={"path": "datasets/lif_flim_testdata/FLIM_testdata.lif"}
)
signal_ref = result["outputs"]["image"]
```

### Step 3: Compute Phasor
```python
result = run_function(
    fn_id="phasorpy.phasor.phasor_from_signal",
    inputs={"signal": signal_ref},
    params={"axis": -1, "harmonic": 1}
)
mean_ref = result["outputs"]["mean"]
real_ref = result["outputs"]["real"]
imag_ref = result["outputs"]["imag"]
```

### Step 4: Calibrate (Optional)
```python
result = run_function(
    fn_id="phasorpy.lifetime.phasor_calibrate",
    inputs={
        "real": real_ref,
        "imag": imag_ref
    },
    params={
        "lifetime": 4.04,  # Fluorescein reference lifetime (ns)
        "frequency": 80e6  # 80 MHz laser
    }
)
calibrated_real = result["outputs"]["real"]
calibrated_imag = result["outputs"]["imag"]
```

### Step 5: Generate Phasor Plot
```python
result = run_function(
    fn_id="phasorpy.plot.plot_phasor",
    inputs={
        "real": calibrated_real,
        "imag": calibrated_imag
    },
    params={}
)
plot_ref = result["outputs"]["plot"]  # PlotRef with PNG
```

### Step 6: Export Plot
```python
# Export the plot artifact
result = export_artifact(
    ref_id=plot_ref["ref_id"],
    dest_path="output/phasor_plot.png"
)
```

## Verifying the Adapter

### Check Function Count
```python
# Should discover 50+ functions via list_tools
# (Filtered for phasorpy prefix)
tools = bioimage_mcp_list_tools()
phasorpy_fns = [f for f in tools if f.name.startswith("phasorpy.")]
assert len(phasorpy_fns) >= 50
```

### Check Function Schema
```python
# Verify full schema is available via describe_function
schema = bioimage_mcp_describe_function(fn_id="phasorpy.phasor.phasor_from_signal")
# Look for 'signal' input in the schema
input_names = [p["name"] for p in schema["parameters"].values()]
assert "signal" in input_names
assert schema["io_pattern"] == "signal_to_phasor"
```

### Check Error Handling
```python
# Verify invalid parameters return proper error codes
try:
    run_function(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs={"signal": signal_ref},
        params={"frequency": -1.0}  # Invalid
    )
except Exception as e:
    # Error should contain code: INVALID_PARAMETER
    assert "INVALID_PARAMETER" in str(e)
```

## Troubleshooting

### "phasorpy not installed"
Ensure the base environment has phasorpy:
```bash
micromamba activate bioimage-mcp-base
pip install phasorpy>=0.9.0
```

### "Artifact not found"
Check the artifact store path in config:
```yaml
# .bioimage-mcp/config.yaml
artifact_store:
  root: ~/.bioimage-mcp/artifacts
```

### "Invalid axis for phasor_from_signal"
Inspect the signal shape first:
```python
info = get_artifact(ref_id=signal_ref["ref_id"])
print(info["metadata"]["shape"])  # e.g., [1, 256, 1, 512, 512]
# Use axis=1 if decay bins are in channel dimension
```
