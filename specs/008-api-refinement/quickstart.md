# Quickstart: API Refinement Validation

This guide explains how to validate the refined discovery API, unified tool environment, and dynamic permission system.

## Configuration

Update your `.bioimage-mcp/config.yaml` to enable the new features. Note the specific configuration naming aligned with the server's permission model:

```yaml
permissions:
  mode: inherit        # Options: inherit, explicit, hybrid
  on_overwrite: ask   # Options: allow, deny, ask

fs_allowlist_read: []
fs_allowlist_write: []
fs_denylist: []

agent_guidance:
  warn_unactivated: true
```

---

## Breaking Changes (v0.8.0)

Per Constitution v0.6.0, backward compatibility is not required during early development.

**Removed in this version:**
- `builtin.*` tool pack - use `base.*` equivalents
- `call_tool` API - use `run_function`
- Function aliases - use canonical `env.package.module.function` names only
- `query` parameter in `search_functions` - use `keywords`

---

## Validation Workflow

### 1. Hierarchical Discovery
Verify you can navigate from environments down to specific functions.

```json
// 1. List environments
list_tools() 
// Returns: { "tools": [{name: "base", type: "environment"}, {name: "cellpose", type: "environment"}] }

// 2. Navigate to cellpose - auto-expands single-child paths!
list_tools(path="cellpose") 
// Returns: { 
//   "tools": [{name: "eval", fn_id: "cellpose.cellpose.models.eval"}, {name: "train", fn_id: "cellpose.cellpose.models.train"}],
//   "expanded_from": "cellpose -> cellpose.cellpose -> cellpose.cellpose.models"
// }

// 3. Navigate base (multi-package) - shows packages
list_tools(path="base")
// Returns: { "tools": [{name: "skimage", type: "package"}, {name: "phasorpy", type: "package"}] }

// 4. Flatten to get all functions at once
list_tools(path="base", flatten=true)
// Returns: { "tools": [{fn_id: "base.skimage.filters.gaussian"}, {fn_id: "base.phasorpy.phasor.phasor_from_signal"}, ...] }

// 5. Flatten everything
list_tools(flatten=true)
// Returns all functions across all environments
```

### Smart Hierarchy Shortcuts

The discovery API automatically expands single-child paths to reduce roundtrips:

- **Small environments** (like cellpose with 2 functions): One call to see all functions
- **Large environments** (like base with 47 functions): Browse by package/module
- **Flatten option**: Skip hierarchy entirely when you know what you want

This means an agent exploring cellpose doesn't need 4 calls:
```
X list_tools() -> list_tools(path="cellpose") -> list_tools(path="cellpose.cellpose") -> list_tools(path="cellpose.cellpose.models")

OK list_tools() -> list_tools(path="cellpose")  // Done! Functions returned directly
```

### 2. Multi-Keyword Search Ranking
Verify that search results are ranked by relevance. The `keywords` parameter accepts a list of strings or a single string.

```json
// Search for gaussian filters
search_functions(keywords=["gaussian", "filter"])
```

```json
// Typo tolerance via n-gram tokenization
search_functions(keywords=["gausian"])
```

*Verification*: `base.skimage.filters.gaussian` should appear first (match count=2, high weight) over functions that only match one keyword. The response includes `next_cursor`.

### 3. Permission Inheritance
1. Start an MCP client (e.g., Claude Desktop) and add a project folder to its roots.
2. Run a tool that reads from that folder.
3. Check `server.log` for inherited roots:
```text
[INFO] Session started. Inherited roots: ['/home/user/my-microscopy-project']
[INFO] Permission ALLOWED for READ: /home/user/my-microscopy-project/img.tif (Reason: Under inherited root)
```

### 4. Overwrite Protection (Elicitation)
Attempt to write to a file that already exists with `on_overwrite: ask`:
1. The server will send an `elicitation` request.
2. Your client should prompt: "File exists. Overwrite?"
3. If you confirm (Action: `accept`), the operation proceeds.

## Migration Checklist for Agents

If you are building an agent, use the following mapping for consolidated tools:

| Removed Function | Replacement |
|-----------------|-------------|
| `builtin.gaussian_blur` | `base.skimage.filters.gaussian` |
| `builtin.convert_to_ome_zarr` | `base.convert_to_ome_zarr` |
| `call_tool` | `run_function` |

**Tip**: `call_tool` has been removed. Update all calls to use `run_function`.

## Testing Commands

```bash
# Run discovery contract tests
pytest tests/contract/test_discovery_refinement.py

# Run permission integration tests (requires Roots-capable mock)
pytest tests/integration/test_inherit_permissions.py

# Validate naming migration
pytest tests/unit/registry/test_aliases.py
```
