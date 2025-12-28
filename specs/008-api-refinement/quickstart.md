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

## Validation Workflow

### 1. Hierarchical Discovery
Verify you can navigate from environments down to specific functions.

```json
// 1. List environments
list_tools() 
// Returns: { "tools": [{name: "base", type: "environment"}, {name: "cellpose", type: "environment"}], "next_cursor": null }

// 2. List packages in base
list_tools(path="base") 
// Returns: { "tools": [{name: "skimage", type: "package"}, {name: "phasorpy", type: "package"}], "next_cursor": null }

// 3. List modules in skimage
list_tools(path="base.skimage")
// Returns: { "tools": [{name: "filters", type: "module"}, {name: "morphology", type: "module"}], "next_cursor": null }

// 4. List functions in filters
list_tools(path="base.skimage.filters")
// Returns: { "tools": [{name: "gaussian", fn_id: "base.skimage.filters.gaussian"}, ...], "next_cursor": null }
```

### 2. Multi-Keyword Search Ranking
Verify that search results are ranked by relevance. The `keywords` parameter accepts a list of strings or a single string.

```json
// Search for gaussian filters
search_functions(keywords=["gaussian", "filter"])
```
*Verification*: `base.skimage.filters.gaussian` should appear first (match count=2, high weight) over functions that only match one keyword. Legacy `query` parameter is still supported as an alias for `keywords`. The response includes `next_cursor`.

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

| Old ID (Deprecated) | New Canonical ID |
|---------------------|------------------|
| `builtin.gaussian_blur` | `base.skimage.filters.gaussian` |
| `builtin.convert_to_ome_zarr` | `base.convert_to_ome_zarr` |
| `call_tool` | `run_function` |

**Tip**: Always prefer `run_function`. If you call `call_tool`, it will work but a deprecation warning will be logged (not returned in the JSON response).

## Testing Commands

```bash
# Run discovery contract tests
pytest tests/contract/test_discovery_refinement.py

# Run permission integration tests (requires Roots-capable mock)
pytest tests/integration/test_inherit_permissions.py

# Validate naming migration
pytest tests/unit/registry/test_aliases.py
```
