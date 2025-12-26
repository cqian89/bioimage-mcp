# Next Steps: Bioimage-MCP Usability Improvements

**Date:** December 26, 2025  
**Based on:** Phasor FLIM workflow testing and architecture review

## Executive Summary

This document proposes four major improvements to bioimage-mcp based on user testing and architectural review:

1. **Dynamic Function Registry** - Expose all bioimage/signal processing functions via search
2. **In-Memory Artifact Processing** - Keep data in memory between tool calls
3. **LLM Guidance Hints** - Add next-step hints to guide workflow
4. **Automated Workflow Testing** - Create test harness for MCP tool sequences

---

## 1. Dynamic Function Registry

### Problem
Currently, only manually-defined wrapper functions are exposed. Users cannot access the full power of scikit-image, scipy.ndimage, phasorpy, or numpy array manipulation (reshape, transpose, moveaxis, squeeze).

### Proposed Solution

#### 1.1 Auto-generate MCP tools from Python signatures

Use `griffe` (static analysis) and `docstring_parser` to extract:
- Function signatures with type hints
- Docstring descriptions (Numpydoc/Google style)
- Parameter constraints and defaults

```python
# Example: Auto-generated tool definition from skimage.filters.gaussian
{
  "fn_id": "skimage.filters.gaussian",
  "name": "gaussian",
  "description": "Multi-dimensional Gaussian filter.",
  "params": {
    "sigma": {"type": "number", "description": "Standard deviation for Gaussian kernel"},
    "preserve_range": {"type": "boolean", "default": false}
  },
  "inputs": {"image": {"type": "BioImageRef", "required": true}},
  "outputs": {"filtered": {"type": "BioImageRef"}}
}
```

#### 1.2 Filter for bio-relevant functions

Apply an allow-list strategy:
- **Include namespaces:** `skimage.filters`, `skimage.morphology`, `skimage.measure`, `skimage.transform`, `scipy.ndimage`, `phasorpy.phasor`, `numpy` (only: `transpose`, `moveaxis`, `squeeze`, `expand_dims`, `reshape`)
- **Filter by signature:** At least one input/output must be array-like
- **Exclude:** Functions with `**kwargs` only, private functions (`_prefix`)

#### 1.3 Add missing axis manipulation tools

Priority tools to add immediately:
```python
# High priority - needed for FLIM axis correction
base.swap_axes(image, axis1, axis2)      # Swap two axes
base.relabel_axes(image, mapping)        # Rename axis labels (e.g., Z -> T)
base.squeeze(image, axis=None)           # Remove singleton dimensions
base.expand_dims(image, axis)            # Add dimension
base.moveaxis(image, source, dest)       # Move axis position
```

#### 1.4 Implementation approach

1. **Lazy manifest generation:** Build JSON manifest at install time, not runtime
2. **Paginated discovery:** Group by namespace prefix (e.g., `base.filters.*`)
3. **On-demand import:** Only import the actual module when tool is called

#### Libraries to use
- `griffe` - Static code analysis
- `docstring_parser` - Docstring to structured data
- `pydantic` - Schema generation

#### Risks
- Type ambiguity in some functions (generic `Any` types)
- Safety: Must validate namespace allow-list strictly

---

## 2. In-Memory Artifact Processing

### Problem
Every tool writes outputs to disk as OME-TIFF/OME-Zarr. This causes:
- High I/O latency for iterative workflows
- Disk space consumption for intermediate results
- No ability for LLM to inspect data characteristics without a separate "describe" call

### Proposed Solution

#### 2.1 Session-based in-memory cache

```python
class SessionArtifactCache:
    """LRU cache for in-memory artifacts within a session."""
    
    def __init__(self, max_memory_gb: float = 4.0):
        self.cache: dict[str, MemoryArtifact] = {}
        self.max_bytes = int(max_memory_gb * 1024**3)
        self.current_bytes = 0
    
    def put(self, ref_id: str, data: np.ndarray, metadata: dict) -> str:
        """Store array in memory, spill oldest if over limit."""
        ...
    
    def get(self, ref_id: str) -> np.ndarray | None:
        """Retrieve from cache, or load from disk if spilled."""
        ...
```

#### 2.2 Return metadata with every artifact

When loading or processing an image, always return:
```json
{
  "ref_id": "abc123",
  "in_memory": true,
  "metadata": {
    "shape": [56, 512, 512],
    "dtype": "uint16",
    "axes": "TYX",
    "axes_inferred": true,
    "physical_sizes": {"Y": 1.1795, "X": 1.1795},
    "size_bytes": 29360128,
    "file_metadata": {
      "ome_xml_summary": "FLIM TCSPC data, 56 time bins @ 0.027ns",
      "custom_attributes": {"FirstAxis": "DC-TCSPC T", "FirstAxis-Unit": "ns"}
    }
  }
}
```

This gives the LLM context about:
- Data dimensions and types
- Whether axes were inferred (suggesting manual correction may be needed)
- Physical calibration information
- Vendor-specific metadata that may affect interpretation

#### 2.3 Lazy loading for large files

For files > 2GB, use Zarr/Dask lazy loading:
```python
def load_image(uri: str, lazy: bool = True) -> LazyArtifact:
    if lazy and estimated_size > 2 * 1024**3:
        return dask.array.from_zarr(uri)  # Lazy, chunked
    return np.array(...)  # Eager, in-memory
```

#### 2.4 Handle subprocess isolation

Since tools run in isolated conda environments (subprocess), true memory sharing requires:
- **Option A:** Persistent worker process per tool-pack with shared memory
- **Option B:** Fast IPC via Unix socket + Arrow/Plasma for zero-copy transfer
- **Option C (simpler):** Memory-mapped OME-Zarr temp files (fast, cross-process)

**Recommendation:** Start with Option C (OME-Zarr with `MemoryStore` fallback to disk) for simplicity.

#### Memory management strategy

```
Session starts
  |
  v
Tool call produces artifact
  |
  v
Check session cache size
  |
  +-- Under limit --> Store in memory
  |
  +-- Over limit --> Spill oldest to temp Zarr file
                     |
                     v
                     Keep lightweight reference
```

#### Risks
- OOM if multiple large datasets held simultaneously
- Subprocess isolation complicates true shared memory
- Need clear garbage collection when session ends

---

## 3. LLM Guidance Hints

### Problem
LLMs don't know:
- What input format tools expect
- What tools to use next in a workflow
- How to fix errors (e.g., axis mismatch)

### Proposed Solution

#### 3.1 Add `inputs` schema to describe_function

Current:
```json
{
  "fn_id": "base.phasor_from_flim",
  "schema": {
    "properties": {"harmonic": {...}, "time_axis": {...}}
  }
}
```

Proposed:
```json
{
  "fn_id": "base.phasor_from_flim",
  "inputs": {
    "dataset": {
      "type": "BioImageRef",
      "required": true,
      "description": "FLIM dataset with time-bin dimension",
      "expected_axes": ["T", "Y", "X"],
      "preprocessing_hint": "If T dimension has only 1 sample, check if FLIM bins are in Z axis"
    }
  },
  "params": {
    "harmonic": {...},
    "time_axis": {...}
  },
  "outputs": {
    "g_image": {"type": "BioImageRef", "description": "Phasor G coordinates"},
    "s_image": {"type": "BioImageRef", "description": "Phasor S coordinates"},
    "intensity_image": {"type": "BioImageRef"}
  }
}
```

#### 3.2 Add next_step_hints to tool responses

```json
{
  "status": "succeeded",
  "outputs": {"g_image": {...}, "s_image": {...}},
  "hints": {
    "next_steps": [
      {
        "fn_id": "base.phasor_calibrate",
        "reason": "Apply calibration using reference standard",
        "required_inputs": ["reference dataset with known lifetime"]
      }
    ],
    "common_issues": [
      "Raw phasors are uncalibrated - use phasor_calibrate for quantitative analysis"
    ]
  }
}
```

#### 3.3 Add corrective hints on errors

```json
{
  "status": "failed",
  "error": {
    "message": "not enough samples=1 along axis=0",
    "code": "AXIS_SAMPLES_ERROR"
  },
  "hints": {
    "diagnosis": "The T axis has only 1 sample. FLIM time bins may be stored in Z dimension.",
    "suggested_fix": {
      "fn_id": "base.relabel_axes",
      "params": {"mapping": {"Z": "T"}},
      "explanation": "Relabel Z axis as T to treat Z slices as FLIM time bins"
    },
    "related_metadata": {
      "detected_axes": "TCZYX",
      "shape": [1, 1, 56, 512, 512],
      "ome_hint": "AxesLabels.FirstAxis = 'DC-TCSPC T' suggests Z is actually time"
    }
  }
}
```

#### 3.4 Add workflow guidance to discovery tools

**list_tools response:**
```json
{
  "tools": [...],
  "workflow_hint": "Use search_functions to find specific capabilities, then activate_functions to enable them"
}
```

**search_functions response:**
```json
{
  "functions": [...],
  "usage_hint": "Call activate_functions with fn_ids before using. Use describe_function for parameter details."
}
```

**activate_functions response:**
```json
{
  "active": ["base.phasor_from_flim", ...],
  "usage_hint": "Activated functions can now be called via call_tool. Use describe_function to see input requirements."
}
```

#### Implementation approach

1. Add `hints` field to `CallToolResult` model
2. Define hint schemas per function in manifest.yaml
3. Auto-generate some hints from docstrings and type signatures
4. Add workflow-level hints to discovery endpoints

---

## 4. Automated Workflow Testing

### Problem
No automated way to test the full LLM workflow:
1. `list_tools` -> `search_functions` -> `activate_functions` -> `describe_function` -> `call_tool`
2. Multi-step workflows like FLIM phasor analysis
3. Error handling and recovery paths

### Proposed Solution

#### 4.1 Create MCP test harness

```python
# tests/integration/test_mcp_workflows.py

class MCPTestClient:
    """Simulates LLM tool calls against the MCP server."""
    
    async def list_tools(self, limit: int = 10) -> dict:
        ...
    
    async def search_functions(self, query: str) -> dict:
        ...
    
    async def activate_functions(self, fn_ids: list[str]) -> dict:
        ...
    
    async def describe_function(self, fn_id: str) -> dict:
        ...
    
    async def call_tool(self, fn_id: str, inputs: dict, params: dict) -> dict:
        ...


@pytest.fixture
async def mcp_client():
    """Start MCP server and return test client."""
    async with MCPTestServer() as server:
        yield MCPTestClient(server)
```

#### 4.2 Define golden path workflows

```python
# tests/integration/test_phasor_workflow.py

async def test_phasor_flim_workflow(mcp_client, sample_flim_tiff):
    """Test the complete FLIM phasor analysis workflow."""
    
    # Step 1: Search for phasor tools
    result = await mcp_client.search_functions("phasor")
    assert "base.phasor_from_flim" in [f["fn_id"] for f in result["functions"]]
    
    # Step 2: Activate phasor tools
    result = await mcp_client.activate_functions([
        "base.phasor_from_flim",
        "base.phasor_calibrate"
    ])
    assert result["active"] == ["base.phasor_from_flim", "base.phasor_calibrate"]
    
    # Step 3: Describe to get input requirements
    result = await mcp_client.describe_function("base.phasor_from_flim")
    assert "dataset" in result.get("inputs", {}) or "time_axis" in result["schema"]["properties"]
    
    # Step 4: Call phasor analysis
    result = await mcp_client.call_tool(
        fn_id="base.phasor_from_flim",
        inputs={"dataset": {"type": "BioImageRef", "uri": sample_flim_tiff}},
        params={"harmonic": 1}
    )
    
    # Verify outputs
    assert result["status"] == "succeeded"
    assert "g_image" in result["outputs"]
    assert "s_image" in result["outputs"]
    assert result["outputs"]["g_image"]["type"] == "BioImageRef"
```

#### 4.3 Test all tools systematically

```python
# tests/integration/test_all_tools.py

@pytest.mark.parametrize("fn_id", get_all_registered_functions())
async def test_tool_describe_returns_valid_schema(mcp_client, fn_id):
    """Every registered function should return a valid JSON schema."""
    result = await mcp_client.describe_function(fn_id)
    assert "schema" in result
    assert result["schema"].get("type") == "object"


@pytest.mark.parametrize("fn_id,test_case", get_tool_test_cases())
async def test_tool_execution(mcp_client, fn_id, test_case):
    """Run each tool with a known-good test case."""
    result = await mcp_client.call_tool(
        fn_id=fn_id,
        inputs=test_case["inputs"],
        params=test_case["params"]
    )
    assert result["status"] == "succeeded"
```

#### 4.4 Add CLI test command

```bash
# Run all MCP workflow tests
python -m bioimage_mcp test-workflows

# Test specific workflow
python -m bioimage_mcp test-workflows --workflow phasor-flim

# Interactive debug mode (step through workflow)
python -m bioimage_mcp test-workflows --interactive
```

#### Implementation approach

1. Create `MCPTestClient` class that wraps MCP protocol calls
2. Add pytest fixtures for server lifecycle
3. Define test cases for each tool in `tests/integration/tool_test_cases.yaml`
4. Add GitHub Actions CI step to run workflow tests

#### Libraries to use
- `pytest-asyncio` - Async test support
- `pytest-timeout` - Prevent hanging tests
- `hypothesis` - Property-based testing for edge cases

---

## Implementation Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| P0 | Add axis manipulation tools (swap, relabel) | 1 day | Unblocks FLIM workflow |
| P0 | Automated workflow test harness | 2 days | Enables safe iteration |
| P1 | Add inputs schema to describe_function | 1 day | Improves LLM usability |
| P1 | Add next_step_hints to tool responses | 2 days | Guides LLM workflows |
| P2 | Dynamic function registry (skimage, scipy) | 3 days | Expands capabilities |
| P2 | In-memory artifact cache | 3 days | Improves performance |
| P3 | Corrective error hints | 2 days | Better error recovery |
| P3 | Lazy loading for large files | 2 days | Handles large data |

---

## Success Criteria

### For P0 items (immediate blockers)
- [ ] FLIM phasor workflow completes end-to-end on FLUTE test data
- [ ] All tools have passing automated tests
- [ ] No manual axis manipulation required by user

### For P1 items (usability)
- [ ] LLM can discover input requirements via describe_function
- [ ] LLM receives actionable next-step suggestions after each tool call
- [ ] Error messages include specific fix suggestions

### For P2/P3 items (capability expansion)
- [ ] 50+ functions available via search (skimage, scipy, phasorpy)
- [ ] Multi-step workflows complete without disk I/O for intermediate results
- [ ] Large (>4GB) datasets load successfully with lazy loading

---

## Appendix: Files to Create/Modify

### New files
- `src/bioimage_mcp/registry/scanner.py` - Dynamic function introspection
- `src/bioimage_mcp/sessions/cache.py` - In-memory artifact cache
- `tests/integration/mcp_client.py` - Test harness
- `tests/integration/test_workflows.py` - Workflow tests
- `tests/integration/tool_test_cases.yaml` - Test case definitions

### Modified files
- `src/bioimage_mcp/api/discovery.py` - Add hints to responses
- `src/bioimage_mcp/api/tools.py` - Add hints to call results
- `src/bioimage_mcp/runtimes/protocol.py` - Add hint fields to response model
- `tools/base/manifest.yaml` - Add axis manipulation functions
- `tools/base/bioimage_mcp_base/transforms.py` - Implement axis tools
