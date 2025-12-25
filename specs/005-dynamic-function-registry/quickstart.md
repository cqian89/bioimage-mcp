# Quickstart: Dynamic Function Registry

This guide explains how to configure and use dynamically discovered tools from `scikit-image`, `phasorpy`, and `scipy.ndimage`.

## 1. Configuration

The dynamic registry is configured in `tools/base/manifest.yaml` (or other tool packs).

```yaml
dynamic_sources:
  - adapter: skimage
    modules:
      - skimage.filters
      - skimage.morphology
    include_patterns: ["*"]
    exclude_patterns: ["_*", "test_*"]
  
  - adapter: phasorpy
    modules:
      - phasorpy.phasor
    include_patterns: ["phasor_transform", "phasor_from_signal"]
```

## 2. Discovery

Once configured, functions appear in the standard tool list.

```python
# List tools to see dynamic functions
tools = mcp.list_tools()
print([t.name for t in tools if "skimage" in t.name])
# Output: ['skimage.filters.gaussian', 'skimage.filters.median', ...]

# Get full schema
tool_info = mcp.get_tool("skimage.filters.gaussian")
print(tool_info.inputSchema)
```

## 3. Execution

Call dynamic tools just like static ones. The adapter handles artifact conversion.

```python
# Apply Gaussian blur
result = mcp.call_tool(
    "skimage.filters.gaussian",
    arguments={
        "image": "image-artifact-uri",
        "sigma": 2.0
    }
)
```

## 4. Caching

Discovery results are cached. If you change the environment (update lockfile), the system automatically re-scans the modules on next startup.
