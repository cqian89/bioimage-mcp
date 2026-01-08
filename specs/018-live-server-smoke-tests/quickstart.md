# Quickstart: Live Server Smoke Tests

**Feature**: 018-live-server-smoke-tests  
**Date**: 2026-01-08

This guide explains how to run the smoke test suite for bioimage-mcp.

---

## Prerequisites

### Required
- Python 3.13+
- `bioimage-mcp-base` conda environment installed
- Repository cloned with `datasets/` directory present

### Optional (for full suite)
- `bioimage-mcp-cellpose` conda environment installed

### Verify Setup

```bash
# Check base environment
conda run -n bioimage-mcp-base python -c "print('Base environment OK')"

# Check cellpose environment (optional)
conda run -n bioimage-mcp-cellpose python -c "print('Cellpose environment OK')"

# Check dataset
ls datasets/FLUTE_FLIM_data_tif/
# Should show: hMSC control.tif, Fluorescein_hMSC.tif, etc.
```

---

## Running Smoke Tests

### Minimal Suite (CI Mode)

Runs only scenarios that require the base environment. Fast enough for CI.

```bash
# Run minimal smoke tests
pytest tests/smoke/ -m smoke_minimal -v

# With timeout enforcement (2 minutes max)
pytest tests/smoke/ -m smoke_minimal -v --timeout=120
```

### Full Suite

Runs all scenarios, including those requiring optional tool environments.

```bash
# Run all smoke tests
pytest tests/smoke/ -v

# Skip cellpose if not installed
pytest tests/smoke/ -v -m "not requires_env"
```

### Recording Mode

Captures verbose interaction logs for debugging. Note that log recording is **disabled by default** to minimize disk usage and keep CI environments clean.

```bash
# Run with full logging (opt-in)
pytest tests/smoke/ -v --smoke-record

# Logs are saved to .bioimage-mcp/smoke_logs/
ls .bioimage-mcp/smoke_logs/
```

---

## Individual Scenarios

### FLIM Phasor Workflow

Tests the phasor analysis pipeline with real FLIM data.

```bash
pytest tests/smoke/test_flim_phasor_live.py -v
```

**What it tests**:
1. `list()` - Server returns environments
2. `describe()` - Fetch phasor function schema
3. `run(base.io.bioimage.read)` - Load FLIM image
4. `run(base.xarray.rename)` - Relabel axes for phasor
5. `run(base.phasorpy.phasor.phasor_from_signal)` - Compute phasors

### Cellpose Pipeline

Tests cell segmentation with preprocessing.

```bash
pytest tests/smoke/test_cellpose_pipeline_live.py -v
```

**What it tests**:
1. `run(base.io.bioimage.read)` - Load image
2. `run(base.xarray.sum)` - Z projection
3. `run(base.io.bioimage.export)` - Convert to OME-TIFF
4. `run(cellpose.models.CellposeModel.eval)` - Segment cells

---

## Understanding Test Output

### Passed Test

```
tests/smoke/test_flim_phasor_live.py::test_flim_phasor_workflow PASSED [100%]
```

### Skipped Test (Missing Environment)

```
tests/smoke/test_cellpose_pipeline_live.py::test_cellpose_pipeline SKIPPED [50%]
  Reason: Required environment not available: bioimage-mcp-cellpose
```

### Failed Test

```
tests/smoke/test_flim_phasor_live.py::test_flim_phasor_workflow FAILED [100%]
  SmokeTestError: Tool 'run' failed: ValidationError for fn_id=base.io.bioimage.read
  Interaction log saved: .bioimage-mcp/smoke_logs/smoke_2026-01-08_143022.json
```

---

## Interaction Logs

Interaction logs are saved to `.bioimage-mcp/smoke_logs/` **only when the `--smoke-record` flag is enabled**.

This is an opt-in feature to:
1. Prevent unnecessary disk usage during standard test runs.
2. Avoid cluttering CI runner environments by default.
3. Provide targeted debugging data only when requested.

### Log Structure

```json
{
  "test_run_id": "smoke_2026-01-08_143022",
  "scenario": "flim_phasor",
  "status": "passed",
  "interactions": [
    {"direction": "request", "tool": "list", ...},
    {"direction": "response", "tool": "list", ...},
    ...
  ]
}
```

### Analyzing Failures

1. Find the log file:
   ```bash
   ls -lt .bioimage-mcp/smoke_logs/ | head -1
   ```

2. Open and find the failing interaction:
   ```bash
   jq '.interactions[] | select(.error != null)' .bioimage-mcp/smoke_logs/smoke_*.json
   ```

3. Check server stderr:
   ```bash
   jq '.server_stderr' .bioimage-mcp/smoke_logs/smoke_*.json
   ```

---

## Troubleshooting

### Server Fails to Start

**Symptom**: Test fails with "Server failed to initialize within 30s"

**Causes**:
- Missing dependencies in core environment
- Port conflict (shouldn't happen with stdio)
- Configuration error

**Debug**:
```bash
# Run server directly to see errors
python -m bioimage_mcp serve --stdio
# Ctrl+C to stop
```

### Tool Execution Timeout

**Symptom**: Test fails with "Tool execution timed out"

**Causes**:
- Tool environment not installed
- Heavy computation on slow hardware
- Subprocess deadlock

**Debug**:
```bash
# Check if tool env exists
conda env list | grep bioimage-mcp

# Run doctor to check readiness
python -m bioimage_mcp doctor
```

### Dataset Not Found

**Symptom**: Test skipped with "Dataset missing at..."

**Causes**:
- Dataset not downloaded
- Running from wrong directory

**Fix**:
```bash
# Ensure you're in repo root
pwd
# Should show: /path/to/bioimage-mcp

# Check dataset exists
ls datasets/FLUTE_FLIM_data_tif/
```

---

## CI Integration

### GitHub Actions Example

```yaml
# .github/workflows/smoke.yml
name: Smoke Tests

on: [push, pull_request]

jobs:
  smoke-minimal:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      
      - name: Setup Conda
        uses: conda-incubator/setup-miniconda@v3
        with:
          auto-activate-base: false
      
      - name: Install base environment
        run: |
          conda env create -f envs/bioimage-mcp-base.lock.yml
      
      - name: Install test dependencies
        run: pip install -e ".[test]"
      
      - name: Run smoke tests
        run: pytest tests/smoke/ -m smoke_minimal -v --timeout=120
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-logs
          path: .bioimage-mcp/smoke_logs/
```

### Time Budgets

- **Minimal suite**: 2 minutes max (SC-001)
- **Individual scenarios**: 5 minutes max (SC-003)
- **Server startup**: 30 seconds max (SC-002)

### Best Practices

1. Run `smoke_minimal` tests on every PR
2. Run `smoke_full` tests on merge to main (requires tool environments)
3. Upload `.bioimage-mcp/smoke_logs/` as artifacts for debugging
4. Use `--smoke-record` for debugging failed CI runs

---

## Adding New Scenarios

1. Create a new test file in `tests/smoke/`:
   ```python
   # tests/smoke/test_my_scenario_live.py
   import pytest
   
   @pytest.mark.smoke_minimal  # or smoke_full
   @pytest.mark.requires_env("bioimage-mcp-base")
   async def test_my_scenario(live_server, sample_image):
       # Your test steps here
       result = await live_server.call_tool("list", {})
       assert "items" in result
   ```

2. Add required fixtures in `conftest.py` if needed.

3. Run your scenario:
   ```bash
   pytest tests/smoke/test_my_scenario_live.py -v
   ```
