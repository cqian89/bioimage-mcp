# Data Model: API Refinement & Permissions

## Entity Models

### Server Configuration
Top-level keys in `.bioimage-mcp/config.yaml`.

**permissions**:
- `mode`: `PermissionMode`
- `on_overwrite`: `OverwritePolicy`

**fs_allowlist_read**: list[str] (Top-level)
**fs_allowlist_write**: list[str] (Top-level)
**fs_denylist**: list[str] (Top-level)

**agent_guidance**:
- `warn_unactivated`: bool (Default: true)

---

### Permission Settings

**PermissionMode (Enum)**:
- `explicit`: Use only paths in `fs_allowlist_read/write`.
- `inherit`: (Default) Use paths provided by MCP `list_roots()`.
- `hybrid`: Combine `explicit` and `inherit` paths.

**OverwritePolicy (Enum)**:
- `allow`: Overwrite without asking.
- `deny`: Fail operation if file exists.
- `ask`: Prompt user via MCP Elicitation.

**PermissionDecision (Model)**:
- `operation`: "read" | "write"
- `path`: Absolute path checked.
- `mode`: `PermissionMode` used.
- `decision`: "ALLOWED" | "DENIED" | "ASK"
- `reason`: e.g., "Under inherited root /home/user/workspace"
- `timestamp`: UTC ISO string.

---

### Tool Hierarchy
Models for the refined discovery API.

**ToolHierarchyNode (Model)**:
- `name`: Node name (e.g., "filters").
- `full_path`: Full dot-notated path (e.g., "base.skimage.filters").
- `type`: "environment" | "package" | "module" | "function".
- `has_children`: Boolean.
- `fn_id`: Optional[str] - only present if `type == "function"`.
- `summary`: Optional[str] - short description.

**ScoredFunction (Model)**:
- `fn_id`: Canonical function ID.
- `name`: Human name.
- `description`: Summary text.
- `score`: Total weighted match score.
- `match_count`: Number of keywords matched.
- `tags`: List of strings.

---

### Function Registry
Models for canonical naming and aliasing.

**FunctionAlias (Model)**:
- `alias_id`: e.g., `base.gaussian`.
- `canonical_id`: e.g., `base.skimage.filters.gaussian`.
- `deprecated`: Boolean (True for short names).
- `migration_hint`: Message suggesting the new name.

---

### Request/Response Schemas

**ListToolsRequest**:
- `path`: Optional[str] - dot-notated prefix.
- `paths`: Optional[list[str]] - batch navigation.
- `limit`: int (default 20).
- `cursor`: str.

**ListToolsResponse**:
- `tools`: list[ToolHierarchyNode]
- `next_cursor`: str

**SearchFunctionsRequest**:
- `keywords`: list[str] | str (Required).
- `query`: Optional[str] - Legacy alias for `keywords`.
- `tags`: Optional[list[str]].
- `limit`: int (default 20).

**SearchFunctionsResponse**:
- `functions`: list[ScoredFunction]
- `next_cursor`: str

**DescribeFunctionRequest**:
- `fn_id`: Optional[str] - backward compatible single ID.
- `fn_ids`: Optional[list[str]] - batch retrieval.

**DescribeFunctionResponse**:
- `schemas`: dict[str, dict] - Mapping of fn_id to JSON schema.
- `errors`: dict[str, str] - Mapping of fn_id to error message.

**RunFunctionRequest**:
- `fn_id`: Function ID (canonical or alias).
- `inputs`: dict[str, ArtifactRef].
- `params`: dict[str, Any].
- `metadata`: includes `warn_unactivated`.

**RunFunctionResponse**:
- `result`: Execution output.
- `warnings`: list[str] (e.g., unactivated; NOTE: `call_tool` deprecation is logged, NOT returned here).
- `workflow_hint`: Guidance for the next step.
