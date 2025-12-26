# Quickstart: Axis Manipulation Tools, LLM Guidance Hints & Workflow Test Harness

**Date**: 2025-12-26  
**Spec**: [spec.md](./spec.md)

## Validation Commands

After implementation, run these commands to verify the feature works correctly.

### 1. Run All Tests

```bash
# Run complete test suite
pytest

# Run with verbose output and timing
pytest -v --durations=20
```

### 2. Axis Tools Unit Tests

```bash
# Run axis operation unit tests
pytest tests/unit/base/test_axis_ops.py -v

# Expected: 10+ tests passing (2+ per axis tool)
# - test_relabel_axes_swap_zt
# - test_relabel_axes_duplicate_error
# - test_squeeze_singleton
# - test_squeeze_non_singleton_error
# - test_squeeze_all_singletons
# - test_expand_dims_at_start
# - test_expand_dims_duplicate_name_error
# - test_moveaxis_forward
# - test_moveaxis_negative_index
# - test_swap_axes_basic
```

### 3. Contract Tests

```bash
# Run axis tools schema validation
pytest tests/contract/test_axis_tools_schema.py -v

# Run hints schema validation
pytest tests/contract/test_hints_schema.py -v

# Expected: All registered axis tools return valid JSON schemas
```

### 4. Workflow Test Harness

```bash
# Run workflow tests (mock mode - no tool environments needed)
pytest tests/integration/test_workflows.py -v -m "not requires_env"

# Run workflow tests (full execution - requires bioimage-mcp-base env)
pytest tests/integration/test_workflows.py -v

# Expected:
# - test_full_discovery_to_execution_flow: PASSED
# - test_flim_phasor_workflow: PASSED
# - test_yaml_workflow_cases: PASSED (parametrized)
```

### 5. FLIM Phasor Golden Path

```bash
# Run the FLIM phasor workflow test specifically
pytest tests/integration/test_workflows.py::test_flim_phasor_golden_path -v

# Expected output:
# - Loads Embryo.tif from FLUTE dataset
# - Relabels Z<->T axes
# - Runs phasor_from_flim successfully
# - Outputs: g_image, s_image, intensity_image
```

### 6. Individual Axis Tool Verification

```bash
# Verify axis tools are discoverable
python -c "
from bioimage_mcp.registry.loader import load_manifests
from pathlib import Path

manifests, _ = load_manifests([Path('tools')])
for m in manifests:
    for fn in m.functions:
        if 'relabel' in fn.fn_id or 'squeeze' in fn.fn_id or 'expand' in fn.fn_id or 'move' in fn.fn_id or 'swap' in fn.fn_id:
            print(f'{fn.fn_id}: {fn.name}')
"

# Expected output:
# base.relabel_axes: Relabel axes
# base.squeeze: Squeeze dimensions
# base.expand_dims: Expand dimensions
# base.moveaxis: Move axis
# base.swap_axes: Swap axes
```

### 7. Hints Verification

```bash
# Verify describe_function returns hints for phasor_from_flim
python -c "
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import connect
from bioimage_mcp.config.schema import Config
from pathlib import Path

config = Config(
    artifact_store_root=Path('/tmp/test-artifacts'),
    tool_manifest_roots=[Path('tools')],
)
conn = connect(config)
discovery = DiscoveryService(conn)

# Load manifests first (would be done by server startup)
from bioimage_mcp.registry.loader import load_manifests
manifests, _ = load_manifests(config.tool_manifest_roots)
for m in manifests:
    discovery.upsert_tool(m.tool_id, m.name, m.description, m.tool_version, m.env_id, str(m.manifest_path), True, True)
    for fn in m.functions:
        discovery.upsert_function(fn.fn_id, fn.tool_id, fn.name, fn.description, fn.tags, 
                                   [p.model_dump() for p in fn.inputs], 
                                   [p.model_dump() for p in fn.outputs], 
                                   fn.params_schema)

result = discovery.describe_function('base.phasor_from_flim')
print('Hints present:', 'hints' in result or 'inputs' in result)
discovery.close()
"

# Expected: Hints present: True
```

### 8. Performance Check

```bash
# Check axis tool performance (<1s for 100MB images)
pytest tests/unit/base/test_axis_ops.py -v --durations=10

# Expected: All axis tool tests complete in <1s
```

### 9. Coverage Report

```bash
# Generate coverage report for axis tools
pytest tests/unit/base/test_axis_ops.py --cov=bioimage_mcp_base.axis_ops --cov-report=term-missing

# Expected: 100% branch coverage for axis tools
```

### 10. Lint Check

```bash
# Verify code style
ruff check tools/base/bioimage_mcp_base/axis_ops.py
ruff check tests/integration/mcp_test_client.py

# Expected: No issues
```

---

## Success Criteria Verification

| Criterion | Verification Command | Expected Result |
|-----------|---------------------|-----------------|
| SC-001: FLIM workflow completes | `pytest tests/integration/test_workflows.py::test_flim_phasor_golden_path` | PASSED |
| SC-002: Axis tools <1s | `pytest --durations=10` | All <1000ms |
| SC-003: 10+ axis tool tests | `pytest tests/unit/base/test_axis_ops.py --collect-only` | >=10 tests |
| SC-004: Discovery-to-execution test | `pytest tests/integration/test_workflows.py::test_full_discovery_to_execution_flow` | PASSED |
| SC-005: Schema validation | `pytest tests/contract/test_axis_tools_schema.py` | All PASSED |
| SC-006: Mock mode works | `pytest tests/integration/test_workflows.py -m "not requires_env"` | PASSED |
| SC-007: YAML test discovery | `pytest tests/integration/test_workflows.py::test_workflow_from_yaml --collect-only` | >=2 tests |
| SC-008: Inputs schema in describe | See Hints Verification above | Hints present |
| SC-009: next_steps in response | `pytest tests/integration/test_hints.py` | PASSED |
| SC-010: Error hints present | `pytest tests/integration/test_error_hints.py` | PASSED |
| SC-011: Rich artifact metadata | `pytest tests/contract/test_artifact_metadata.py` | PASSED |

---

## Development Setup

```bash
# Ensure base toolkit environment exists
python -m bioimage_mcp doctor

# If missing, install it
python -m bioimage_mcp install base

# Run tests
pytest

# Run just the new tests for this feature
pytest tests/unit/base/test_axis_ops.py tests/contract/test_axis_tools_schema.py tests/integration/test_workflows.py -v
```
